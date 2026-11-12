from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.doctor import Doctor
from app.models.facility import Facility, FacilityService
from app.models.village import Village
from app.schemas.facility import (
    DoctorSummary,
    FacilityCreate,
    FacilityDetailResponse,
    FacilityServiceResponse,
)


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
            latitude=facility.latitude,
            longitude=facility.longitude,
            contact_details=facility.contact_details,
            services=services_data,
            doctors=doctors_data,
            created_at=facility.created_at,
            updated_at=facility.updated_at,
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
            latitude=data.latitude,
            longitude=data.longitude,
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
