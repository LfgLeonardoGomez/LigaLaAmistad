from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

# SQLite needs this to be used from FastAPI's thread pool. Postgres does not.
connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)

engine = create_engine(settings.database_url, connect_args=connect_args)


def create_db_and_tables() -> None:
    """Create every table declared by the models.

    The imports are local and unused on purpose: importing a model module is what
    registers its table in SQLModel.metadata. Without them, tables are missing.
    """
    from app.auth import models as auth_models  # noqa: F401
    from app.matches import models as match_models  # noqa: F401
    from app.sponsors import models as sponsor_models  # noqa: F401
    from app.teams import models as team_models  # noqa: F401
    from app.zones import models as zone_models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
