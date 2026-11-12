from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.shared import (
    AvailabilityOut,
    StockReportIn,
    StockReportOut,
)
from app.services.stock_service import StockService

router = APIRouter(prefix="/stock", tags=["Stock Intelligence"])


@router.post("/report", response_model=StockReportOut, status_code=status.HTTP_201_CREATED)
async def submit_stock_report(
    payload: StockReportIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a medicine stock report.

    SECURITY RULE:
    The server determines source_type strictly from the authenticated caller's role.
    Client-provided source_type is never accepted or trusted.
    """
    service = StockService(db)
    try:
        response = await service.create_report(
            facility_id=payload.facility_id,
            medicine_id=payload.medicine_id,
            availability_status=payload.availability_status,
            reporter_id=current_user.id,
            caller_role=current_user.role,
        )
        return response
    except ValueError as e:
        error_msg = str(e)
        if "does not exist" in error_msg or "not found" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "NOT_FOUND", "message": error_msg}},
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "BAD_REQUEST", "message": error_msg}},
        )


@router.get("/availability", response_model=AvailabilityOut)
async def get_stock_availability(
    medicine_id: UUID = Query(..., description="Medicine UUID (required)"),
    facility_ids: Optional[str] = Query(None, description="Optional comma-separated facility UUIDs"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve probabilistic stock availability for a medicine across healthcare facilities.

    Labels:
    - LIKELY: p_available >= 0.65
    - UNCERTAIN: 0.35 < p_available < 0.65 (or insufficient confidence)
    - UNLIKELY: p_available <= 0.35
    """
    facility_id_list: Optional[List[UUID]] = None
    if facility_ids:
        try:
            facility_id_list = [UUID(f.strip()) for f in facility_ids.split(",") if f.strip()]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "BAD_REQUEST", "message": "Malformed facility UUID list"}},
            )

    service = StockService(db)
    try:
        items = await service.get_availability(medicine_id=medicine_id, facility_ids=facility_id_list)
        return AvailabilityOut(medicine_id=medicine_id, items=items)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": str(e)}},
        )
