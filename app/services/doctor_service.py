from datetime import date, datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.doctor import Doctor, DoctorSchedule
from app.models.facility import Facility
from app.schemas.doctor import (
    DoctorCreate,
    DoctorScheduleCreate,
    DoctorScheduleDetailResponse,
    DoctorScheduleResponse,
)
from app.schemas.shared import AttendanceStatus


class DoctorServiceHandler:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_doctors(
        self,
        facility_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Doctor], int]:
        """List doctors with optional facility filtering."""
        stmt = select(Doctor)
        if facility_id:
            stmt = stmt.where(Doctor.facility_id == facility_id)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_res = await self.db.execute(count_stmt)
        total = count_res.scalar_one()

        items_stmt = stmt.offset(skip).limit(limit)
        items_res = await self.db.execute(items_stmt)
        items = list(items_res.scalars().all())

        return items, total

    async def get_doctor_schedule(
        self,
        doctor_id: UUID,
        target_date: Optional[date] = None,
    ) -> Optional[DoctorScheduleDetailResponse]:
        """Retrieve doctor schedule and attendance status.

        CRITICAL: Never invents doctor attendance.
        If no schedule is logged, returns UNKNOWN.
        EXPECTED denotes planned shift, not confirmed attendance.
        """
        d_stmt = select(Doctor).where(Doctor.id == doctor_id)
        d_res = await self.db.execute(d_stmt)
        doctor = d_res.scalar_one_or_none()
        if not doctor:
            return None

        query_date = target_date or date.today()

        s_stmt = select(DoctorSchedule).where(
            DoctorSchedule.doctor_id == doctor_id,
            DoctorSchedule.schedule_date == query_date,
        )
        s_res = await self.db.execute(s_stmt)
        schedule = s_res.scalar_one_or_none()

        if schedule:
            schedule_dto = DoctorScheduleResponse(
                id=schedule.id,
                doctor_id=schedule.doctor_id,
                facility_id=schedule.facility_id,
                schedule_date=schedule.schedule_date,
                start_time=schedule.start_time,
                end_time=schedule.end_time,
                attendance_status=AttendanceStatus(schedule.attendance_status),
                last_verified_at=schedule.last_verified_at,
                verified_by=schedule.verified_by,
                notes=schedule.notes,
                created_at=schedule.created_at,
                updated_at=schedule.updated_at,
            )
            return DoctorScheduleDetailResponse(
                doctor_id=doctor.id,
                doctor_name=doctor.name,
                facility_id=doctor.facility_id,
                date=query_date,
                attendance_status=AttendanceStatus(schedule.attendance_status),
                last_verified_at=schedule.last_verified_at,
                schedule=schedule_dto,
            )
        else:
            return DoctorScheduleDetailResponse(
                doctor_id=doctor.id,
                doctor_name=doctor.name,
                facility_id=doctor.facility_id,
                date=query_date,
                attendance_status=AttendanceStatus.UNKNOWN,
                last_verified_at=None,
                schedule=None,
            )

    async def create_doctor(self, data: DoctorCreate) -> Doctor:
        """Register a new doctor at a facility."""
        f_stmt = select(Facility).where(Facility.id == data.facility_id)
        f_res = await self.db.execute(f_stmt)
        facility = f_res.scalar_one_or_none()
        if not facility:
            raise ValueError(f"Facility with id {data.facility_id} does not exist")

        doctor = Doctor(
            facility_id=data.facility_id,
            name=data.name,
            specialization=data.specialization,
            qualification=data.qualification,
            contact_phone=data.contact_phone,
        )
        self.db.add(doctor)
        await self.db.commit()
        await self.db.refresh(doctor)
        return doctor

    async def create_schedule(self, data: DoctorScheduleCreate) -> DoctorSchedule:
        """Register a planned doctor schedule."""
        sched = DoctorSchedule(
            doctor_id=data.doctor_id,
            facility_id=data.facility_id,
            schedule_date=data.schedule_date,
            start_time=data.start_time,
            end_time=data.end_time,
            attendance_status=data.attendance_status.value if hasattr(data.attendance_status, "value") else str(data.attendance_status),
            notes=data.notes,
        )
        self.db.add(sched)
        await self.db.commit()
        await self.db.refresh(sched)
        return sched

    async def verify_attendance(
        self,
        doctor_id: UUID,
        target_date: date,
        status: AttendanceStatus,
        verified_by: Optional[UUID] = None,
    ) -> DoctorSchedule:
        """Record verified attendance (PRESENT / ABSENT)."""
        s_stmt = select(DoctorSchedule).where(
            DoctorSchedule.doctor_id == doctor_id,
            DoctorSchedule.schedule_date == target_date,
        )
        s_res = await self.db.execute(s_stmt)
        sched = s_res.scalar_one_or_none()

        status_str = status.value if hasattr(status, "value") else str(status)

        if not sched:
            d_stmt = select(Doctor).where(Doctor.id == doctor_id)
            d_res = await self.db.execute(d_stmt)
            doctor = d_res.scalar_one_or_none()
            if not doctor:
                raise ValueError(f"Doctor {doctor_id} not found")

            sched = DoctorSchedule(
                doctor_id=doctor_id,
                facility_id=doctor.facility_id,
                schedule_date=target_date,
                attendance_status=status_str,
                last_verified_at=datetime.now(timezone.utc),
                verified_by=verified_by,
            )
            self.db.add(sched)
        else:
            sched.attendance_status = status_str
            sched.last_verified_at = datetime.now(timezone.utc)
            sched.verified_by = verified_by

        await self.db.commit()
        await self.db.refresh(sched)
        return sched
