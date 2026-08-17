"""Creates the data the system takes for granted and does not manage from the UI.

Idempotent: running it twice does not duplicate anything.

    uv run python -m app.seed
"""

import os

from sqlmodel import Session, select

from app.auth.models import AdminUser
from app.core.security import hash_password
from app.database.session import create_db_and_tables, engine
from app.zones.models import Zone

ZONE_NAMES = ["Zona A", "Zona B"]

DEFAULT_ADMIN_EMAIL = "admin@ligalaamistad.com"
DEFAULT_ADMIN_PASSWORD = "changeme"


def seed_zones(session: Session) -> None:
    for name in ZONE_NAMES:
        if session.exec(select(Zone).where(Zone.name == name)).first() is None:
            session.add(Zone(name=name))
            print(f"zone created: {name}")


def seed_admin(session: Session) -> None:
    email = os.getenv("ADMIN_EMAIL", DEFAULT_ADMIN_EMAIL)
    password = os.getenv("ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)

    if session.exec(select(AdminUser).where(AdminUser.email == email)).first():
        return

    session.add(AdminUser(email=email, password_hash=hash_password(password)))
    print(f"admin created: {email}")


def main() -> None:
    create_db_and_tables()
    with Session(engine) as session:
        seed_zones(session)
        seed_admin(session)
        session.commit()
    print("seed done")


if __name__ == "__main__":
    main()
