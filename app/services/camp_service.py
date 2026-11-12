"""
Health Camp Discovery and District Coverage Query Service for NALAM AI.
Provides multi-criteria search, spatial proximity sorting, canonical district coverage analytics,
follow-up facility integration, and administrative verification.
"""

from datetime import datetime, timezone, timedelta
import math
from typing import Dict, List, Optional, Any, Tuple
import uuid

from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.health_camp import HealthCamp, HealthCampSource, UserCampPreference
from app.models.facility import Facility
from app.schemas.health_camp import (
    HealthCampOut,
    HealthCampListResponse,
    DistrictCoverageItem,
    DistrictCoverageResponse,
    CampVerificationUpdateIn,
    UserCampPreferenceIn,
    UserCampPreferenceOut,
)
from app.services.tn_districts import (
    get_all_districts,
    normalize_tn_district,
    get_district_metadata,
    TN_DISTRICTS,
)
from app.services.camp_collector_service import CampCollectorService


def calculate_haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points in kilometers."""
    R = 6371.0  # Earth's radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)


class CampService:
    """
    Core service for querying health camps, calculating proximity,
    aggregating statewide district coverage, and managing user preferences.
    """

    @staticmethod
    async def get_camps(
        session: AsyncSession,
        query: Optional[str] = None,
        district: Optional[str] = None,
        category: Optional[str] = None,
        verification_status: Optional[str] = "VERIFIED",
        event_status: Optional[str] = "UPCOMING",
        date_range: Optional[str] = "upcoming",  # all, today, this_week, upcoming, past
        user_lat: Optional[float] = None,
        user_lng: Optional[float] = None,
        max_distance_km: Optional[float] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> HealthCampListResponse:
        """
        Query health camps with full text, spatial, temporal, and district filtering.
        """
        now = datetime.now(timezone.utc)
        stmt = select(HealthCamp)
        conditions = []

        # District normalization
        if district and district.upper() != "ALL":
            canon_dist = normalize_tn_district(district)
            if canon_dist:
                conditions.append(HealthCamp.district == canon_dist)
            else:
                conditions.append(HealthCamp.district.ilike(f"%{district.strip()}%"))

        # Category filter
        if category and category.upper() != "ALL":
            conditions.append(HealthCamp.category == category)

        # Verification status
        if verification_status and verification_status.upper() != "ALL":
            conditions.append(HealthCamp.verification_status == verification_status)

        # Event status & date range
        if event_status and event_status.upper() != "ALL":
            conditions.append(HealthCamp.event_status == event_status)

        if date_range == "today":
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            conditions.append(and_(HealthCamp.start_date >= today_start, HealthCamp.start_date < today_end))
        elif date_range == "this_week":
            week_end = now + timedelta(days=7)
            conditions.append(and_(HealthCamp.start_date >= now, HealthCamp.start_date <= week_end))
        elif date_range == "upcoming":
            conditions.append(HealthCamp.start_date >= now - timedelta(hours=4))
        elif date_range == "past":
            conditions.append(HealthCamp.start_date < now)

        # Free-text search across title, description, venue, services
        if query and query.strip():
            q = f"%{query.strip()}%"
            conditions.append(
                or_(
                    HealthCamp.title.ilike(q),
                    HealthCamp.description.ilike(q),
                    HealthCamp.venue_name.ilike(q),
                    HealthCamp.full_address.ilike(q),
                    HealthCamp.taluk.ilike(q),
                    HealthCamp.district.ilike(q),
                    HealthCamp.organizing_dept.ilike(q),
                )
            )

        if conditions:
            stmt = stmt.where(and_(*conditions))

        # Default temporal ordering
        if date_range == "past":
            stmt = stmt.order_by(desc(HealthCamp.start_date))
        else:
            stmt = stmt.order_by(asc(HealthCamp.start_date))

        res = await session.execute(stmt)
        camps = list(res.scalars().all())

        # If spatial coordinates provided, compute distance and sort by distance
        items_out: List[HealthCampOut] = []
        for camp in camps:
            dist_km = None
            if user_lat is not None and user_lng is not None and camp.latitude is not None and camp.longitude is not None:
                dist_km = calculate_haversine_distance_km(user_lat, user_lng, camp.latitude, camp.longitude)

            # Apply distance filter if requested
            if max_distance_km and dist_km is not None and dist_km > max_distance_km:
                continue

            camp_dict = {
                "id": camp.id,
                "title": camp.title,
                "description": camp.description,
                "category": camp.category,
                "organizing_dept": camp.organizing_dept,
                "start_date": camp.start_date,
                "end_date": camp.end_date,
                "venue_name": camp.venue_name,
                "full_address": camp.full_address,
                "village": camp.village,
                "town": camp.town,
                "taluk": camp.taluk,
                "district": camp.district,
                "latitude": camp.latitude,
                "longitude": camp.longitude,
                "services_offered": camp.services_offered or [],
                "eligibility": camp.eligibility,
                "registration_instructions": camp.registration_instructions,
                "contact_info": camp.contact_info,
                "source_id": camp.source_id,
                "source_org": camp.source_org,
                "source_url": camp.source_url,
                "publication_date": camp.publication_date,
                "discovered_at": camp.discovered_at,
                "last_checked_at": camp.last_checked_at,
                "verification_status": camp.verification_status,
                "event_status": camp.event_status,
                "followup_instructions": camp.followup_instructions,
                "followup_facility_id": camp.followup_facility_id,
                "provenance": camp.provenance or {},
                "distance_km": dist_km,
                "created_at": camp.created_at,
                "updated_at": camp.updated_at,
            }
            items_out.append(HealthCampOut(**camp_dict))

        # Proximity sort when user coordinates are provided
        if user_lat is not None and user_lng is not None:
            # Sort with valid distance first in ascending order, then those without distance by date
            items_out.sort(key=lambda x: (x.distance_km is None, x.distance_km if x.distance_km is not None else 0, x.start_date))

        total_count = len(items_out)
        paginated_items = items_out[offset : offset + limit]

        user_loc = None
        if user_lat is not None and user_lng is not None:
            user_loc = {"latitude": user_lat, "longitude": user_lng}

        return HealthCampListResponse(
            items=paginated_items,
            total=total_count,
            user_location=user_loc,
            filters_applied={
                "query": query,
                "district": district,
                "category": category,
                "verification_status": verification_status,
                "event_status": event_status,
                "date_range": date_range,
                "max_distance_km": max_distance_km,
            },
        )

    @staticmethod
    async def get_camp_by_id(session: AsyncSession, camp_id: uuid.UUID) -> Optional[HealthCampOut]:
        """Fetch single camp details with linked follow-up facility information."""
        stmt = select(HealthCamp).where(HealthCamp.id == camp_id)
        res = await session.execute(stmt)
        camp = res.scalars().first()
        if not camp:
            return None

        # Build schema
        camp_dict = {
            "id": camp.id,
            "title": camp.title,
            "description": camp.description,
            "category": camp.category,
            "organizing_dept": camp.organizing_dept,
            "start_date": camp.start_date,
            "end_date": camp.end_date,
            "venue_name": camp.venue_name,
            "full_address": camp.full_address,
            "village": camp.village,
            "town": camp.town,
            "taluk": camp.taluk,
            "district": camp.district,
            "latitude": camp.latitude,
            "longitude": camp.longitude,
            "services_offered": camp.services_offered or [],
            "eligibility": camp.eligibility,
            "registration_instructions": camp.registration_instructions,
            "contact_info": camp.contact_info,
            "source_id": camp.source_id,
            "source_org": camp.source_org,
            "source_url": camp.source_url,
            "publication_date": camp.publication_date,
            "discovered_at": camp.discovered_at,
            "last_checked_at": camp.last_checked_at,
            "verification_status": camp.verification_status,
            "event_status": camp.event_status,
            "followup_instructions": camp.followup_instructions,
            "followup_facility_id": camp.followup_facility_id,
            "provenance": camp.provenance or {},
            "distance_km": None,
            "created_at": camp.created_at,
            "updated_at": camp.updated_at,
        }
        return HealthCampOut(**camp_dict)

    @staticmethod
    async def get_district_coverage(session: AsyncSession) -> DistrictCoverageResponse:
        """
        Aggregate comprehensive statewide coverage across all 38 canonical Tamil Nadu districts.
        Distinguishes between verified event coverage, no published events, and insufficient data.
        """
        now = datetime.now(timezone.utc)

        # 1. Count upcoming verified camps per district
        camp_counts_stmt = select(
            HealthCamp.district, func.count(HealthCamp.id)
        ).where(
            and_(
                HealthCamp.verification_status == "VERIFIED",
                HealthCamp.event_status == "UPCOMING",
                HealthCamp.start_date >= now - timedelta(hours=4),
            )
        ).group_by(HealthCamp.district)

        camp_res = await session.execute(camp_counts_stmt)
        camps_by_dist = dict(camp_res.all())

        # 2. Query source statuses and last check timestamps
        sources_stmt = select(HealthCampSource)
        src_res = await session.execute(sources_stmt)
        sources = list(src_res.scalars().all())

        latest_check_all = None
        for s in sources:
            if s.last_checked_at:
                if not latest_check_all or s.last_checked_at > latest_check_all:
                    latest_check_all = s.last_checked_at

        # Map district sources
        dist_sources: Dict[str, List[HealthCampSource]] = {}
        for s in sources:
            if s.district:
                d = normalize_tn_district(s.district) or s.district
                dist_sources.setdefault(d, []).append(s)

        # Build coverage items for all 38 districts
        coverage_items: List[DistrictCoverageItem] = []
        total_verified_camps = 0
        districts_with_events = 0

        for canon_name, meta in sorted(TN_DISTRICTS.items()):
            cnt = camps_by_dist.get(canon_name, 0)
            total_verified_camps += cnt
            if cnt > 0:
                districts_with_events += 1

            # Determine check status and last check date
            district_srcs = dist_sources.get(canon_name, [])
            last_checked = None
            check_status = "SUCCESS"

            if district_srcs:
                for ds in district_srcs:
                    if ds.last_checked_at:
                        if not last_checked or ds.last_checked_at > last_checked:
                            last_checked = ds.last_checked_at
                    if ds.last_status == "ERROR":
                        check_status = "ERROR"
            else:
                # Inherits from statewide source check status
                last_checked = latest_check_all
                check_status = "SUCCESS" if latest_check_all else "PENDING"

            # Determine coverage classification
            if cnt > 0:
                cov_status = "VERIFIED_EVENTS_AVAILABLE"
            elif check_status == "SUCCESS" and last_checked is not None:
                cov_status = "NO_PUBLISHED_EVENTS"
            else:
                cov_status = "INSUFFICIENT_DATA"

            coverage_items.append(
                DistrictCoverageItem(
                    district=canon_name,
                    district_ta=meta["name_ta"],
                    headquarters=meta["headquarters"],
                    portal_url=meta["portal_url"],
                    verified_events_count=cnt,
                    last_checked_at=last_checked,
                    check_status=check_status,
                    coverage_status=cov_status,
                )
            )

        return DistrictCoverageResponse(
            districts=coverage_items,
            total_districts=len(coverage_items),
            total_verified_camps=total_verified_camps,
            districts_with_events_count=districts_with_events,
            monitored_sources_count=len(sources),
            last_collection_timestamp=latest_check_all,
        )

    @staticmethod
    async def update_camp_verification(
        session: AsyncSession, camp_id: uuid.UUID, update_in: CampVerificationUpdateIn
    ) -> Optional[HealthCampOut]:
        """Administrative review action to confirm, flag, reject, or postpone a camp."""
        stmt = select(HealthCamp).where(HealthCamp.id == camp_id)
        res = await session.execute(stmt)
        camp = res.scalars().first()
        if not camp:
            return None

        camp.verification_status = update_in.verification_status
        if update_in.event_status:
            camp.event_status = update_in.event_status
        if update_in.followup_instructions:
            camp.followup_instructions = update_in.followup_instructions
        if update_in.notes:
            prov = dict(camp.provenance or {})
            prov["admin_notes"] = update_in.notes
            prov["reviewed_at"] = datetime.now(timezone.utc).isoformat()
            camp.provenance = prov

        await session.commit()
        await session.refresh(camp)
        return await CampService.get_camp_by_id(session, camp_id)

    @staticmethod
    async def sync_all_sources(session: AsyncSession) -> Dict[str, Any]:
        """Execute scheduled collection for all active official sources."""
        # Ensure default sources exist
        await CampCollectorService.initialize_default_sources(session)

        stmt = select(HealthCampSource).where(HealthCampSource.is_active == True)
        res = await session.execute(stmt)
        sources = list(res.scalars().all())

        total_new_events = 0
        success_count = 0
        failure_count = 0
        results_summary = []

        for src in sources:
            ok, new_cnt, err = await CampCollectorService.run_collector_for_source(session, src)
            if ok:
                success_count += 1
                total_new_events += new_cnt
            else:
                failure_count += 1
            results_summary.append({
                "source": src.name,
                "status": "SUCCESS" if ok else "ERROR",
                "new_events": new_cnt,
                "error": err,
            })

        return {
            "sources_processed": len(sources),
            "sources_succeeded": success_count,
            "sources_failed": failure_count,
            "total_new_events": total_new_events,
            "details": results_summary,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    async def get_user_preferences(session: AsyncSession, user_id: uuid.UUID) -> UserCampPreferenceOut:
        """Fetch user camp notification preferences."""
        stmt = select(UserCampPreference).where(UserCampPreference.user_id == user_id)
        res = await session.execute(stmt)
        pref = res.scalars().first()
        if not pref:
            # Return defaults
            return UserCampPreferenceOut(
                user_id=user_id,
                opt_in=True,
                preferred_districts=[],
                max_distance_km=30,
                notify_categories=[],
            )
        return UserCampPreferenceOut.from_orm(pref)

    @staticmethod
    async def update_user_preferences(
        session: AsyncSession, user_id: uuid.UUID, pref_in: UserCampPreferenceIn
    ) -> UserCampPreferenceOut:
        """Update user camp notification preferences."""
        stmt = select(UserCampPreference).where(UserCampPreference.user_id == user_id)
        res = await session.execute(stmt)
        pref = res.scalars().first()

        if not pref:
            pref = UserCampPreference(
                user_id=user_id,
                opt_in=pref_in.opt_in,
                preferred_districts=pref_in.preferred_districts,
                max_distance_km=pref_in.max_distance_km,
                notify_categories=pref_in.notify_categories,
            )
            session.add(pref)
        else:
            pref.opt_in = pref_in.opt_in
            pref.preferred_districts = pref_in.preferred_districts
            pref.max_distance_km = pref_in.max_distance_km
            pref.notify_categories = pref_in.notify_categories

        await session.commit()
        await session.refresh(pref)
        return UserCampPreferenceOut.from_orm(pref)
