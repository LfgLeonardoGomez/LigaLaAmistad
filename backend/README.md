# Liga La Amistad — API

FastAPI + SQLModel + PostgreSQL.

## Setup

```bash
cp .env.example .env          # then fill in SECRET_KEY and the Cloudinary keys
docker compose up -d          # local Postgres on host port 5433
uv sync
uv run alembic upgrade head   # creates the schema
uv run python -m app.seed     # Zona A / Zona B and the first admin
uv run fastapi dev src/app/main.py
```

Interactive docs: http://127.0.0.1:8000/docs

Port 5433 and not 5432: a native Postgres install often already holds 5432, and
on Windows both can bind it without an error — the native one just wins.

## Tests

```bash
uv run pytest
```

Runs against a throwaway SQLite file, so nothing needs to be up. To run the same
suite against the real Postgres:

```bash
TEST_DATABASE_URL=postgresql+psycopg://liga:liga@localhost:5433/liga uv run pytest
```

`tests/test_standings.py` targets `calculate_standings`, the pure function that
holds every tournament rule. It touches no database at all.

## Migrations

Alembic owns the schema. The app does **not** create tables on startup, so a
migration that was never applied fails loudly instead of being papered over.

```bash
uv run alembic revision --autogenerate -m "what changed"
uv run alembic upgrade head
```

After autogenerating, read the file before applying it. Autogenerate is a
draft, not an authority.

## Layout

```txt
src/app/
  main.py            app, CORS, routers
  seed.py            zones + first admin, idempotent
  core/              config, security, images, rate limit, shared model mixins
  database/          engine and session
  auth/              login, logout, me, admin management
  zones/             seed data, no router of its own
  teams/             admin CRUD (no delete: teams withdraw)
  matches/           admin CRUD + result loading
  standings/         computed on read, never stored
  sponsors/          admin CRUD
  public/            read-only endpoints for the public site
```

Each module is `schemas.py` + `service.py` + `router.py`. Services are plain
functions that take a `Session`. There is no repository layer and no unit of
work: for a project this size they add indirection without buying anything.

## Deploy

El deploy usa el `Dockerfile`, no el detector automatico de la plataforma. Es
unas pocas lineas y se puede probar en local antes de subir nada:

```bash
docker build -t liga-api .
docker run --rm -p 8000:8000   -e DATABASE_URL=... -e SECRET_KEY=... liga-api
```

El contenedor corre `alembic upgrade head` y recien despues levanta el servidor,
asi un deploy nunca sirve un esquema viejo.

Variables a cargar en Railway:

| Variable | Note |
|---|---|
| `DATABASE_URL` | Reference the Postgres plugin. The scheme is rewritten to `postgresql+psycopg://` automatically. |
| `SECRET_KEY` | At least 32 characters, or the app refuses to start. |
| `CORS_ORIGINS` | The front end origin. Never `*`, cookies are dropped on a wildcard. |
| `COOKIE_SECURE` | `true` once served over HTTPS. |
| `COOKIE_SAMESITE` | `none` in production. Vercel and Railway are different sites, and `lax` would drop the session cookie. Requires `COOKIE_SECURE=true`. |
| `CLOUDINARY_*` | Without them, image uploads answer 503. |

## Notes

- Standings are recomputed on every read. Correcting a result invalidates nothing.
- A match does not store its zone or its winner. Both are derived.
- Teams are never deleted. Leaving the league sets `status` to `withdrawn`.
- Admins are created by a logged-in admin. There is no public sign-up, and
  nobody can deactivate their own account.
- The login rate limit lives in process memory. It resets on restart and does
  not add up across instances; a second instance would need Redis.
