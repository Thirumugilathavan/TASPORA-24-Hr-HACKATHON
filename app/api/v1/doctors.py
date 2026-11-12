from datetime import date
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.doctor import (
    DoctorCreate,
    DoctorResponse,
    DoctorScheduleCreate,
    DoctorScheduleDetailResponse,
    DoctorScheduleResponse,
)
from app.schemas.shared import AttendanceStatus, Page
from app.services.doctor_service import DoctorServiceHandler

router = APIRouter(prefix="/doctors", tags=["Doctors & Schedules"])


@router.get("", response_model=Page[DoctorResponse])
async def get_doctors(
    facility_id: Optional[UUID] = Query(None, description="Filter doctors by facility UUID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List doctors, optionally filtered by healthcare facility."""
    handler = DoctorServiceHandler(db)
    items, total = await handler.list_doctors(facility_id=facility_id, skip=skip, limit=limit)
    return Page(items=items, total=total)


@router.get("/{id}/schedule", response_model=DoctorScheduleDetailResponse)
async def get_doctor_schedule(
    id: UUID,
    date: Optional[date] = Query(None, description="Schedule date (YYYY-MM-DD), defaults to current date"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve doctor schedule and attendance status.

    IMPORTANT:
    Clearly distinguishes EXPECTED (planned) vs confirmed verified attendance (PRESENT / ABSENT).
    Does not invent doctor attendance.
    """
    handler = DoctorServiceHandler(db)
    schedule_detail = await handler.get_doctor_schedule(id, target_date=date)
    if not schedule_detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": f"Doctor {id} not found"}},
        )
    return schedule_detail


@router.post("", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
async def create_doctor(
    payload: DoctorCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new doctor."""
    handler = DoctorServiceHandler(db)
    try:
        return await handler.create_doctor(payload)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "BAD_REQUEST", "message": str(e)}},
        )


@router.post("/{id}/schedule", response_model=DoctorScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_doctor_schedule(
    id: UUID,
    payload: DoctorScheduleCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a planned doctor shift schedule (defaults to EXPECTED attendance)."""
    handler = DoctorServiceHandler(db)
    payload.doctor_id = id
    return await handler.create_schedule(payload)


@router.post("/{id}/verify-attendance", response_model=DoctorScheduleResponse)
async def verify_doctor_attendance(
    id: UUID,
    date: date = Query(..., description="Date to verify attendance for (YYYY-MM-DD)"),
    attendance_status: AttendanceStatus = Query(..., description="PRESENT or ABSENT"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record verified attendance (PRESENT / ABSENT) for a doctor."""
    handler = DoctorServiceHandler(db)
    try:
        return await handler.verify_attendance(
            doctor_id=id,
            target_date=date,
            status=attendance_status,
            verified_by=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": str(e)}},
        )
