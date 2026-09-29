"""Password hashing and JWT issuing/verification.

Passwords use PBKDF2-HMAC-SHA256 from the standard library so the demo needs no
extra native dependency (no bcrypt/passlib build step). The stored format is
``pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>``.

This module also owns the **email-prefix role policy**: the text in front of an
employee's numeric id in their email address selects their access role, so
adding a user is just a matter of using a correctly-prefixed address.
"""
import hashlib
import hmac
import os
import re
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings
from app.db.models import Role

_ALGORITHM_TAG = "pbkdf2_sha256"
_ITERATIONS = 260_000
_SALT_BYTES = 16

# Prefix (the text before the trailing employee id) -> access role.
EMAIL_ROLE_PREFIXES: dict[str, Role] = {
    "hr": Role.HR,
    "hradmin": Role.HR,
    "admin": Role.HR,
    "humanresources": Role.HR,
    "manage": Role.MANAGER,
    "manager": Role.MANAGER,
    "mgr": Role.MANAGER,
    "lead": Role.MANAGER,
    "supervisor": Role.MANAGER,
    "employee": Role.EMPLOYEE,
    "emp": Role.EMPLOYEE,
    "staff": Role.EMPLOYEE,
    "user": Role.EMPLOYEE,
}

DEFAULT_ROLE = Role.EMPLOYEE

# Trailing separators left behind once the employee id is stripped, e.g.
# "hr_1000" -> "hr", "manage-1234" -> "manage".
_TRIM_CHARS = "._-+ "


def email_role_prefix(email: str) -> str:
    """The text in front of the employee id: 'hr1000@x.com' -> 'hr'.

    Returns an empty string when the local part is only digits, or has no
    alphabetic prefix at all (e.g. '1021@x.com').
    """
    local = (email or "").split("@", 1)[0].strip().lower()
    # Drop the employee id itself (any trailing digits) and any separator.
    prefix = re.sub(r"\d+$", "", local).rstrip(_TRIM_CHARS)
    return prefix


def role_from_email(email: str) -> Role:
    """Derive the access role from the email prefix, defaulting to EMPLOYEE.

    Recognised prefixes (case-insensitive) are listed in EMAIL_ROLE_PREFIXES.
    Anything unrecognised — including addresses with no prefix, such as
    'anil.menon@xyzcorp.com' — is treated as EMPLOYEE.
    """
    prefix = email_role_prefix(email)
    if prefix in EMAIL_ROLE_PREFIXES:
        return EMAIL_ROLE_PREFIXES[prefix]
    # Allow a compound prefix such as "hradmin" to match a known leading word.
    for known, role in EMAIL_ROLE_PREFIXES.items():
        if prefix.startswith(known):
            return role
    return DEFAULT_ROLE


def describe_role_prefix(email: str) -> str:
    """Human-readable explanation of what role an email will receive."""
    prefix = email_role_prefix(email)
    role = role_from_email(email)
    if prefix and prefix in EMAIL_ROLE_PREFIXES:
        return f"'{prefix}' prefix -> {role.value}"
    if prefix:
        return f"'{prefix}' is not a known role prefix -> {role.value} (default)"
    return f"no prefix before the employee id -> {role.value} (default)"


def hash_password(password: str) -> str:
    salt = os.urandom(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"{_ALGORITHM_TAG}${_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        tag, iterations, salt_hex, hash_hex = stored.split("$")
        if tag != _ALGORITHM_TAG:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
        )
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(digest.hex(), hash_hex)


def create_access_token(user_id: int, email: str, role: str, employee_id: str | None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "emp": employee_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    """Return the token claims, or None if the token is invalid/expired/tampered."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None