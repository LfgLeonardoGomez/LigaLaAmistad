from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.auth import service
from app.auth.deps import COOKIE_NAME, get_current_admin
from app.auth.models import AdminUser
from app.auth.schemas import AdminCreate, AdminRead, AdminUpdate, LoginIn
from app.core.config import settings
from app.core.ratelimit import check_rate_limit, clear_attempts
from app.core.security import create_access_token
from app.database.session import SessionDep

router = APIRouter(prefix="/auth", tags=["auth"])

CurrentAdmin = Annotated[AdminUser, Depends(get_current_admin)]


@router.post("/login", response_model=AdminRead)
def login(data: LoginIn, request: Request, response: Response, session: SessionDep):
    check_rate_limit(
        request,
        max_attempts=settings.login_max_attempts,
        window_seconds=settings.login_window_seconds,
    )

    admin = service.authenticate(session, data)
    clear_attempts(request)

    response.set_cookie(
        key=COOKIE_NAME,
        value=create_access_token(admin.id),
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_expire_minutes * 60,
    )
    return admin


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    # The attributes must match the ones used at login, or the browser keeps
    # the original cookie and the logout does nothing.
    response.delete_cookie(
        key=COOKIE_NAME,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )


@router.get("/me", response_model=AdminRead)
def me(admin: CurrentAdmin):
    return admin


# Admin management. Separate router because /auth/login must stay open, and
# everything here must not.
admin_users_router = APIRouter(
    prefix="/admin/users",
    tags=["admin: users"],
    dependencies=[Depends(get_current_admin)],
)


@admin_users_router.post(
    "", response_model=AdminRead, status_code=status.HTTP_201_CREATED
)
def create_admin(data: AdminCreate, session: SessionDep):
    return service.create_admin(session, data)


@admin_users_router.get("", response_model=list[AdminRead])
def list_admins(session: SessionDep):
    return service.list_admins(session)


@admin_users_router.patch("/{admin_id}", response_model=AdminRead)
def update_admin(
    admin_id: int, data: AdminUpdate, session: SessionDep, current: CurrentAdmin
):
    return service.update_admin(session, admin_id, data, current)
