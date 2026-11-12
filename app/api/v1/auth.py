from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    hash_password,
    needs_rehash,
    normalize_phone_number,
    verify_password,
)
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

    SECURITY RULES:
    1. Public registration is strictly constrained to the PATIENT role.
       Any role value sent in the client payload is ignored and overridden
       with Role.PATIENT.
    2. Phone numbers are normalized to standard 10-digit format (+91, leading 0,
       spaces, and formatting characters are stripped).
    3. Passwords are securely hashed using salted bcrypt (rounds=12) with
       Unicode normalization to guarantee consistent verification across platforms.
    """
    norm_phone = normalize_phone_number(payload.phone)
    if not norm_phone or len(norm_phone) != 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "code": "INVALID_PHONE_FORMAT",
                    "message": "Please enter a valid 10-digit mobile number.",
                }
            },
        )

    # Check for existing phone number (checking both normalized and raw formatted phone)
    raw_phone = payload.phone.strip()
    stmt = select(User).where(
        (User.phone == norm_phone) | (User.phone == raw_phone)
    )
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

    # Hash password securely using direct salted bcrypt
    hashed_pwd = hash_password(payload.password)

    # Create new patient user with normalized canonical phone
    new_user = User(
        name=payload.name.strip(),
        phone=norm_phone,
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
    """Authenticate with phone and password to receive a Bearer JWT token.

    Identifier matching:
    Matches against canonical 10-digit normalized phone or raw submitted phone.
    Handles +91 prefixes, leading zero, formatting spaces, and dashes transparently.

    Password verification:
    Uses constant-time comparison across bcrypt, argon2, and legacy formats,
    automatically upgrading legacy/un-salted hashes to current bcrypt standards upon
    verified login.
    """
    norm_phone = normalize_phone_number(payload.phone)
    raw_phone = payload.phone.strip()

    # Query user by normalized phone or raw phone
    stmt = select(User).where(
        (User.phone == norm_phone) | (User.phone == raw_phone)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
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

    # Verify password against stored hash
    if not verify_password(payload.password, user.password_hash):
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

    # Seamless background data migration:
    needs_update = False

    # 1. Migrate user phone to canonical 10-digit normalized representation if needed
    if user.phone != norm_phone and len(norm_phone) == 10:
        user.phone = norm_phone
        needs_update = True

    # 2. Upgrade legacy or weaker hashes to current salted bcrypt rounds=12
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
        needs_update = True

    if needs_update:
        db.add(user)
        await db.commit()

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
