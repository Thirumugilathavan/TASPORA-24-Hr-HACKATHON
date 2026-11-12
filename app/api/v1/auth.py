from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import LoginIn, RegisterIn, TokenOut, UserOut
from app.schemas.shared import Role

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new patient account",
)
async def register(
    payload: RegisterIn,
    db: AsyncSession = Depends(get_db),
):
    """Public registration endpoint.

    SECURITY RULE:
    Public registration is strictly constrained to the PATIENT role.
    Any role value sent in the client payload is ignored and overridden
    with Role.PATIENT. Staff, Doctor, ASHA and Admin accounts must be
    provisioned through controlled administrative mechanisms.
    """
    # Check for existing phone number
    stmt = select(User).where(User.phone == payload.phone)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "CONFLICT",
                    "message": "A user with this phone number is already registered.",
                }
            },
        )

    # Hash password securely using direct bcrypt
    hashed_pwd = hash_password(payload.password)

    # Create new patient user (forcing role to PATIENT)
    new_user = User(
        name=payload.name,
        phone=payload.phone,
        password_hash=hashed_pwd,
        role=Role.PATIENT.value,  # Strict server-enforced role
        is_active=True,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


@router.post(
    "/login",
    response_model=TokenOut,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and issue JWT access token",
)
async def login(
    payload: LoginIn,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with phone and password to receive a Bearer JWT token."""
    stmt = select(User).where(User.phone == payload.phone)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "INVALID_CREDENTIALS",
                    "message": "Invalid phone number or password.",
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "ACCOUNT_DISABLED",
                    "message": "This account has been deactivated.",
                }
            },
        )

    # Issue token containing user ID and role
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role, "phone": user.phone}
    )

    return TokenOut(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        user_id=user.id,
    )
