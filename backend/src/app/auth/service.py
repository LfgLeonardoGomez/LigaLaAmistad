from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.auth.models import AdminUser
from app.auth.schemas import AdminCreate, AdminUpdate, LoginIn
from app.core.security import hash_password, verify_password


def authenticate(session: Session, data: LoginIn) -> AdminUser:
    """Return the admin for these credentials, or raise 401.

    The same message is used for an unknown email and a wrong password on
    purpose: telling them apart lets anyone find out which emails exist.
    """
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password",
    )

    admin = session.exec(
        select(AdminUser).where(AdminUser.email == data.email)
    ).first()

    if admin is None or not verify_password(data.password, admin.password_hash):
        raise invalid
    if not admin.is_active:
        raise invalid

    return admin


def create_admin(session: Session, data: AdminCreate) -> AdminUser:
    taken = session.exec(
        select(AdminUser).where(AdminUser.email == data.email)
    ).first()
    if taken is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An admin with that email already exists",
        )

    admin = AdminUser(
        email=data.email, password_hash=hash_password(data.password)
    )
    session.add(admin)
    session.commit()
    session.refresh(admin)
    return admin


def list_admins(session: Session) -> list[AdminUser]:
    return list(session.exec(select(AdminUser).order_by(AdminUser.id)).all())


def get_admin(session: Session, admin_id: int) -> AdminUser:
    admin = session.get(AdminUser, admin_id)
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found"
        )
    return admin


def update_admin(
    session: Session, admin_id: int, data: AdminUpdate, current_admin: AdminUser
) -> AdminUser:
    admin = get_admin(session, admin_id)
    changes = data.model_dump(exclude_unset=True)

    if changes.get("is_active") is False and admin.id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account",
        )

    if "password" in changes:
        admin.password_hash = hash_password(changes.pop("password"))

    for field, value in changes.items():
        setattr(admin, field, value)

    session.add(admin)
    session.commit()
    session.refresh(admin)
    return admin
