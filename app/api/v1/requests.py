from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import check_patient_ownership, get_current_user
from app.models.patient import Patient
from app.models.request import HealthcareRequest
from app.models.user import User
from app.schemas.shared import RequestIn, RequestOut, Role
from app.schemas.workflow import RequestDetailOut

router = APIRouter(prefix="/requests", tags=["Healthcare Requests"])


@router.post(
    "",
    response_model=RequestOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new healthcare request",
)
@router.post(
    "/",
    response_model=RequestOut,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_request(
    payload: RequestIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a patient healthcare request (Consultation, Refill, Checkup, Diagnostic, Camp Follow-up, Scheme Assistance).

    Authorization:
    - PATIENT users can only initiate requests for their own account.
    - ASHA, DOCTOR, STAFF, and ADMIN users may initiate requests on behalf of any patient.
    """
    if not await check_patient_ownership(db, current_user, payload.patient_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "FORBIDDEN",
                    "message": "Patients can only create healthcare requests for their own account.",
                }
            },
        )

    # Derive default title if not provided
    req_title = payload.title
    if not req_title:
        type_str = payload.request_type.value.replace("_", " ").title()
        req_title = f"{type_str} Request"

    new_request = HealthcareRequest(
        patient_id=payload.patient_id,
        request_type=payload.request_type,
        title=req_title,
        medicine_id=payload.medicine_id,
        facility_id=payload.facility_id,
        camp_id=payload.camp_id,
        preferred_date=payload.preferred_date,
        contact_phone=payload.contact_phone or getattr(current_user, "phone", None),
        extra_metadata=payload.extra_metadata,
        description=payload.description or "",
        urgency=payload.urgency,
        status="PENDING",
    )

    db.add(new_request)
    await db.commit()
    await db.refresh(new_request)

    return RequestOut(
        id=new_request.id,
        status=new_request.status,
        created_at=new_request.created_at,
        patient_id=new_request.patient_id,
        request_type=new_request.request_type,
        title=new_request.title,
        medicine_id=new_request.medicine_id,
        facility_id=new_request.facility_id,
        camp_id=new_request.camp_id,
        preferred_date=new_request.preferred_date,
        contact_phone=new_request.contact_phone,
        extra_metadata=new_request.extra_metadata,
        description=new_request.description,
        urgency=new_request.urgency,
    )


@router.get(
    "",
    response_model=List[RequestDetailOut],
    status_code=status.HTTP_200_OK,
    summary="List healthcare requests for current user or system",
)
@router.get(
    "/",
    response_model=List[RequestDetailOut],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def list_requests(
    patient_id: Optional[UUID] = Query(None, description="Filter by patient ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (PENDING, RECOMMENDED, BOOKED, COMPLETED)"),
    camp_id: Optional[UUID] = Query(None, description="Filter by linked health camp ID"),
    facility_id: Optional[UUID] = Query(None, description="Filter by linked facility ID"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve list of healthcare requests accessible to the authenticated user.

    - PATIENT users see their own requests (by User ID or Patient profile ID).
    - Healthcare workers (ASHA, DOCTOR, STAFF, ADMIN) see all requests or filtered by patient.
    """
    stmt = select(HealthcareRequest)

    if current_user.role == Role.PATIENT.value:
        # Determine allowed patient IDs for this patient user
        p_stmt = select(Patient.id).where(Patient.user_id == current_user.id)
        p_res = await db.execute(p_stmt)
        patient_prof_id = p_res.scalar_one_or_none()
        
        allowed_ids = [current_user.id]
        if patient_prof_id:
            allowed_ids.append(patient_prof_id)

        if patient_id:
            if patient_id not in allowed_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": {
                            "code": "FORBIDDEN",
                            "message": "Patients can only view requests for their own account.",
                        }
                    },
                )
            stmt = stmt.where(HealthcareRequest.patient_id == patient_id)
        else:
            stmt = stmt.where(HealthcareRequest.patient_id.in_(allowed_ids))
    elif patient_id:
        stmt = stmt.where(HealthcareRequest.patient_id == patient_id)

    if status_filter and status_filter.upper() != "ALL":
        stmt = stmt.where(HealthcareRequest.status == status_filter.upper())

    if camp_id:
        stmt = stmt.where(HealthcareRequest.camp_id == camp_id)

    if facility_id:
        stmt = stmt.where(HealthcareRequest.facility_id == facility_id)

    stmt = stmt.order_by(HealthcareRequest.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get(
    "/{id}",
    response_model=RequestDetailOut,
    status_code=status.HTTP_200_OK,
    summary="Retrieve healthcare request by ID",
)
@router.get(
    "/{id}/",
    response_model=RequestDetailOut,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def get_request(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve details of an existing healthcare request.

    Authorization:
    - PATIENT users can only view their own requests.
    - Healthcare workers (ASHA, DOCTOR, STAFF, ADMIN) can view any request.
    """
    stmt = select(HealthcareRequest).where(HealthcareRequest.id == id)
    result = await db.execute(stmt)
    req = result.scalar_one_or_none()

    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Healthcare request not found.",
                }
            },
        )

    if not await check_patient_ownership(db, current_user, req.patient_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "FORBIDDEN",
                    "message": "You do not have permission to view this healthcare request.",
                }
            },
        )

    return req
