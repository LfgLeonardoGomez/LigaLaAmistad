"""Alembic environment.

The database URL comes from the application settings, not from alembic.ini, so
there is a single source of truth and no credentials get committed.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

from app.core.config import settings

# Importing the model modules is what fills SQLModel.metadata. Without them,
# autogenerate would think every table should be dropped.
from app.auth import models as auth_models  # noqa: F401,E402
from app.matches import models as match_models  # noqa: F401,E402
from app.sponsors import models as sponsor_models  # noqa: F401,E402
from app.teams import models as team_models  # noqa: F401,E402
from app.zones import models as zone_models  # noqa: F401,E402

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
