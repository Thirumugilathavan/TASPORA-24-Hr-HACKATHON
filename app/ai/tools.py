"""NALAM AI AI Tool Registry and Backend Execution Handlers.

Provides typed, verified tool functions executing real NALAM AI business logic:
- Facility search & geographic proximity ranking
- Doctor schedule & verified attendance lookups
- Probabilistic medicine inventory queries
- Expected loss minimization recommendation calculations
- Direct slot booking
- Project RAG documentation queries
- Emergency 108 protocol guidance
"""
from datetime import date, datetime, timezone
import math
import re
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.math_utils import round_expected_loss
from app.models.doctor import Doctor, DoctorSchedule
from app.models.facility import Facility, FacilityService
from app.models.medicine import Medicine
from app.models.patient import Patient
from app.models.stock import FacilityMedicineBelief
from app.models.user import User
from app.models.village import Village
from app.models.scheme import GovernmentScheme
from app.schemas.shared import AttendanceStatus, AvailabilityLabel
from app.services.distance_service import haversine_km
from app.ai.rag import rag_engine

# Known reference coordinates for Tamil Nadu & evaluation districts
REFERENCE_COORDINATES = {
    "tiruchengode": (11.3800, 77.8900, "Namakkal, Tamil Nadu"),
    "molasi": (11.3420, 77.8450, "Namakkal, Tamil Nadu"),
    "namakkal": (11.2189, 78.1674, "Namakkal, Tamil Nadu"),
    "rampur": (12.9165, 79.1325, "Vellore, Tamil Nadu"),
    "mohanpur": (12.9240, 79.1450, "Vellore, Tamil Nadu"),
    "anandpur": (12.2253, 79.0747, "Tiruvannamalai, Tamil Nadu"),
    "vellore": (12.9165, 79.1325, "Vellore, Tamil Nadu"),
    "salem": (11.6643, 78.1460, "Salem, Tamil Nadu"),
    "sitapur": (27.5684, 80.6791, "Sitapur, Uttar Pradesh"),
}


async def search_facilities_tool(
    db: AsyncSession,
    location_name: Optional[str] = None,
    facility_type: Optional[str] = None,
    service: Optional[str] = None,
    max_distance_km: float = 50.0,
    reference_lat: Optional[float] = None,
    reference_lon: Optional[float] = None,
    limit: int = 5,
) -> Dict[str, Any]:
    """Searches real facilities from database, calculates distance, and loads doctors & services."""
    target_lat = reference_lat
    target_lon = reference_lon
    detected_location = location_name

    # Determine reference coordinates if location name provided
    if location_name and (target_lat is None or target_lon is None):
        clean_loc = location_name.strip().lower()
        # 1. Check known coordinates
        for loc_key, (klat, klon, _) in REFERENCE_COORDINATES.items():
            if loc_key in clean_loc or clean_loc in loc_key:
                target_lat, target_lon = klat, klon
                break

        # 2. Check villages table
        if target_lat is None:
            v_stmt = select(Village).where(func.lower(Village.name).contains(clean_loc))
            v_res = await db.execute(v_stmt)
            v_match = v_res.scalars().first()
            if v_match:
                target_lat, target_lon = v_match.latitude, v_match.longitude
                detected_location = v_match.name

    # Query facilities with eager loaded relationships
    stmt = select(Facility).options(
        selectinload(Facility.services),
        selectinload(Facility.doctors).selectinload(Doctor.schedules),
    )

    if facility_type:
        clean_type = facility_type.strip().upper()
        stmt = stmt.where(func.upper(Facility.facility_type) == clean_type)

    if service:
        stmt = (
            stmt.join(Facility.services)
            .where(func.lower(FacilityService.service_name).contains(service.lower()))
            .distinct()
        )

    res = await db.execute(stmt)
    all_facilities = list(res.scalars().all())

    # Fallback to all facilities if specific filter was empty
    if not all_facilities and facility_type:
        fallback_stmt = select(Facility).options(
            selectinload(Facility.services),
            selectinload(Facility.doctors).selectinload(Doctor.schedules),
        )
        res = await db.execute(fallback_stmt)
        all_facilities = list(res.scalars().all())

    today = date.today()
    results = []

    for fac in all_facilities:
        dist_km = None
        if target_lat is not None and target_lon is not None:
            dist_km = round(haversine_km(target_lat, target_lon, fac.latitude, fac.longitude), 1)

        # Check doctor attendance
        doctors_info = []
        for doc in fac.doctors:
            today_sched = next((s for s in doc.schedules if s.schedule_date == today), None)
            att_status = today_sched.attendance_status if today_sched else "UNKNOWN"
            hours = f"{today_sched.start_time} - {today_sched.end_time}" if today_sched else "Schedule pending"
            verified = today_sched.last_verified_at.strftime("%H:%M") if today_sched and today_sched.last_verified_at else None

            doctors_info.append({
                "doctor_id": str(doc.id),
                "name": doc.name,
                "specialization": doc.specialization,
                "attendance_status": att_status,
                "hours": hours,
                "verified_at": verified,
            })

        services_list = [s.service_name for s in fac.services]

        results.append({
            "facility_id": str(fac.id),
            "name": fac.name,
            "facility_type": fac.facility_type,
            "address": fac.address,
            "distance_km": dist_km,
            "latitude": fac.latitude,
            "longitude": fac.longitude,
            "contact_details": fac.contact_details or {},
            "services": services_list,
            "doctors": doctors_info,
        })

    # Sort by distance if coordinates available
    if target_lat is not None and target_lon is not None:
        results.sort(key=lambda x: (x["distance_km"] if x["distance_km"] is not None else 999.0))
    else:
        results.sort(key=lambda x: x["name"])

    return {
        "query_location": detected_location,
        "reference_lat": target_lat,
        "reference_lon": target_lon,
        "count": len(results[:limit]),
        "facilities": results[:limit],
    }


async def check_doctor_availability_tool(
    db: AsyncSession,
    facility_name: Optional[str] = None,
    doctor_name: Optional[str] = None,
    specialization: Optional[str] = None,
    location_name: Optional[str] = None,
    target_date: Optional[date] = None,
) -> Dict[str, Any]:
    """Retrieves verified doctor schedule and attendance status from database."""
    query_date = target_date or date.today()

    stmt = select(Doctor).options(
        selectinload(Doctor.facility),
        selectinload(Doctor.schedules),
    )

    if doctor_name:
        stmt = stmt.where(func.lower(Doctor.name).contains(doctor_name.lower().strip()))

    if specialization:
        stmt = stmt.where(func.lower(Doctor.specialization).contains(specialization.lower().strip()))

    if facility_name:
        stmt = stmt.join(Doctor.facility).where(func.lower(Facility.name).contains(facility_name.lower().strip()))

    res = await db.execute(stmt)
    doctors = list(res.scalars().all())

    # Fallback to all doctors if search too strict
    if not doctors:
        fallback_stmt = select(Doctor).options(
            selectinload(Doctor.facility),
            selectinload(Doctor.schedules),
        ).limit(10)
        res = await db.execute(fallback_stmt)
        doctors = list(res.scalars().all())

    results = []
    for doc in doctors:
        sched = next((s for s in doc.schedules if s.schedule_date == query_date), None)
        status = sched.attendance_status if sched else "UNKNOWN"
        time_slot = f"{sched.start_time} - {sched.end_time}" if sched else "Pending"
        notes = sched.notes if sched else "No duty log entered"

        results.append({
            "doctor_id": str(doc.id),
            "name": doc.name,
            "specialization": doc.specialization,
            "qualification": doc.qualification,
            "facility_id": str(doc.facility.id) if doc.facility else None,
            "facility_name": doc.facility.name if doc.facility else "Unassigned",
            "attendance_status": status,
            "shift_hours": time_slot,
            "notes": notes,
            "last_verified_at": sched.last_verified_at.isoformat() if sched and sched.last_verified_at else None,
        })

    return {
        "date": query_date.isoformat(),
        "total_doctors_found": len(results),
        "doctors": results,
    }


async def check_medicine_stock_tool(
    db: AsyncSession,
    medicine_name: str,
    facility_name: Optional[str] = None,
    location_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Queries probabilistic medicine availability beliefs across facilities."""
    clean_med = medicine_name.strip().lower()

    # Find medicine in catalogue
    m_stmt = select(Medicine).where(
        or_(
            func.lower(Medicine.name).contains(clean_med),
            func.lower(Medicine.generic_name).contains(clean_med),
        )
    )
    m_res = await db.execute(m_stmt)
    matched_med = m_res.scalars().first()

    if not matched_med:
        # Search all medicines
        all_meds = (await db.execute(select(Medicine))).scalars().all()
        return {
            "medicine_found": False,
            "query": medicine_name,
            "available_medicines": [m.name for m in all_meds],
            "facilities": [],
        }

    # Query beliefs
    b_stmt = (
        select(FacilityMedicineBelief)
        .where(FacilityMedicineBelief.medicine_id == matched_med.id)
        .options(selectinload(FacilityMedicineBelief.facility))
    )

    if facility_name:
        b_stmt = b_stmt.join(FacilityMedicineBelief.facility).where(
            func.lower(Facility.name).contains(facility_name.lower().strip())
        )

    b_res = await db.execute(b_stmt)
    beliefs = list(b_res.scalars().all())

    facilities_data = []
    for b in beliefs:
        facilities_data.append({
            "facility_id": str(b.facility.id),
            "facility_name": b.facility.name,
            "facility_type": b.facility.facility_type,
            "address": b.facility.address,
            "p_available": round(b.p_available, 2),
            "confidence": round(b.confidence, 2),
            "availability_label": b.label,
            "evidence_count": b.evidence_count,
            "last_report_at": b.last_report_at.isoformat() if b.last_report_at else None,
        })

    # Sort: LIKELY first, highest probability first
    label_prio = {"LIKELY": 0, "UNCERTAIN": 1, "UNLIKELY": 2}
    facilities_data.sort(key=lambda x: (label_prio.get(x["availability_label"], 9), -x["p_available"]))

    return {
        "medicine_found": True,
        "medicine": {
            "id": str(matched_med.id),
            "name": matched_med.name,
            "generic_name": matched_med.generic_name,
            "strength": matched_med.strength,
            "dosage_form": matched_med.dosage_form,
        },
        "facilities": facilities_data,
    }


async def get_recommendations_tool(
    db: AsyncSession,
    village_name: Optional[str] = None,
    request_type: str = "CONSULTATION",
    urgency: str = "NORMAL",
    medicine_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculates uncertainty-aware healthcare recommendations minimizing Expected Trip Loss."""
    clean_v = (village_name or "Tiruchengode").strip().lower()

    # Find origin village coordinates
    target_lat, target_lon = 11.3800, 77.8900
    matched_village_name = village_name or "Tiruchengode"

    for k, (klat, klon, _) in REFERENCE_COORDINATES.items():
        if k in clean_v or clean_v in k:
            target_lat, target_lon = klat, klon
            matched_village_name = k.capitalize()
            break

    # Look up in DB
    v_stmt = select(Village).where(func.lower(Village.name).contains(clean_v))
    v_res = await db.execute(v_stmt)
    v_row = v_res.scalars().first()
    if v_row:
        target_lat, target_lon = v_row.latitude, v_row.longitude
        matched_village_name = v_row.name

    # Retrieve all facilities
    f_stmt = select(Facility).options(
        selectinload(Facility.services),
        selectinload(Facility.doctors).selectinload(Doctor.schedules),
        selectinload(Facility.belief_states),
    )
    facilities = list((await db.execute(f_stmt)).scalars().all())

    # Find medicine if specified
    med_id = None
    if medicine_name:
        m_stmt = select(Medicine).where(func.lower(Medicine.name).contains(medicine_name.lower().strip()))
        m_row = (await db.execute(m_stmt)).scalars().first()
        if m_row:
            med_id = m_row.id

    today = date.today()
    scored_candidates = []

    for fac in facilities:
        dist_km = round(haversine_km(target_lat, target_lon, fac.latitude, fac.longitude), 1)

        # Baseline travel cost (heuristic: base + cost_per_km * distance)
        base_cost = 25.0 if fac.facility_type == "CHC" else 15.0
        cost_per_km = 3.0 if fac.facility_type == "CHC" else 2.0
        travel_cost = base_cost + cost_per_km * dist_km

        # Failure probability calculation
        failure_prob = 0.1  # baseline friction

        # Doctor presence factor
        has_present_doctor = False
        has_expected_doctor = False
        for doc in fac.doctors:
            sched = next((s for s in doc.schedules if s.schedule_date == today), None)
            if sched and sched.attendance_status == "PRESENT":
                has_present_doctor = True
            elif sched and sched.attendance_status == "EXPECTED":
                has_expected_doctor = True

        if request_type in ["CONSULTATION", "CHECKUP"]:
            if has_present_doctor:
                failure_prob += 0.05
            elif has_expected_doctor:
                failure_prob += 0.35  # rostered but not checked in
            else:
                failure_prob += 0.80  # no doctor

        # Medicine availability factor
        med_p_avail = 0.5
        med_label = "UNCERTAIN"
        if med_id:
            belief = next((b for b in fac.belief_states if b.medicine_id == med_id), None)
            if belief:
                med_p_avail = belief.p_available
                med_label = belief.label
                failure_prob = max(failure_prob, 1.0 - med_p_avail)
            else:
                failure_prob = max(failure_prob, 0.70)

        failure_prob = max(0.02, min(0.98, failure_prob))
        expected_loss = round_expected_loss(failure_prob * travel_cost)

        doc_summary = "PRESENT" if has_present_doctor else ("EXPECTED" if has_expected_doctor else "ABSENT")

        scored_candidates.append({
            "facility_id": str(fac.id),
            "facility_name": fac.name,
            "facility_type": fac.facility_type,
            "distance_km": dist_km,
            "doctor_status": doc_summary,
            "medicine_status": med_label if medicine_name else "N/A",
            "medicine_probability": round(med_p_avail, 2) if medicine_name else None,
            "failure_probability": round(failure_prob, 2),
            "travel_cost": round(travel_cost, 1),
            "expected_loss": expected_loss,
            "recommendation_reason": (
                f"Distance: {dist_km} km. Doctor: {doc_summary}. "
                f"Expected Trip Loss: {expected_loss} units (Risk: {int(failure_prob*100)}%)."
            ),
        })

    # Sort ascending by expected loss
    scored_candidates.sort(key=lambda x: (x["expected_loss"], x["distance_km"]))

    return {
        "origin_village": matched_village_name,
        "request_type": request_type,
        "urgency": urgency,
        "medicine_queried": medicine_name,
        "recommendations": scored_candidates[:3],
    }


def query_rag_knowledge_tool(query: str, top_k: int = 3) -> Dict[str, Any]:
    """Retrieves authoritative NALAM AI documentation chunks using BM25 semantic scoring."""
    results = rag_engine.retrieve(query, top_k=top_k)
    return {
        "query": query,
        "matches_count": len(results),
        "sources": results,
    }


def emergency_guidance_tool(symptom_or_query: str) -> Dict[str, Any]:
    """Returns official 108 emergency ambulance protocols and immediate action items."""
    return {
        "is_emergency": True,
        "emergency_number": "108",
        "title": "அவசர மருத்துவ உதவி / Emergency Medical Assistance",
        "instruction_en": (
            "🚨 CRITICAL: Call 108 immediately for free emergency ambulance dispatch. "
            "Stay on the line, state your exact location and landmarks, and keep the patient calm. "
            "Do not attempt unverified transport for severe chest pain, major trauma, or unconsciousness."
        ),
        "instruction_ta": (
            "🚨 அவசர நிலை: உடனடியாக 108 இலவச ஆம்புலன்ஸ் எண்ணை அழைக்கவும்! "
            "இணைப்பில் இருந்து உங்கள் இருப்பிடம் மற்றும் அடையாளங்களை தெரிவிக்கவும். "
            "நோயாளிக்கு தண்ணீர் கொடுக்காமல் அமைதியாக வைத்திருக்கவும்."
        ),
        "nearest_24x7_facilities": [
            "CHC Tiruchengode (24/7 Emergency & Inpatient Trauma Care)",
            "District Headquarters Hospital Namakkal",
            "Government Mohan Kumaramangalam Medical College Hospital, Salem",
        ],
    }


async def query_government_schemes_tool(
    db: AsyncSession,
    query_text: str,
    category: Optional[str] = None,
    limit: int = 3,
) -> Dict[str, Any]:
    """Queries verified government welfare schemes, subsidies, healthcare benefits, and scholarships."""
    from app.services.scheme_recommendation_service import SchemeRecommendationEngine
    await SchemeRecommendationEngine.seed_verified_schemes_if_empty(db)

    stmt = select(GovernmentScheme).where(GovernmentScheme.is_active == True)
    if category and category != "ALL":
        stmt = stmt.where(GovernmentScheme.category == category)

    q = query_text.lower().strip()
    # Map common query keywords to categories or search terms
    if any(k in q for k in ["scholarship", "கல்வி", "படிப்பு", "மாணவர்", "மாணவி", "student", "college", "school"]):
        stmt = stmt.where(GovernmentScheme.category == "EDUCATION")
    elif any(k in q for k in ["hospital", "மருத்துவ", "insurance", "காப்பீடு", "cmchis", "ஆரோக்கிய", "health"]):
        stmt = stmt.where(GovernmentScheme.category == "HEALTHCARE")
    elif any(k in q for k in ["farmer", "விவசாய", "உழவர்", "agriculture", "kisan", "நிலம்"]):
        stmt = stmt.where(GovernmentScheme.category == "AGRICULTURE")
    elif any(k in q for k in ["pension", "ஓய்வூதியம்", "முதியோர்", "விதவை", "senior", "widow"]):
        stmt = stmt.where(GovernmentScheme.category == "PENSION")
    elif any(k in q for k in ["women", "பெண்", "தாய்", "கர்ப்பிணி", "maternity", "மகப்பேறு", "kmut"]):
        stmt = stmt.where(GovernmentScheme.category == "WOMEN_CHILD")
    elif any(k in q for k in ["disability", "மாற்றுத்திறனாளி", "ஊனம்"]):
        stmt = stmt.where(GovernmentScheme.category == "DISABILITY")
    elif any(k in q for k in ["loan", "business", "தொழில்", "முத்ரா", "mudra"]):
        stmt = stmt.where(GovernmentScheme.category == "EMPLOYMENT")

    stmt = stmt.order_by(GovernmentScheme.level.desc(), GovernmentScheme.name.asc()).limit(limit)
    schemes = (await db.execute(stmt)).scalars().all()

    results = []
    for s in schemes:
        results.append({
            "id": str(s.id),
            "slug": s.slug,
            "name": s.name,
            "name_ta": s.name_ta,
            "short_description": s.short_description,
            "short_description_ta": s.short_description_ta,
            "department": s.department,
            "department_ta": s.department_ta,
            "level": s.level,
            "category": s.category,
            "benefit_amount_desc": s.benefit_amount_desc,
            "benefit_amount_desc_ta": s.benefit_amount_desc_ta,
            "official_portal_url": s.official_portal_url,
            "official_source_url": s.official_source_url,
            "required_documents": [d["name_en"] for d in (s.required_documents or [])[:3]],
            "required_documents_ta": [d["name_ta"] for d in (s.required_documents or [])[:3]],
        })

    return {
        "query": query_text,
        "count": len(results),
        "schemes": results,
    }
