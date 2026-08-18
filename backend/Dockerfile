# Explicit build instead of letting the platform guess.
#
# Nixpacks has to infer how to build a uv project with a src/ layout, and when
# it guesses wrong the failure shows up as a red deploy with a long log. This
# is a few lines and can be run locally before pushing anything.

FROM python:3.13-slim

# uv comes from its own image: no curl, no install script, pinned version.
COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first, in their own layer: they only change when the lockfile
# does, so editing application code does not reinstall the world.
# README.md travels with them because pyproject declares `readme = "README.md"`
# and the build backend refuses to build the package without it.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-install-project --no-dev

# Now the application itself.
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./
RUN uv sync --locked --no-dev

ENV PATH="/app/.venv/bin:$PATH"

# Railway injects PORT. The default keeps `docker run` usable on its own.
ENV PORT=8000
EXPOSE 8000

# Migrations run before the server so a deploy can never serve an old schema.
# Exec form so signals reach the process and the container stops cleanly.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
