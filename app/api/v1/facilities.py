from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.facility import (
    FacilityCreate,
    FacilityDetailResponse,
    FacilityResponse,
)
from app.schemas.shared import Page
from app.services.facility_service import FacilityServiceHandler

router = APIRouter(prefix="/facilities", tags=["Facilities"])


@router.get("", response_model=Page[FacilityResponse])
async def get_facilities(
    village_id: Optional[UUID] = Query(None, description="Filter by village UUID"),
    facility_type: Optional[str] = Query(None, description="Filter by facility type (PHC, CHC, HOSPITAL, PHARMACY)"),
    service: Optional[str] = Query(None, description="Filter by offered service name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List healthcare facilities with optional criteria (village_id, facility_type, service)."""
    handler = FacilityServiceHandler(db)
    items, total = await handler.list_facilities(
        village_id=village_id,
        facility_type=facility_type,
        service=service,
        skip=skip,
        limit=limit,
    )
    return Page(items=items, total=total)


@router.get("/{id}", response_model=FacilityDetailResponse)
async def get_facility(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get detailed healthcare facility record including services[] and doctors[]."""
    handler = FacilityServiceHandler(db)
    facility_detail = await handler.get_facility(id)
    if not facility_detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": f"Facility {id} not found"}},
        )
    return facility_detail


@router.post("", response_model=FacilityResponse, status_code=status.HTTP_201_CREATED)
async def create_facility(
    payload: FacilityCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new healthcare facility."""
    handler = FacilityServiceHandler(db)
    return await handler.create_facility(payload)
