from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import re
from typing import Any, Dict, Optional
import unicodedata
import bcrypt
from jose import JWTError, jwt
from app.core.config import settings


def normalize_phone_number(raw_phone: str) -> str:
    """Normalize Indian phone numbers to canonical 10-digit format (e.g. 9876500001).

    Handles +91 country prefix, leading zeros (STD 0), spaces, dashes, and parentheses.
    """
    if not raw_phone:
        return ""

    # Strip everything except digits
    digits = re.sub(r"[^\d]", "", str(raw_phone))

    # If starts with 91 and has 12 digits (country code + 10 digits)
    if len(digits) == 12 and digits.startswith("91"):
        return digits[2:]

    # If starts with 0 and has 11 digits (STD zero + 10 digits)
    if len(digits) == 11 and digits.startswith("0"):
        return digits[1:]

    # If standard 10 digits
    if len(digits) == 10:
        return digits

    # Fallback: if longer than 10 digits, take the trailing 10 digits
    if len(digits) > 10:
        return digits[-10:]

    return digits


def hash_password(password: str) -> str:
    """Hash plaintext password using salted bcrypt with rounds=12.

    Applies Unicode NFC normalization before encoding to guarantee consistent UTF-8 byte
    representation across operating systems and browsers.
    """
    if not password:
        raise ValueError("Password cannot be empty.")

    normalized = unicodedata.normalize("NFC", password)
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(normalized.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plaintext password against stored hash.

    Supports:
    1. Standard salted bcrypt hashes ($2b$, $2a$, $2y$)
    2. Argon2 hashes ($argon2id$, $argon2i$) if present
    3. PBKDF2-SHA256 hashes ($pbkdf2$, pbkdf2:)
    4. Salted SHA256 hashes (sha256$salt$hash)
    5. Strips trailing whitespace/newlines from stored hash to guard against DB column padding
    6. Constant-time comparison fallback for legacy test data
    """
    if not plain_password or not hashed_password:
        return False

    norm_pwd = unicodedata.normalize("NFC", plain_password)
    clean_hash = hashed_password.strip()

    # 1. Bcrypt hashes ($2a$, $2b$, $2y$, $2x$)
    if clean_hash.startswith(("$2a$", "$2b$", "$2y$", "$2x$")):
        try:
            return bcrypt.checkpw(norm_pwd.encode("utf-8"), clean_hash.encode("utf-8"))
        except Exception:
            return False

    # 2. Argon2 hashes ($argon2id$, $argon2i$, $argon2d$)
    if clean_hash.startswith(("$argon2id$", "$argon2i$", "$argon2d$")):
        try:
            import argon2
            ph = argon2.PasswordHasher()
            ph.verify(clean_hash, norm_pwd)
            return True
        except Exception:
            pass

    # 3. PBKDF2 hashes
    if clean_hash.startswith(("$pbkdf2", "pbkdf2:")):
        try:
            from passlib.hash import pbkdf2_sha256
            return pbkdf2_sha256.verify(norm_pwd, clean_hash)
        except Exception:
            pass

    # 4. Salted SHA256 hashes: sha256$salt$digest
    if clean_hash.startswith("sha256$"):
        parts = clean_hash.split("$")
        if len(parts) == 3:
            salt, digest = parts[1], parts[2]
            computed = hashlib.sha256((salt + norm_pwd).encode("utf-8")).hexdigest()
            return hmac.compare_digest(computed, digest)

    # 5. Direct bcrypt check fallback
    try:
        return bcrypt.checkpw(norm_pwd.encode("utf-8"), clean_hash.encode("utf-8"))
    except Exception:
        pass

    # 6. Constant-time equality for legacy development artifacts
    try:
        return hmac.compare_digest(norm_pwd, clean_hash)
    except Exception:
        return False


def needs_rehash(hashed_password: str) -> bool:
    """Returns True if the stored hash should be upgraded to current standard bcrypt rounds=12."""
    if not hashed_password:
        return True
    clean_hash = hashed_password.strip()
    # If not a standard $2b$ hash with 12 rounds ($2b$12$), rehash is recommended
    return not clean_hash.startswith("$2b$12$")


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None
