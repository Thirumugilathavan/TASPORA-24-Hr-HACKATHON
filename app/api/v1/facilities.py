from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_optional_current_user, require_role
from app.models.user import User
from app.schemas.facility import (
    FacilityCreate,
    FacilityDetailResponse,
    FacilityResponse,
    NearbyFacilityList,
)
from app.schemas.shared import Page, Role
from app.services.facility_service import FacilityServiceHandler

router = APIRouter(prefix="/facilities", tags=["Facilities"])
healthcare_router = APIRouter(prefix="/healthcare-facilities", tags=["Healthcare Facilities"])


@router.get("/nearby", response_model=NearbyFacilityList)
@healthcare_router.get("/nearby", response_model=NearbyFacilityList)
async def get_nearby_facilities(
    latitude: Optional[float] = Query(None, ge=-90.0, le=90.0, description="Latitude for distance calculation"),
    longitude: Optional[float] = Query(None, ge=-180.0, le=180.0, description="Longitude for distance calculation"),
    village_id: Optional[UUID] = Query(None, description="Village UUID to resolve location from"),
    patient_id: Optional[UUID] = Query(None, description="Patient UUID to resolve location from registered village"),
    radius_km: float = Query(10.0, ge=0.1, le=500.0, description="Search radius in kilometres (default: 10 km)"),
    facility_type: Optional[str] = Query(None, description="Filter by facility type (PHC, CHC, HOSPITAL, SUB_CENTRE, etc.)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve healthcare facilities ranked strictly by ascending geographic distance from the patient's resolved location.

    Location resolution priority:
    1. Explicit coordinates (latitude, longitude)
    2. Explicit village_id
    3. Explicit patient_id
    4. Authenticated current_user's patient profile / registered village
    """
    resolved_patient_id = patient_id
    if not (latitude is not None and longitude is not None) and not village_id and not resolved_patient_id:
        if current_user:
            resolved_patient_id = current_user.id

    if not (latitude is not None and longitude is not None) and not village_id and not resolved_patient_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "LOCATION_REQUIRED",
                    "message": "Must provide either latitude & longitude coordinates, village_id, patient_id, or authenticate as a registered patient.",
                }
            },
        )

    handler = FacilityServiceHandler(db)
    try:
        return await handler.get_nearby_facilities(
            lat=latitude,
            lon=longitude,
            village_id=village_id,
            patient_id=resolved_patient_id,
            radius_km=radius_km,
            facility_type=facility_type,
            limit=limit,
            skip=skip,
        )
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "NOT_FOUND", "message": error_msg}},
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "BAD_REQUEST", "message": error_msg}},
        )


@router.get("", response_model=Page[FacilityResponse])
@healthcare_router.get("", response_model=Page[FacilityResponse])
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
    current_user: User = Depends(require_role([Role.STAFF.value, Role.ADMIN.value])),
    db: AsyncSession = Depends(get_db),
):
    """Register a new healthcare facility (STAFF or ADMIN only)."""
    handler = FacilityServiceHandler(db)
    try:
        return await handler.create_facility(payload)
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
