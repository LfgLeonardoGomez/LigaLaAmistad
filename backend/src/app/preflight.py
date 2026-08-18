"""Checks the environment before the container does anything else.

    python -m app.preflight

Without this, a missing DATABASE_URL falls back to the local development
default and the deploy dies inside SQLAlchemy with sixty lines of traceback
that never mention the variable. One clear line beats that.
"""

import os
import sys

from sqlalchemy import text
from sqlmodel import create_engine

from app.core.config import settings


def fail(message: str, hint: str) -> int:
    print(f"\n  ARRANQUE ABORTADO: {message}\n", file=sys.stderr)
    print(f"  {hint}\n", file=sys.stderr)
    return 1


def main() -> int:
    if "DATABASE_URL" not in os.environ:
        return fail(
            "la variable DATABASE_URL no está definida",
            "En Railway: pestaña Variables del servicio ->\n"
            "  DATABASE_URL = ${{Postgres.DATABASE_URL}}\n"
            "  (referenciala al plugin, no la copies a mano)",
        )

    url = settings.database_url
    # Never print the URL: it carries the password.
    host = url.rsplit("@", 1)[-1] if "@" in url else "(sin host)"
    print(f"  base de datos: {host}")

    try:
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        with engine.connect() as connection:
            version = connection.execute(text("select version()")).scalar_one()
    except Exception as error:
        return fail(
            f"no se pudo conectar a la base ({type(error).__name__})",
            f"Detalle: {str(error).splitlines()[0][:160]}",
        )

    print(f"  conectado: {version.split(',')[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
