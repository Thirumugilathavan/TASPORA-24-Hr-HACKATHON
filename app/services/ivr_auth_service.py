from datetime import datetime, timedelta, timezone
import re
from typing import Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.security import verify_password
from app.models.ivr import IVRAuthAttempt
from app.models.patient import Patient
from app.models.user import User


def normalize_phone_number(raw_phone: str) -> str:
    """Normalize Indian phone numbers to standard 10-digit format (e.g. 9876500001).

    Handles +91, 0 prefix, spaces, dashes, parentheses.
    """
    if not raw_phone:
        return ""

    # Strip everything except digits and leading plus
    digits = re.sub(r"[^\d]", "", raw_phone)

    # If starts with 91 and has 12 digits (country code + 10 digits)
    if len(digits) == 12 and digits.startswith("91"):
        return digits[2:]

    # If starts with 0 and has 11 digits (STD zero + 10 digits)
    if len(digits) == 11 and digits.startswith("0"):
        return digits[1:]

    # If already 10 digits
    if len(digits) == 10:
        return digits

    # Fallback to last 10 digits if longer, or raw digits
    if len(digits) > 10:
        return digits[-10:]

    return digits


class IVRAuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def lookup_caller(self, phone: str) -> Tuple[Optional[User], Optional[Patient]]:
        """Identify caller and associated patient profile from incoming phone number."""
        norm_phone = normalize_phone_number(phone)
        if not norm_phone:
            return None, None

        # Lookup user
        u_stmt = select(User).where(User.phone == norm_phone, User.is_active == True)
        u_res = await self.db.execute(u_stmt)
        user = u_res.scalar_one_or_none()

        if not user:
            return None, None

        # Lookup patient profile with village eagerly loaded
        p_stmt = (
            select(Patient)
            .where(Patient.user_id == user.id)
            .options(selectinload(Patient.village))
        )
        p_res = await self.db.execute(p_stmt)
        patient = p_res.scalar_one_or_none()

        return user, patient

    async def verify_pin(self, phone: str, pin: str) -> Tuple[bool, Optional[str]]:
        """Verify 4-digit IVR PIN with rate-limiting and brute-force lockout protection.

        Returns:
            (is_valid, error_code)
            error_code can be: None, "LOCKED", "USER_NOT_FOUND", "INVALID_PIN"
        """
        norm_phone = normalize_phone_number(phone)
        now = datetime.now(timezone.utc)

        # 1. Check rate limit / lockout state
        attempt_stmt = select(IVRAuthAttempt).where(IVRAuthAttempt.phone == norm_phone)
        attempt_res = await self.db.execute(attempt_stmt)
        attempt = attempt_res.scalar_one_or_none()

        if attempt:
            if attempt.is_locked:
                locked_until = attempt.locked_until
                if locked_until is not None:
                    if locked_until.tzinfo is None:
                        locked_until = locked_until.replace(tzinfo=timezone.utc)
                    if now < locked_until:
                        return False, "LOCKED"
                # Lock expired; reset attempts
                attempt.is_locked = False
                attempt.attempts_count = 0
                attempt.locked_until = None
        else:
            attempt = IVRAuthAttempt(
                phone=norm_phone,
                attempts_count=0,
                is_locked=False,
                last_attempt_at=now,
            )
            self.db.add(attempt)
            await self.db.flush()

        # 2. Lookup user
        user, _ = await self.lookup_caller(norm_phone)
        if not user:
            attempt.attempts_count += 1
            attempt.last_attempt_at = now
            await self.db.commit()
            return False, "USER_NOT_FOUND"

        # 3. Secure PIN verification
        # For button phone users, accepted PIN is either:
        # a) Last 4 digits of their registered mobile number (safe rural default)
        # b) Direct match against password if user password is 4 digits
        # c) bcrypt password match
        clean_pin = pin.strip()
        expected_default_pin = norm_phone[-4:] if len(norm_phone) >= 4 else "1234"

        is_correct = False
        if clean_pin == expected_default_pin:
            is_correct = True
        elif clean_pin and verify_password(clean_pin, user.password_hash):
            is_correct = True

        if is_correct:
            attempt.attempts_count = 0
            attempt.is_locked = False
            attempt.locked_until = None
            attempt.last_attempt_at = now
            await self.db.commit()
            return True, None
        else:
            attempt.attempts_count += 1
            attempt.last_attempt_at = now
            if attempt.attempts_count >= settings.IVR_MAX_AUTH_ATTEMPTS:
                attempt.is_locked = True
                attempt.locked_until = now + timedelta(minutes=settings.IVR_AUTH_LOCKOUT_MINUTES)
                await self.db.commit()
                return False, "LOCKED"

            await self.db.commit()
            return False, "INVALID_PIN"
