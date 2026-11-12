import math
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.doctor import Doctor
from app.models.facility import Facility, FacilityService
from app.models.patient import Patient
from app.models.village import Village
from app.schemas.facility import (
    DoctorSummary,
    FacilityCreate,
    FacilityDetailResponse,
    FacilityResponse,
    FacilityServiceResponse,
    NearbyFacilityList,
    NearbyFacilityResponse,
)
from app.services.distance_service import haversine_km, validate_coordinates


class FacilityServiceHandler:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_facilities(
        self,
        village_id: Optional[UUID] = None,
        facility_type: Optional[str] = None,
        service: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Facility], int]:
        """List facilities with multi-criteria filtering."""
        stmt = select(Facility)

        if village_id:
            stmt = stmt.where(Facility.village_id == village_id)

        if facility_type:
            stmt = stmt.where(func.upper(Facility.facility_type) == facility_type.upper())

        if service:
            stmt = (
                stmt.join(Facility.services)
                .where(func.lower(FacilityService.service_name).contains(service.lower()))
                .distinct()
            )

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_res = await self.db.execute(count_stmt)
        total = count_res.scalar_one()

        items_stmt = stmt.offset(skip).limit(limit)
        items_res = await self.db.execute(items_stmt)
        items = list(items_res.scalars().all())

        return items, total

    async def get_facility(self, facility_id: UUID) -> Optional[FacilityDetailResponse]:
        """Retrieve facility detail including services[] and doctors[]."""
        stmt = (
            select(Facility)
            .where(Facility.id == facility_id)
            .options(
                selectinload(Facility.services),
                selectinload(Facility.doctors),
            )
        )
        res = await self.db.execute(stmt)
        facility = res.scalar_one_or_none()

        if not facility:
            return None

        services_data = [
            FacilityServiceResponse(
                id=s.id,
                service_name=s.service_name,
                description=s.description,
                created_at=s.created_at,
            )
            for s in facility.services
        ]

        doctors_data = [
            DoctorSummary(
                id=d.id,
                name=d.name,
                specialization=d.specialization,
                qualification=d.qualification,
                contact_phone=d.contact_phone,
            )
            for d in facility.doctors
        ]

        return FacilityDetailResponse(
            id=facility.id,
            name=facility.name,
            facility_type=facility.facility_type,
            address=facility.address,
            village_id=facility.village_id,
            district=facility.district,
            state=facility.state,
            subdistrict=facility.subdistrict,
            latitude=facility.latitude,
            longitude=facility.longitude,
            ownership=facility.ownership,
            source=facility.source,
            source_id=facility.source_id,
            contact_details=facility.contact_details,
            services=services_data,
            doctors=doctors_data,
            created_at=facility.created_at,
            updated_at=facility.updated_at,
        )

    async def get_nearby_facilities(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        village_id: Optional[UUID] = None,
        patient_id: Optional[UUID] = None,
        radius_km: float = 10.0,
        facility_type: Optional[str] = None,
        limit: int = 20,
        skip: int = 0,
    ) -> NearbyFacilityList:
        """
        Calculates geographic distance and returns nearby healthcare facilities
        ranked in strict ascending order of distance (nearest first).
        Uses indexed bounding-box query for sub-millisecond retrieval across 147k+ facilities.
        """
        resolved_lat: float
        resolved_lon: float
        resolved_name: str
        resolved_source: str
        resolved_meta: Dict[str, Any] = {}

        if lat is not None and lon is not None:
            validate_coordinates(lat, lon, "Query coordinates")
            resolved_lat = float(lat)
            resolved_lon = float(lon)
            resolved_source = "coordinates"
            resolved_name = f"Coordinates ({resolved_lat:.4f}, {resolved_lon:.4f})"
        elif village_id is not None:
            v_stmt = select(Village).where(Village.id == village_id)
            v_res = await self.db.execute(v_stmt)
            village = v_res.scalar_one_or_none()
            if not village:
                raise ValueError(f"Village with ID '{village_id}' not found")
            resolved_lat = village.latitude
            resolved_lon = village.longitude
            resolved_source = "village"
            resolved_name = f"{village.name} ({village.district}, {village.state or ''})"
            resolved_meta = {
                "village_id": str(village.id),
                "name": village.name,
                "district": village.district,
                "state": village.state,
                "subdistrict": village.subdistrict,
            }
        elif patient_id is not None:
            p_stmt = select(Patient).where((Patient.id == patient_id) | (Patient.user_id == patient_id))
            p_res = await self.db.execute(p_stmt)
            patient = p_res.scalar_one_or_none()
            if not patient:
                raise ValueError(f"Patient with ID '{patient_id}' not found")
            v_stmt = select(Village).where(Village.id == patient.village_id)
            v_res = await self.db.execute(v_stmt)
            village = v_res.scalar_one_or_none()
            if not village:
                raise ValueError(f"Patient's registered village with ID '{patient.village_id}' not found")
            resolved_lat = village.latitude
            resolved_lon = village.longitude
            resolved_source = "patient_village"
            resolved_name = f"{village.name} ({village.district}, {village.state or ''})"
            resolved_meta = {
                "patient_id": str(patient.id),
                "village_id": str(village.id),
                "name": village.name,
                "district": village.district,
                "state": village.state,
                "subdistrict": village.subdistrict,
            }
        else:
            raise ValueError("Must provide either latitude & longitude, village_id, or patient_id")

        if radius_km <= 0 or radius_km > 500:
            raise ValueError("radius_km must be between 0.1 and 500.0 km")

        # Compute bounding box using index on (latitude, longitude)
        lat_delta = radius_km / 111.0
        cos_lat = max(math.cos(math.radians(resolved_lat)), 0.01)
        lon_delta = radius_km / (111.0 * cos_lat)

        min_lat = resolved_lat - lat_delta
        max_lat = resolved_lat + lat_delta
        min_lon = resolved_lon - lon_delta
        max_lon = resolved_lon + lon_delta

        stmt = select(Facility).where(
            Facility.latitude.between(min_lat, max_lat),
            Facility.longitude.between(min_lon, max_lon),
        )

        if facility_type and facility_type.upper() != "ALL":
            ft = facility_type.upper()
            if ft in ("HOSPITAL", "THO", "DHO"):
                stmt = stmt.where(func.upper(Facility.facility_type).in_(["HOSPITAL", "THO", "DHO"]))
            elif ft in ("SCE", "SUB_CENTRE", "SUB-CENTRE", "SUB_CENTER", "SUB-CENTER"):
                stmt = stmt.where(func.upper(Facility.facility_type).in_(["SCE", "SUB_CENTRE", "SUB_CENTER"]))
            elif ft == "PHC":
                stmt = stmt.where(func.upper(Facility.facility_type) == "PHC")
            elif ft == "CHC":
                stmt = stmt.where(func.upper(Facility.facility_type) == "CHC")
            else:
                stmt = stmt.where(func.upper(Facility.facility_type) == ft)

        result = await self.db.execute(stmt)
        candidates = result.scalars().all()

        # Compute exact Haversine distance and filter
        ranked = []
        for f in candidates:
            if f.latitude is None or f.longitude is None:
                continue
            try:
                exact_dist = haversine_km(resolved_lat, resolved_lon, f.latitude, f.longitude)
            except ValueError:
                continue

            if exact_dist <= radius_km:
                ranked.append((f, exact_dist))

        # Automatic distance-based ranking: ascending distance, stable tie-break by name
        ranked.sort(key=lambda x: (x[1], x[0].name or ""))

        total_matching = len(ranked)
        paged = ranked[skip : skip + limit]

        items = []
        for f, d in paged:
            items.append(
                NearbyFacilityResponse(
                    id=f.id,
                    name=f.name,
                    facility_type=f.facility_type,
                    address=f.address,
                    village_id=f.village_id,
                    district=f.district,
                    state=f.state,
                    subdistrict=f.subdistrict,
                    latitude=f.latitude,
                    longitude=f.longitude,
                    ownership=f.ownership or "Government",
                    source=f.source or "nic",
                    source_id=f.source_id,
                    contact_details=f.contact_details,
                    distance_km=round(d, 2),
                    unverified_availability=True,
                    directions_url=f"https://www.google.com/maps/dir/?api=1&destination={f.latitude},{f.longitude}",
                    created_at=f.created_at,
                    updated_at=f.updated_at,
                )
            )

        resolved_location_info = {
            "latitude": resolved_lat,
            "longitude": resolved_lon,
            "source": resolved_source,
            "label": resolved_name,
            **resolved_meta,
        }

        has_more = (skip + len(items)) < total_matching

        return NearbyFacilityList(
            items=items,
            total=total_matching,
            resolved_location=resolved_location_info,
            radius_km=radius_km,
            skip=skip,
            limit=limit,
            has_more=has_more,
        )

    async def create_facility(self, data: FacilityCreate) -> Facility:
        """Create new facility with initial service records."""
        # Validate that village exists
        v_stmt = select(Village).where(Village.id == data.village_id)
        v_res = await self.db.execute(v_stmt)
        if not v_res.scalar_one_or_none():
            raise ValueError(f"Village with id {data.village_id} does not exist")

        facility = Facility(
            name=data.name,
            facility_type=data.facility_type,
            address=data.address,
            village_id=data.village_id,
            district=data.district or "",
            state=data.state or "",
            subdistrict=data.subdistrict or "",
            latitude=data.latitude,
            longitude=data.longitude,
            ownership=data.ownership or "Government",
            source=data.source or "nic",
            source_id=data.source_id,
            contact_details=data.contact_details,
        )
        self.db.add(facility)
        await self.db.flush()

        if data.services:
            for s_name in data.services:
                serv = FacilityService(
                    facility_id=facility.id,
                    service_name=s_name,
                    description=f"{s_name} provided at {facility.name}",
                )
                self.db.add(serv)

        await self.db.commit()
        await self.db.refresh(facility)
        return facility
