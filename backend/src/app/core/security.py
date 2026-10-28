import datetime

import bcrypt
import jwt

from app.core.config import settings

ALGORITHM = "HS256"


def hash_password(plain_password: str) -> str:
    encoded = plain_password.encode("utf-8")
    if len(encoded) > 72:
        raise ValueError("Password must not exceed 72 UTF-8 bytes")
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode()


def verify_password(plain_password: str, password_hash: str) -> bool:
    encoded = plain_password.encode("utf-8")
    # bcrypt silently truncates at 72 bytes in some versions and raises in
    # others. Treat oversized credentials as invalid, not as a server error.
    if len(encoded) > 72:
        return False
    return bcrypt.checkpw(encoded, password_hash.encode())


def _auth_version(updated_at: datetime.datetime) -> int:
    """Stable microsecond timestamp used to revoke an admin's existing JWTs."""
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=datetime.UTC)
    return int(updated_at.timestamp() * 1_000_000)


def create_access_token(admin_id: int, updated_at: datetime.datetime) -> str:
    expires_at = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": str(admin_id), "exp": expires_at, "ver": _auth_version(updated_at)}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def read_access_token(
    token: str, updated_at: datetime.datetime | None = None
) -> int | None:
    """Return the admin id carried by the token, or None if it is invalid or expired."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        if updated_at is not None and payload.get("ver") != _auth_version(updated_at):
            return None
        return int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None
