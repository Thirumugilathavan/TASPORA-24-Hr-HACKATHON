from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import check_patient_ownership, get_current_user
from app.models.doctor import DoctorSchedule
from app.models.facility import Facility
from app.models.patient import Patient
from app.models.recommendation import Recommendation
from app.models.request import HealthcareRequest
from app.models.stock import FacilityMedicineBelief
from app.models.user import User
from app.models.village import Village
from app.schemas.shared import RecommendationItem, RecommendationOut, Role
from app.schemas.workflow import RecommendationCreateIn
from app.services.recommendation_service import generate_recommendations

router = APIRouter(prefix="/recommendations", tags=["Smart Recommendations"])


@router.post(
    "",
    response_model=RecommendationOut,
    status_code=status.HTTP_200_OK,
    summary="Generate and store loss-minimized facility recommendations",
)
async def create_recommendation(
    payload: RecommendationCreateIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate smart facility recommendations for a healthcare request.

    Factors considered:
    1. Facility suitability for requested service
    2. Doctor attendance and schedule confirmation
    3. Medicine availability probability and confidence
    4. Approximate straight-line distance (km)
    5. Expected journey loss (failure_probability * travel_cost)

    Recommendations are persisted and sorted ascending by expected_loss.
    """
    # 1. Verify existence of the healthcare request
    stmt = select(HealthcareRequest).where(HealthcareRequest.id == payload.request_id)
    result = await db.execute(stmt)
    req = result.scalar_one_or_none()

    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Healthcare request not found.",
                }
            },
        )

    # 2. Authorization check
    if not await check_patient_ownership(db, current_user, req.patient_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "FORBIDDEN",
                    "message": "You do not have permission to generate recommendations for this request.",
                }
            },
        )

    # 3. Retrieve patient village & live database entities if available
    p_stmt = select(Patient).where(
        (Patient.id == req.patient_id) | (Patient.user_id == req.patient_id)
    )
    p_res = await db.execute(p_stmt)
    patient_rec = p_res.scalar_one_or_none()

    target_village_id = patient_rec.village_id if patient_rec else None
    village_coords = None
    if target_village_id:
        v_stmt = select(Village).where(Village.id == target_village_id)
        v_res = await db.execute(v_stmt)
        village_obj = v_res.scalar_one_or_none()
        if village_obj:
            village_coords = (village_obj.latitude, village_obj.longitude)

    # Check for live facilities in the database
    f_stmt = select(Facility).options(selectinload(Facility.services))
    f_res = await db.execute(f_stmt)
    db_facilities = f_res.scalars().all()

    candidate_facilities = None
    if db_facilities:
        candidate_facilities = []
        today = date.today()
        for f in db_facilities:
            svc_names = [s.service_name for s in f.services]
            ft = f.facility_type.upper()
            base_cost = 25 if ft == "CHC" else 15 if ft == "PHC" else 40 if ft == "HOSPITAL" else 10

            fac_dict = {
                "id": f.id,
                "name": f.name,
                "facility_type": f.facility_type,
                "services": svc_names,
                "base_cost": base_cost,
                "cost_per_km": 3,
                "latitude": f.latitude,
                "longitude": f.longitude,
                "_simulated": True,
            }

            # Check doctor attendance today if scheduled
            sched_stmt = select(DoctorSchedule).where(
                DoctorSchedule.facility_id == f.id,
                DoctorSchedule.schedule_date == today,
            )
            sched_res = await db.execute(sched_stmt)
            sched = sched_res.scalars().first()
            if sched:
                fac_dict["doctor_status"] = sched.attendance_status

            # Check medicine belief if request has medicine_id
            if req.medicine_id:
                belief_stmt = select(FacilityMedicineBelief).where(
                    FacilityMedicineBelief.facility_id == f.id,
                    FacilityMedicineBelief.medicine_id == req.medicine_id,
                )
                b_res = await db.execute(belief_stmt)
                belief = b_res.scalar_one_or_none()
                if belief:
                    fac_dict["medicine_belief"] = {
                        "p": belief.p_available,
                        "conf": belief.confidence,
                        "label": belief.label,
                    }

            candidate_facilities.append(fac_dict)

    # 4. Generate recommendations using intelligence engine
    items = generate_recommendations(
        req,
        village_id=target_village_id,
        candidate_facilities=candidate_facilities,
        village_coords=village_coords,
    )
    items_dicts = [item.model_dump(mode="json") for item in items]

    # 5. Check if recommendations already persisted for this request
    rec_stmt = select(Recommendation).where(Recommendation.request_id == payload.request_id)
    rec_res = await db.execute(rec_stmt)
    existing_rec = rec_res.scalar_one_or_none()

    if existing_rec:
        existing_rec.items_payload = items_dicts
    else:
        new_rec = Recommendation(
            request_id=payload.request_id,
            items_payload=items_dicts,
        )
        db.add(new_rec)

    await db.commit()

    return RecommendationOut(
        request_id=payload.request_id,
        items=items,
    )


@router.get(
    "/{request_id}",
    response_model=RecommendationOut,
    status_code=status.HTTP_200_OK,
    summary="Retrieve stored recommendations for a healthcare request",
)
async def get_recommendations_for_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve existing stored recommendations for a request."""
    # 1. Fetch request for ownership check
    req_stmt = select(HealthcareRequest).where(HealthcareRequest.id == request_id)
    req_res = await db.execute(req_stmt)
    req = req_res.scalar_one_or_none()

    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Healthcare request not found.",
                }
            },
        )

    if not await check_patient_ownership(db, current_user, req.patient_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "FORBIDDEN",
                    "message": "You do not have permission to view recommendations for this request.",
                }
            },
        )

    # 2. Fetch stored recommendation
    rec_stmt = select(Recommendation).where(Recommendation.request_id == request_id)
    rec_res = await db.execute(rec_stmt)
    rec = rec_res.scalar_one_or_none()

    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "No recommendations found for this request. Call POST /api/recommendations first.",
                }
            },
        )

    items = [RecommendationItem(**item) for item in rec.items_payload]

    return RecommendationOut(
        request_id=rec.request_id,
        items=items,
    )
