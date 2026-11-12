from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.facility import Facility
from app.models.medicine import Medicine
from app.models.stock import StockReport
from app.schemas.shared import (
    AvailabilityItem,
    AvailabilityStatus,
    BeliefSnapshot,
    Role,
    SourceType,
    StockReportOut,
)
from app.services.availability_service import AvailabilityService


class StockService:
    def __init__(self, db: AsyncSession, availability_service: Optional[AvailabilityService] = None):
        self.db = db
        self.availability_service = availability_service or AvailabilityService(db)

    @staticmethod
    def role_to_source_type(role: str) -> SourceType:
        """Map authenticated user role to server-derived SourceType.

        CRITICAL: Never trust client-provided source_type.
        """
        r = role.upper() if isinstance(role, str) else role.value
        if r in (Role.STAFF.value, Role.ADMIN.value, Role.DOCTOR.value):
            return SourceType.STAFF
        elif r == Role.ASHA.value:
            return SourceType.ASHA
        elif r == Role.PATIENT.value:
            return SourceType.PATIENT
        return SourceType.PATIENT

    async def create_report(
        self,
        facility_id: UUID,
        medicine_id: UUID,
        availability_status: AvailabilityStatus,
        reporter_id: UUID,
        caller_role: str,
        notes: Optional[str] = None,
    ) -> StockReportOut:
        """Append stock report to ledger and update availability belief state."""
        # Validate existence of facility and medicine
        f_stmt = select(Facility).where(Facility.id == facility_id)
        f_res = await self.db.execute(f_stmt)
        if not f_res.scalar_one_or_none():
            raise ValueError(f"Facility with id {facility_id} does not exist")

        m_stmt = select(Medicine).where(Medicine.id == medicine_id)
        m_res = await self.db.execute(m_stmt)
        if not m_res.scalar_one_or_none():
            raise ValueError(f"Medicine with id {medicine_id} does not exist")

        # Derive source_type strictly on server
        source_type = self.role_to_source_type(caller_role)

        report = StockReport(
            facility_id=facility_id,
            medicine_id=medicine_id,
            reporter_id=reporter_id,
            source_type=source_type.value,
            availability_status=availability_status.value,
            verification_status="PENDING",
            notes=notes,
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)

        # Update belief state
        belief = await self.availability_service.update_belief_state(facility_id, medicine_id)

        return StockReportOut(
            report_id=report.id,
            verification_status=report.verification_status,
            updated=BeliefSnapshot(
                p_available=belief.p_available,
                confidence=belief.confidence,
            ),
        )

    async def get_availability(
        self,
        medicine_id: UUID,
        facility_ids: Optional[List[UUID]] = None,
    ) -> List[AvailabilityItem]:
        """Query availability across specified facilities or all facilities."""
        m_stmt = select(Medicine).where(Medicine.id == medicine_id)
        m_res = await self.db.execute(m_stmt)
        if not m_res.scalar_one_or_none():
            raise ValueError(f"Medicine with id {medicine_id} does not exist")

        f_stmt = select(Facility)
        if facility_ids:
            f_stmt = f_stmt.where(Facility.id.in_(facility_ids))

        f_res = await self.db.execute(f_stmt)
        facilities = list(f_res.scalars().all())

        results: List[AvailabilityItem] = []
        for fac in facilities:
            p_avail, conf, label, count, last_rep = await self.availability_service.calculate_belief(
                fac.id, medicine_id
            )
            results.append(
                AvailabilityItem(
                    facility_id=fac.id,
                    p_available=p_avail,
                    confidence=conf,
                    label=label,
                    evidence_count=count,
                    last_report_at=last_rep,
                )
            )

        return results
