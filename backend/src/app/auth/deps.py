from typing import Annotated

from fastapi import Cookie, HTTPException, status

from app.auth.models import AdminUser
from app.core.security import read_access_token
from app.database.session import SessionDep

COOKIE_NAME = "access_token"


def get_current_admin(
    session: SessionDep,
    access_token: Annotated[str | None, Cookie()] = None,
) -> AdminUser:
    """Guard for every admin route. Reads the httpOnly cookie set at login."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
    )

    if access_token is None:
        raise unauthorized

    admin_id = read_access_token(access_token)
    if admin_id is None:
        raise unauthorized

    admin = session.get(AdminUser, admin_id)
    if admin is None or not admin.is_active:
        raise unauthorized

    return admin
