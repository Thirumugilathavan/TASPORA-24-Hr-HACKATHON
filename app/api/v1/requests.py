from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
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
async def create_request(
    payload: RequestIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a patient healthcare request (Consultation, Refill, Checkup, Diagnostic).

    Authorization:
    - PATIENT users can only initiate requests for their own account.
    - ASHA, DOCTOR, STAFF, and ADMIN users may initiate requests on behalf of any patient.
    """
    if current_user.role == Role.PATIENT.value and payload.patient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "FORBIDDEN",
                    "message": "Patients can only create healthcare requests for their own account.",
                }
            },
        )

    new_request = HealthcareRequest(
        patient_id=payload.patient_id,
        request_type=payload.request_type,
        medicine_id=payload.medicine_id,
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
    )


@router.get(
    "/{id}",
    response_model=RequestDetailOut,
    status_code=status.HTTP_200_OK,
    summary="Retrieve healthcare request by ID",
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

    if current_user.role == Role.PATIENT.value and req.patient_id != current_user.id:
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
