from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.recommendation import Recommendation
from app.models.request import HealthcareRequest
from app.models.user import User
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
    if current_user.role == Role.PATIENT.value and req.patient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "FORBIDDEN",
                    "message": "You do not have permission to generate recommendations for this request.",
                }
            },
        )

    # 3. Generate recommendations using intelligence engine
    items = generate_recommendations(req)
    items_dicts = [item.model_dump(mode="json") for item in items]

    # 4. Check if recommendations already persisted for this request
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

    if current_user.role == Role.PATIENT.value and req.patient_id != current_user.id:
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
