import secrets
from typing import Callable, List, Optional
from uuid import UUID
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency that verifies Bearer JWT token and returns the authenticated User."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHORIZED", "message": "Missing bearer authentication token"}},
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHORIZED", "message": "Invalid or expired token"}},
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHORIZED", "message": "Token missing subject identifier"}},
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_uuid = UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHORIZED", "message": "Malformed user identifier"}},
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt = select(User).where(User.id == user_uuid, User.is_active == True)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHORIZED", "message": "User account not found or deactivated"}},
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Dependency that returns the authenticated User if a valid Bearer token is provided, or None."""
    if not credentials or not credentials.credentials:
        return None

    payload = decode_access_token(credentials.credentials)
    if not payload:
        return None

    user_id_str = payload.get("sub")
    if not user_id_str:
        return None

    try:
        user_uuid = UUID(user_id_str)
    except ValueError:
        return None

    stmt = select(User).where(User.id == user_uuid, User.is_active == True)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def require_role(allowed_roles: List[str]) -> Callable:
    """Dependency factory restricting route access to specified roles."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "FORBIDDEN",
                        "message": f"Operation not permitted. Required roles: {allowed_roles}"
                    }
                },
            )
        return current_user

    return role_checker


async def check_patient_ownership(
    db: AsyncSession,
    current_user: User,
    patient_id: UUID,
) -> bool:
    """Verify whether patient_id belongs to current_user (either as User.id or Patient profile id),
    or if caller is an authorized operational role acting on behalf of an existing patient.
    """
    if current_user.role == "PATIENT":
        if patient_id == current_user.id:
            return True

        from app.models.patient import Patient

        stmt = select(Patient.id).where(
            Patient.id == patient_id,
            Patient.user_id == current_user.id,
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none() is not None

    # For operational roles (ASHA, DOCTOR, STAFF, ADMIN), verify the patient actually exists
    from app.models.patient import Patient

    p_stmt = select(Patient.id).where((Patient.id == patient_id) | (Patient.user_id == patient_id))
    if (await db.execute(p_stmt)).scalar_one_or_none() is not None:
        return True

    u_stmt = select(User.id).where(User.id == patient_id)
    return (await db.execute(u_stmt)).scalar_one_or_none() is not None


async def verify_ivr_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> str:
    """Verify X-API-Key header for telephony webhooks and IVR endpoints per API.md."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHORIZED", "message": "Missing X-API-Key header"}},
        )
    expected_key = getattr(settings, "IVR_API_KEY", "carebridge-ivr-secret-api-key")
    if not secrets.compare_digest(x_api_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN", "message": "Invalid API key"}},
        )
    return x_api_key
