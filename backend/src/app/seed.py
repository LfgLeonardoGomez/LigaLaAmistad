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

# There is deliberately no default password. A default here is published in the
# repository, so a deploy that forgets ADMIN_PASSWORD would come up with an
# admin account whose credentials anyone can read. Failing is the safer outcome.
MIN_ADMIN_PASSWORD_LENGTH = 8


def seed_zones(session: Session) -> None:
    for name in ZONE_NAMES:
        if session.exec(select(Zone).where(Zone.name == name)).first() is None:
            session.add(Zone(name=name))
            print(f"zone created: {name}")


def seed_admin(session: Session) -> None:
    email = os.getenv("ADMIN_EMAIL", DEFAULT_ADMIN_EMAIL)

    if session.exec(select(AdminUser).where(AdminUser.email == email)).first():
        return

    # Only demanded when an admin is about to be created: an existing
    # deployment keeps booting without it.
    password = os.getenv("ADMIN_PASSWORD")
    if not password:
        raise RuntimeError(
            "ADMIN_PASSWORD no está definida y hay que crear el primer "
            "administrador. Definila antes de arrancar; no hay valor por "
            "defecto a propósito."
        )
    if len(password) < MIN_ADMIN_PASSWORD_LENGTH:
        raise RuntimeError(
            f"ADMIN_PASSWORD tiene que tener al menos "
            f"{MIN_ADMIN_PASSWORD_LENGTH} caracteres."
        )

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
