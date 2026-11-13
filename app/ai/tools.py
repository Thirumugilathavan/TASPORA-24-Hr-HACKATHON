"""CareBridge AI Tool Registry and Backend Execution Handlers.

Provides typed, verified tool functions executing real CareBridge business logic:
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
from app.models.facility import (
    Facility,
    FacilityService,
    FacilitySpecialty,
    FacilitySource,
    FacilityAppointmentConfig,
)
from app.models.medicine import Medicine
from app.models.patient import Patient
from app.models.stock import FacilityMedicineBelief
from app.models.user import User
from app.models.village import Village
from app.schemas.shared import AttendanceStatus, AvailabilityLabel
from app.services.distance_service import haversine_km
from app.ai.rag import rag_engine
from app.ai.location_extractor import REFERENCE_COORDINATES, get_coordinates_for_location


async def search_facilities_tool(
    db: AsyncSession,
    location_name: Optional[str] = None,
    facility_type: Optional[str] = None,
    facility_category: Optional[str] = None,
    ownership: Optional[str] = None,
    service: Optional[str] = None,
    maternity: Optional[bool] = None,
    emergency: Optional[bool] = None,
    max_distance_km: float = 50.0,
    reference_lat: Optional[float] = None,
    reference_lon: Optional[float] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """Searches verified facilities from database with multi-criteria filtering and geographic ranking."""
    target_lat = reference_lat
    target_lon = reference_lon
    detected_location = location_name

    # Determine reference coordinates if location name provided
    clean_loc = (location_name or "").strip().lower()
    if clean_loc and (target_lat is None or target_lon is None):
        for loc_key, (klat, klon, _) in REFERENCE_COORDINATES.items():
            if loc_key in clean_loc or clean_loc in loc_key:
                target_lat, target_lon = klat, klon
                break

        # Check villages table if still unresolved
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
        selectinload(Facility.specialties_rel),
        selectinload(Facility.appointment_config),
        selectinload(Facility.doctors).selectinload(Doctor.schedules),
    )

    # Check if querying Coimbatore specifically or a known block/town
    coimbatore_keywords = [
        "coimbatore", "kovai", "cbe", "pollachi", "mettupalayam", "valparai", "annur",
        "sulur", "kinathukadavu", "madukkarai", "anamalai", "thondamuthur", "karamadai",
        "sarcarsamakulam", "sultanpet", "singanallur", "peelamedu", "r.s. puram",
        "gandhipuram", "saibaba colony", "ram nagar", "selvapuram", "ganapathy"
    ]
    is_coimbatore_query = any(k in clean_loc for k in coimbatore_keywords)

    if is_coimbatore_query:
        stmt = stmt.where(func.lower(Facility.district) == "coimbatore")
        # If user named a specific block/locality (e.g. "Pollachi", "Mettupalayam")
        specific_sub = next((k for k in coimbatore_keywords[3:] if k in clean_loc), None)
        if specific_sub:
            sub_clean = f"%{specific_sub}%"
            stmt = stmt.where(
                func.lower(func.coalesce(Facility.block, "")).like(sub_clean)
                | func.lower(func.coalesce(Facility.locality, "")).like(sub_clean)
                | func.lower(Facility.address).like(sub_clean)
                | func.lower(Facility.name).like(sub_clean)
            )

    # Filter by category / type if specified
    if facility_category:
        cat_upper = facility_category.strip().upper()
        stmt = stmt.where(func.upper(Facility.facility_category).contains(cat_upper))
    elif facility_type:
        clean_type = facility_type.strip().upper()
        if clean_type in ["PHC", "UPHC"]:
            stmt = stmt.where(
                or_(
                    func.upper(Facility.facility_type).in_(["PHC", "UPHC"]),
                    func.upper(Facility.facility_category).in_(["PRIMARY_HEALTH_CENTRE", "URBAN_PRIMARY_HEALTH_CENTRE", "PHC", "UPHC", "MATERNITY_HOME"]),
                )
            )
        elif clean_type in ["CHC", "COMMUNITY_HEALTH_CENTRE"]:
            stmt = stmt.where(
                or_(
                    func.upper(Facility.facility_type) == "CHC",
                    func.upper(Facility.facility_category).in_([
                        "CHC",
                        "COMMUNITY_HEALTH_CENTRE",
                        "SUB_DISTRICT_HOSPITAL",
                        "TALUK_HOSPITAL",
                    ]),
                )
            )
        else:
            stmt = stmt.where(func.upper(Facility.facility_type) == clean_type)

    # Filter by ownership (e.g., "government", "private")
    if ownership:
        clean_own = ownership.strip().lower()
        if clean_own in ["government", "govt", "public"]:
            stmt = stmt.where(func.lower(Facility.ownership).in_(["government", "municipal corporation"]))
        elif clean_own == "private":
            stmt = stmt.where(func.lower(Facility.ownership) == "private")

    # Filter by maternity / emergency flags
    if maternity is True or (service and "matern" in service.lower()):
        stmt = stmt.where(Facility.maternity_services == True)

    if emergency is True or (service and ("emerg" in service.lower() or "trauma" in service.lower() or "casualty" in service.lower())):
        stmt = stmt.where(Facility.emergency_services == True)

    # Generic service search
    if service and not ("matern" in service.lower() or "emerg" in service.lower()):
        stmt = (
            stmt.join(Facility.services)
            .where(func.lower(FacilityService.service_name).contains(service.lower()))
            .distinct()
        )

    res = await db.execute(stmt)
    all_facilities = list(res.scalars().all())

    # Do not silently fall back to unrelated facilities from another district!
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

        # Verified booking info
        apt_cfg = fac.appointment_config
        booking_method = apt_cfg.booking_method if apt_cfg else (fac.appointment_booking_method or "WALK_IN_ONLY")
        booking_url = apt_cfg.booking_url if apt_cfg else fac.online_booking_url
        booking_phone = apt_cfg.booking_phone if apt_cfg else fac.official_phone
        instructions_en = apt_cfg.instructions_en if apt_cfg else None
        instructions_ta = apt_cfg.instructions_ta if apt_cfg else None

        results.append({
            "facility_id": str(fac.id),
            "name": fac.name,
            "alternate_names": fac.alternate_names or [],
            "facility_type": fac.facility_type,
            "facility_category": fac.facility_category,
            "ownership": fac.ownership,
            "district": fac.district,
            "block": fac.block,
            "locality": fac.locality,
            "address": fac.address,
            "pincode": fac.pincode,
            "distance_km": dist_km,
            "latitude": fac.latitude,
            "longitude": fac.longitude,
            "official_phone": fac.official_phone,
            "official_website": fac.official_website,
            "emergency_contact": fac.emergency_contact,
            "opening_hours": fac.opening_hours,
            "emergency_services": fac.emergency_services,
            "ambulance_available": fac.ambulance_available,
            "maternity_services": fac.maternity_services,
            "pharmacy_available": fac.pharmacy_available,
            "specialties": fac.specialties or [],
            "appointment_booking_method": booking_method,
            "online_booking_url": booking_url,
            "booking_phone": booking_phone,
            "instructions_en": instructions_en,
            "instructions_ta": instructions_ta,
            "official_source_url": fac.official_source_url,
            "verification_status": fac.verification_status,
            "contact_details": fac.contact_details or {},
            "services": services_list,
            "doctors": doctors_info,
        })

    # Sort by distance if coordinates available
    if target_lat is not None and target_lon is not None:
        results.sort(key=lambda x: (x["distance_km"] if x["distance_km"] is not None else 999.0))
    else:
        results.sort(key=lambda x: x["name"])

    # If location_name was explicitly requested and not Coimbatore-wide, filter within max_distance_km
    in_range_facilities = results
    if clean_loc and not is_coimbatore_query:
        other_districts = ["tiruppur", "tirupur", "erode", "nilgiris", "salem", "namakkal", "ooty"]
        is_prohibited_district = any(d in clean_loc for d in other_districts)

        matched = []
        for f in results:
            addr_lower = (f["address"] or "").lower()
            name_lower = f["name"].lower()
            dist_lower = (f["district"] or "").lower()
            is_text_match = clean_loc in addr_lower or clean_loc in name_lower or clean_loc in dist_lower

            # If user explicitly asked for another district, do not leak Coimbatore facilities
            if is_prohibited_district:
                if is_text_match:
                    matched.append(f)
            else:
                is_dist_match = f["distance_km"] is not None and f["distance_km"] <= max_distance_km
                if is_text_match or is_dist_match:
                    matched.append(f)
        in_range_facilities = matched

    return {
        "query_location": detected_location,
        "reference_lat": target_lat,
        "reference_lon": target_lon,
        "in_range": len(in_range_facilities) > 0,
        "nearest_distance_km": results[0]["distance_km"] if results else None,
        "nearest_facility_name": results[0]["name"] if results else None,
        "count": len(in_range_facilities[:limit]),
        "facilities": in_range_facilities[:limit],
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
    elif location_name and location_name.strip():
        clean_loc = location_name.strip().lower()
        stmt = stmt.join(Doctor.facility).where(
            or_(
                func.lower(Facility.address).contains(clean_loc),
                func.lower(Facility.name).contains(clean_loc),
            )
        )

    res = await db.execute(stmt)
    doctors = list(res.scalars().all())

    # Fallback to all doctors ONLY if query had no specific location or facility filter
    if not doctors and not location_name and not facility_name and not doctor_name:
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
    """Retrieves authoritative CareBridge documentation chunks using BM25 semantic scoring."""
    results = rag_engine.retrieve(query, top_k=top_k)
    return {
        "query": query,
        "matches_count": len(results),
        "sources": results,
    }


def emergency_guidance_tool(symptom_or_query: str, location_name: Optional[str] = None) -> Dict[str, Any]:
    """Returns official 108 emergency ambulance protocols and verified 24x7 emergency hospital directory."""
    clean_loc = (location_name or "").lower()
    coimbatore_keywords = [
        "coimbatore", "kovai", "pollachi", "mettupalayam", "valparai", "annur",
        "sulur", "kinathukadavu", "madukkarai", "anamalai", "thondamuthur", "karamadai",
        "singanallur", "peelamedu", "r.s. puram", "gandhipuram", "saibaba colony"
    ]
    is_cbe = any(k in clean_loc for k in coimbatore_keywords) or any(k in symptom_or_query.lower() for k in coimbatore_keywords)

    if is_cbe:
        emergency_facilities = [
            "Coimbatore Medical College Hospital (CMCH) — 24/7 Level 1 Trauma Care, Trichy Road (Phone: 0422-2301393)",
            "Government ESI Medical College Hospital — 24/7 Casualty & Emergency, Singanallur (Phone: 0422-2574391)",
            "Government Headquarters Hospital (GHQH), Pollachi — 24/7 CEmONC & Trauma, Udumalai Road (Phone: 04259-229322)",
            "Government Hospital, Mettupalayam — 24/7 CEmONC & Trauma Care (Phone: 04254-222027)",
            "Ganga Hospital — 24/7 Emergency Trauma & Micro-surgery Unit, Mettupalayam Road (Phone: 0422-4250000)",
            "PSG Hospitals — 24/7 Emergency, Stroke & Cardiac Care, Peelamedu (Emergency: 7449108108 / 0422-4345353)",
            "Kovai Medical Center and Hospital (KMCH) — 24/7 Level 1 Emergency Centre, Avanashi Road (Phone: 0422-4323999)",
            "Sri Ramakrishna Hospital — 24/7 Emergency & Trauma, New Siddhapudur (Phone: 7970108108 / 0422-3500000)",
        ]
    else:
        emergency_facilities = [
            "CHC Tiruchengode (24/7 Emergency & Inpatient Trauma Care)",
            "District Headquarters Hospital Namakkal",
            "Government Mohan Kumaramangalam Medical College Hospital, Salem",
        ]

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
        "nearest_24x7_facilities": emergency_facilities,
    }


async def get_appointment_slots_tool(
    db: AsyncSession,
    facility_name: Optional[str] = None,
    location_name: Optional[str] = None,
    target_date: Optional[date] = None,
) -> Dict[str, Any]:
    """Retrieves genuine hospital booking configurations and verified doctor schedules.
    Never invents fake appointment IDs, fake slots, or mock confirmations.
    """
    query_date = target_date or date.today()

    stmt = select(Facility).options(
        selectinload(Facility.appointment_config),
        selectinload(Facility.doctors).selectinload(Doctor.schedules),
    )

    clean_fac = (facility_name or "").strip().lower()
    clean_loc = (location_name or "").strip().lower()

    if clean_fac:
        stmt = stmt.where(
            func.lower(Facility.name).contains(clean_fac)
            | func.lower(func.coalesce(Facility.locality, "")).contains(clean_fac)
        )
    elif clean_loc:
        coimbatore_keywords = [
            "coimbatore", "kovai", "pollachi", "mettupalayam", "valparai", "annur",
            "sulur", "kinathukadavu", "madukkarai", "anamalai", "thondamuthur", "karamadai"
        ]
        if any(k in clean_loc for k in coimbatore_keywords):
            stmt = stmt.where(func.lower(Facility.district) == "coimbatore")
            specific_sub = next((k for k in coimbatore_keywords[2:] if k in clean_loc), None)
            if specific_sub:
                stmt = stmt.where(
                    func.lower(func.coalesce(Facility.block, "")).contains(specific_sub)
                    | func.lower(func.coalesce(Facility.locality, "")).contains(specific_sub)
                    | func.lower(Facility.address).contains(specific_sub)
                )
        else:
            stmt = stmt.where(
                or_(
                    func.lower(Facility.address).contains(clean_loc),
                    func.lower(Facility.name).contains(clean_loc),
                )
            )

    res = await db.execute(stmt)
    facs = list(res.scalars().all())

    if not facs:
        return {
            "date": query_date.isoformat(),
            "booking_available": False,
            "message": "No matching verified healthcare facility found in database for booking.",
            "options": [],
        }

    booking_options = []
    for fac in facs[:5]:
        apt_cfg = fac.appointment_config
        booking_method = apt_cfg.booking_method if apt_cfg else (fac.appointment_booking_method or "WALK_IN_ONLY")
        online_url = apt_cfg.booking_url if apt_cfg else fac.online_booking_url
        phone = apt_cfg.booking_phone if apt_cfg else fac.official_phone
        inst_en = apt_cfg.instructions_en if apt_cfg else (
            "Walk-in registration at hospital OPD counter (08:00 AM - 12:00 PM). Emergency casualties operate 24x7 without prior booking."
            if booking_method == "WALK_IN_ONLY"
            else f"Book online at {online_url} or call {phone}."
        )
        inst_ta = apt_cfg.instructions_ta if apt_cfg else (
            "மருத்துவமனை புறநோயாளி கவுண்டரில் நேரடி பதிவு (காலை 08:00 - நண்பகல் 12:00). அவசர சிகிச்சை பிரிவு 24 மணி நேரமும் செயல்படும்."
            if booking_method == "WALK_IN_ONLY"
            else f"{online_url} இணையதளத்தில் அல்லது {phone} எண்ணில் முன்பதிவு செய்யலாம்."
        )

        real_doctors = []
        for doc in fac.doctors:
            sched = next((s for s in doc.schedules if s.schedule_date == query_date), None)
            att = sched.attendance_status if sched else "SCHEDULE_PENDING"
            hours = f"{sched.start_time} - {sched.end_time}" if sched else fac.opening_hours or "Consultation pending"

            real_doctors.append({
                "doctor_id": str(doc.id),
                "doctor_name": doc.name,
                "specialization": doc.specialization,
                "doctor_status": att,
                "shift_hours": hours,
            })

        booking_options.append({
            "facility_id": str(fac.id),
            "facility_name": fac.name,
            "district": fac.district,
            "block": fac.block,
            "locality": fac.locality,
            "address": fac.address,
            "ownership": fac.ownership,
            "booking_method": booking_method,
            "online_booking_url": online_url,
            "booking_phone": phone,
            "instructions_en": inst_en,
            "instructions_ta": inst_ta,
            "emergency_services": fac.emergency_services,
            "opening_hours": fac.opening_hours,
            "verified_doctors": real_doctors,
            "available_slots": [],  # Never invent mock slots!
        })

    return {
        "date": query_date.isoformat(),
        "booking_available": len(booking_options) > 0,
        "options": booking_options,
    }
