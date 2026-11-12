from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.patient_village import PatientDetailOut, PatientIn, PatientOut
from app.services.patient_service import PatientService

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.post(
    "",
    response_model=PatientOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create patient profile",
    description="Registers a new patient profile associated with the authenticated user and village.",
)
async def create_patient(
    data: PatientIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PatientOut:
    return await PatientService.create_patient(db, current_user, data)


@router.get(
    "/{id}",
    response_model=PatientDetailOut,
    status_code=status.HTTP_200_OK,
    summary="Get patient profile by ID",
    description="Retrieves the detailed patient profile including demographic and village data.",
)
async def get_patient(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PatientDetailOut:
    return await PatientService.get_patient_by_id(db, current_user, id)
