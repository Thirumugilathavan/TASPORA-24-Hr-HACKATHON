from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.patient import Patient
from app.models.user import User
from app.models.village import Village
from app.schemas.patient_village import PatientDetailOut, PatientIn, PatientOut, VillageOut


class PatientService:
    @staticmethod
    async def create_patient(db: AsyncSession, current_user: User, data: PatientIn) -> PatientOut:
        """Registers a patient profile for the authenticated user."""
        # 1. Verify village exists
        v_stmt = select(Village).where(Village.id == data.village_id)
        village = (await db.execute(v_stmt)).scalar_one_or_none()
        if not village:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "VILLAGE_NOT_FOUND", "message": "The specified village_id does not exist."}},
            )

        # 2. Check duplicate patient profile for this user
        p_stmt = select(Patient).where(Patient.user_id == current_user.id)
        existing = (await db.execute(p_stmt)).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": {"code": "PATIENT_ALREADY_EXISTS", "message": "A patient profile has already been registered for this user."}},
            )

        # 3. Create Patient record
        patient = Patient(
            user_id=current_user.id,
            village_id=data.village_id,
            date_of_birth=data.date_of_birth,
            preferred_language=data.preferred_language,
            consent_given=data.consent_given,
            emergency_contact_phone=data.emergency_contact_phone,
        )
        db.add(patient)
        await db.commit()
        await db.refresh(patient)
        return PatientOut.model_validate(patient)

    @staticmethod
    async def get_patient_by_id(db: AsyncSession, current_user: User, patient_id: UUID) -> PatientDetailOut:
        """Retrieves patient profile by ID, enforcing patient privacy and role access rules."""
        stmt = select(Patient).where(Patient.id == patient_id)
        patient = (await db.execute(stmt)).scalar_one_or_none()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "PATIENT_NOT_FOUND", "message": "Patient with specified ID was not found."}},
            )

        # Access Control: A PATIENT role user can only view their own record
        if current_user.role == "PATIENT" and patient.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "ACCESS_DENIED", "message": "You do not have permission to access another patient's record."}},
            )

        # Fetch associated user and village
        u_stmt = select(User).where(User.id == patient.user_id)
        user = (await db.execute(u_stmt)).scalar_one_or_none()

        v_stmt = select(Village).where(Village.id == patient.village_id)
        village = (await db.execute(v_stmt)).scalar_one_or_none()
        if not village:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "VILLAGE_NOT_FOUND", "message": "Associated village record not found."}},
            )

        return PatientDetailOut(
            id=patient.id,
            user_id=patient.user_id,
            name=user.name if user else None,
            phone=user.phone if user else None,
            village=VillageOut.model_validate(village),
            date_of_birth=patient.date_of_birth,
            preferred_language=patient.preferred_language,
            consent_given=patient.consent_given,
            emergency_contact_phone=patient.emergency_contact_phone,
            created_at=patient.created_at,
        )
