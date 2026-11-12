"""
FastAPI router for Statewide Tamil Nadu Health Camps, Outreach Events,
District Coverage Analytics, and Official Source Management.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_optional_current_user
from app.models.user import User
from app.models.health_camp import HealthCampSource
from app.schemas.health_camp import (
    HealthCampOut,
    HealthCampListResponse,
    DistrictCoverageResponse,
    HealthCampSourceOut,
    HealthCampSourceCreateIn,
    CampVerificationUpdateIn,
    UserCampPreferenceIn,
    UserCampPreferenceOut,
)
from app.services.camp_service import CampService
from app.services.camp_collector_service import CampCollectorService
from app.services.tn_districts import get_all_districts, normalize_tn_district

router = APIRouter(prefix="/camps", tags=["Health Camps"])


@router.get("", response_model=HealthCampListResponse)
async def list_health_camps(
    query: Optional[str] = Query(None, description="Search by camp title, venue, service, or locality"),
    district: Optional[str] = Query("ALL", description="Target district or 'ALL'"),
    category: Optional[str] = Query("ALL", description="Event category or 'ALL'"),
    verification_status: Optional[str] = Query("VERIFIED", description="VERIFIED, UNVERIFIED, or ALL"),
    event_status: Optional[str] = Query("UPCOMING", description="UPCOMING, ONGOING, COMPLETED, or ALL"),
    date_range: Optional[str] = Query("upcoming", description="all, today, this_week, upcoming, past"),
    user_lat: Optional[float] = Query(None, description="User latitude for proximity ranking"),
    user_lng: Optional[float] = Query(None, description="User longitude for proximity ranking"),
    max_distance_km: Optional[float] = Query(None, ge=1.0, le=500.0, description="Max proximity radius"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Search and discover verified Tamil Nadu government health camps,
    Mobile Medical Unit sessions, NCD screening outreach, and Health Melas.
    """
    return await CampService.get_camps(
        session=db,
        query=query,
        district=district,
        category=category,
        verification_status=verification_status,
        event_status=event_status,
        date_range=date_range,
        user_lat=user_lat,
        user_lng=user_lng,
        max_distance_km=max_distance_km,
        limit=limit,
        offset=offset,
    )


@router.get("/coverage", response_model=DistrictCoverageResponse)
async def get_statewide_coverage(db: AsyncSession = Depends(get_db)):
    """
    Statewide district coverage analytics across all 38 canonical Tamil Nadu districts.
    Reports upcoming verified event count, source check status, and data freshness.
    """
    return await CampService.get_district_coverage(session=db)


@router.get("/districts", response_model=List[Dict[str, Any]])
async def list_tamil_nadu_districts():
    """
    Returns canonical list of all 38 Tamil Nadu districts with headquarters,
    Tamil script names, and centroid coordinates.
    """
    return get_all_districts()


@router.get("/sources", response_model=List[HealthCampSourceOut])
async def list_health_camp_sources(db: AsyncSession = Depends(get_db)):
    """
    List configured official health camp sources with last check timestamps and status.
    """
    await CampCollectorService.initialize_default_sources(db)
    stmt = select(HealthCampSource).order_by(HealthCampSource.name)
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.post("/sources", response_model=HealthCampSourceOut, status_code=status.HTTP_201_CREATED)
async def create_health_camp_source(
    source_in: HealthCampSourceCreateIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new official Tamil Nadu government or district health source.
    """
    canonical_district = normalize_tn_district(source_in.district) if source_in.district else None
    new_src = HealthCampSource(
        name=source_in.name,
        organization=source_in.organization,
        source_url=source_in.source_url,
        collector_type=source_in.collector_type,
        district=canonical_district,
        check_interval_hours=source_in.check_interval_hours,
        is_active=source_in.is_active,
        last_status="PENDING",
    )
    db.add(new_src)
    await db.commit()
    await db.refresh(new_src)
    return new_src


@router.post("/sync", response_model=Dict[str, Any])
async def trigger_source_sync(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger scheduled or on-demand collection sync across all active official sources.
    """
    return await CampService.sync_all_sources(session=db)


@router.get("/preferences", response_model=UserCampPreferenceOut)
async def get_camp_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve user health camp notification preferences.
    """
    return await CampService.get_user_preferences(session=db, user_id=current_user.id)


@router.put("/preferences", response_model=UserCampPreferenceOut)
async def update_camp_preferences(
    pref_in: UserCampPreferenceIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update user health camp notification preferences (opt-in, preferred districts, radius).
    """
    return await CampService.update_user_preferences(
        session=db, user_id=current_user.id, pref_in=pref_in
    )


@router.get("/{id}", response_model=HealthCampOut)
async def get_health_camp_detail(id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Retrieve full details of a specific health camp, including official source provenance
    and linked follow-up healthcare facilities.
    """
    camp = await CampService.get_camp_by_id(session=db, camp_id=id)
    if not camp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": f"Health camp {id} not found"}},
        )
    return camp


@router.patch("/{id}/verification", response_model=HealthCampOut)
async def update_camp_verification(
    id: UUID,
    update_in: CampVerificationUpdateIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Administrative review endpoint to confirm, reject, flag, or update event status.
    """
    updated = await CampService.update_camp_verification(
        session=db, camp_id=id, update_in=update_in
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": f"Health camp {id} not found"}},
        )
    return updated
