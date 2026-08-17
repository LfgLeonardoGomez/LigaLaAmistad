from sqlmodel import Field

from app.core.models import TimestampMixin


class AdminUser(TimestampMixin, table=True):
    """An administrator. No roles in the MVP.

    The first record is created by seed; there is no sign-up in the application.
    """

    __tablename__ = "admin_users"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(max_length=255, unique=True, index=True)
    password_hash: str = Field(max_length=255)
    is_active: bool = Field(default=True)
