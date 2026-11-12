from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
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
                detail={
                    "error": {
                        "code": "PATIENT_ALREADY_EXISTS",
                        "message": "A patient profile has already been registered for this user.",
                    }
                },
            )

        # 3. Create Patient record with explicit consent handling (never assumed True)
        consent_val = bool(data.consent_given) if data.consent_given is not None else False

        patient = Patient(
            user_id=current_user.id,
            village_id=data.village_id,
            date_of_birth=data.date_of_birth,
            preferred_language=data.preferred_language,
            consent_given=consent_val,
            emergency_contact_phone=data.emergency_contact_phone,
        )
        db.add(patient)
        try:
            await db.commit()
            await db.refresh(patient)
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": {
                        "code": "PATIENT_ALREADY_EXISTS",
                        "message": "A patient profile has already been registered for this user.",
                    }
                },
            )

        return PatientOut.model_validate(patient)

    @staticmethod
    async def get_patient_by_id(db: AsyncSession, current_user: User, patient_id: UUID) -> PatientDetailOut:
        """Retrieves patient profile by ID, enforcing unambiguous identity resolution,

        least-privilege role authorization, and consent-based privacy controls.
        """
        # 1. Resolve patient: first by primary key (Patient.id), then fallback to User.id
        stmt = select(Patient).where(Patient.id == patient_id)
        patient = (await db.execute(stmt)).scalar_one_or_none()

        if not patient:
            # Fallback: check if the identifier references the patient's User.id
            u_stmt = select(Patient).where(Patient.user_id == patient_id)
            patient = (await db.execute(u_stmt)).scalar_one_or_none()

        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "PATIENT_NOT_FOUND", "message": "Patient with specified ID was not found."}},
            )

        # 2. Least-privilege role authorization
        if current_user.role == "PATIENT":
            # Patients can strictly only view their own record
            if patient.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": {
                            "code": "ACCESS_DENIED",
                            "message": "You do not have permission to access another patient's record.",
                        }
                    },
                )
        elif current_user.role in ("ASHA", "DOCTOR", "STAFF"):
            # Clinical/operational roles require patient data-sharing consent
            if not patient.consent_given:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": {
                            "code": "CONSENT_REQUIRED",
                            "message": "Patient has not provided consent for clinical data access and coordination.",
                        }
                    },
                )
        elif current_user.role == "ADMIN":
            # Admin has administrative audit access
            pass
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "ACCESS_DENIED",
                        "message": "Your role does not have permission to access patient records.",
                    }
                },
            )

        # 3. Fetch associated user and village
        u_stmt = select(User).where(User.id == patient.user_id)
        user = (await db.execute(u_stmt)).scalar_one_or_none()

        v_stmt = select(Village).where(Village.id == patient.village_id)
        village = (await db.execute(v_stmt)).scalar_one_or_none()
        if not village:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "VILLAGE_NOT_FOUND", "message": "Associated village record not found."}},
            )

        # 4. Sensitive demographic protection:
        # Emergency contact is exposed only to the patient themselves, an ADMIN, or authorized clinical staff with explicit consent
        show_emergency_contact = (
            (current_user.role == "PATIENT" and patient.user_id == current_user.id)
            or current_user.role == "ADMIN"
            or (current_user.role in ("ASHA", "DOCTOR", "STAFF") and bool(patient.consent_given))
        )

        emergency_phone = patient.emergency_contact_phone if show_emergency_contact else None

        return PatientDetailOut(
            id=patient.id,
            user_id=patient.user_id,
            name=user.name if user else None,
            phone=user.phone if user else None,
            village=VillageOut.model_validate(village),
            date_of_birth=patient.date_of_birth,
            preferred_language=patient.preferred_language,
            consent_given=bool(patient.consent_given),
            emergency_contact_phone=emergency_phone,
            created_at=patient.created_at,
        )
