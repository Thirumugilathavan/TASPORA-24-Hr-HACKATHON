from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import check_patient_ownership, get_current_user
from app.models.appointment import Appointment
from app.models.request import HealthcareRequest
from app.models.user import User
from app.schemas.shared import AppointmentIn, AppointmentOut, AppointmentStatus, Role
from app.schemas.workflow import AppointmentCancelOut, AppointmentDetailOut

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.post(
    "",
    response_model=AppointmentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Book an appointment with double-booking prevention",
)
async def create_appointment(
    payload: AppointmentIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Book an appointment with transactional double-booking prevention.

    Conflict Prevention:
    - If doctor_id is provided: Prevents another active booking for the same doctor, date, and time.
    - If doctor_id is null: Prevents another unassigned booking for the same facility, date, and time.
    Returns HTTP 409 CONFLICT if the requested slot is already taken.
    """
    # 1. Authorization check
    if not await check_patient_ownership(db, current_user, payload.patient_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "FORBIDDEN",
                    "message": "Patients can only book appointments for their own account.",
                }
            },
        )

    # 2. Verify associated healthcare request if provided
    if payload.request_id is not None:
        req_stmt = select(HealthcareRequest).where(HealthcareRequest.id == payload.request_id)
        req_res = await db.execute(req_stmt)
        if not req_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Referenced healthcare request not found.",
                    }
                },
            )

    # 3. Application-level conflict check
    if payload.doctor_id is not None:
        conflict_stmt = select(Appointment).where(
            and_(
                Appointment.doctor_id == payload.doctor_id,
                Appointment.appointment_date == payload.appointment_date,
                Appointment.appointment_time == payload.appointment_time,
                Appointment.status != AppointmentStatus.CANCELLED,
            )
        )
    else:
        conflict_stmt = select(Appointment).where(
            and_(
                Appointment.facility_id == payload.facility_id,
                Appointment.doctor_id.is_(None),
                Appointment.appointment_date == payload.appointment_date,
                Appointment.appointment_time == payload.appointment_time,
                Appointment.status != AppointmentStatus.CANCELLED,
            )
        )

    conflict_res = await db.execute(conflict_stmt)
    if conflict_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "SLOT_TAKEN",
                    "message": "Appointment slot is already booked for this date and time.",
                }
            },
        )

    # 4. Insert appointment record
    new_appointment = Appointment(
        patient_id=payload.patient_id,
        facility_id=payload.facility_id,
        doctor_id=payload.doctor_id,
        request_id=payload.request_id,
        appointment_date=payload.appointment_date,
        appointment_time=payload.appointment_time,
        status=AppointmentStatus.BOOKED,
    )

    db.add(new_appointment)
    try:
        await db.commit()
        await db.refresh(new_appointment)
    except IntegrityError:
        # Catches concurrent race condition enforced by the partial unique index
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "SLOT_TAKEN",
                    "message": "Appointment slot was just booked by another concurrent request.",
                }
            },
        )

    return AppointmentOut(
        id=new_appointment.id,
        status=new_appointment.status,
    )


@router.get(
    "/{id}",
    response_model=AppointmentDetailOut,
    status_code=status.HTTP_200_OK,
    summary="Retrieve appointment details by ID",
)
async def get_appointment(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve details of an appointment."""
    stmt = select(Appointment).where(Appointment.id == id)
    res = await db.execute(stmt)
    appt = res.scalar_one_or_none()

    if not appt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Appointment not found.",
                }
            },
        )

    if not await check_patient_ownership(db, current_user, appt.patient_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "FORBIDDEN",
                    "message": "You do not have permission to view this appointment.",
                }
            },
        )

    return appt


@router.patch(
    "/{id}/cancel",
    response_model=AppointmentCancelOut,
    status_code=status.HTTP_200_OK,
    summary="Cancel an existing appointment and release slot",
)
async def cancel_appointment(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel an appointment and release the reserved slot."""
    stmt = select(Appointment).where(Appointment.id == id)
    res = await db.execute(stmt)
    appt = res.scalar_one_or_none()

    if not appt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Appointment not found.",
                }
            },
        )

    if not await check_patient_ownership(db, current_user, appt.patient_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "FORBIDDEN",
                    "message": "You do not have permission to cancel this appointment.",
                }
            },
        )

    if appt.status != AppointmentStatus.CANCELLED:
        appt.status = AppointmentStatus.CANCELLED
        await db.commit()
        await db.refresh(appt)

    return AppointmentCancelOut(
        id=appt.id,
        status=appt.status,
    )
