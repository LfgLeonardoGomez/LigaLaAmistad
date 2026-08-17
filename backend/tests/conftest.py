"""Shared test setup.

Tests run against a throwaway SQLite file by default, so `pytest` needs nothing
running. To run them against the real Postgres instead:

    TEST_DATABASE_URL=postgresql+psycopg://liga:liga@localhost:5433/liga uv run pytest

The environment is set before importing the app on purpose: `app.core.config`
reads it at import time, and `app.database.session` builds the engine from it.
"""

import os
import tempfile
from pathlib import Path

_TEST_DB = Path(tempfile.mkdtemp()) / "test.db"

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", f"sqlite:///{_TEST_DB}"
)
os.environ["SECRET_KEY"] = "test-secret-key-long-enough-for-hs256"
os.environ["CLOUDINARY_CLOUD_NAME"] = ""
os.environ["CLOUDINARY_API_KEY"] = ""
os.environ["CLOUDINARY_API_SECRET"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session, SQLModel  # noqa: E402

from app.auth.models import AdminUser  # noqa: E402
from app.core.ratelimit import reset as reset_rate_limit  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.database.session import create_db_and_tables, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.zones.models import Zone  # noqa: E402

ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "test-password"

# bcrypt is deliberately slow. Hashing once here instead of once per test cuts
# the suite runtime by an order of magnitude.
ADMIN_PASSWORD_HASH = hash_password(ADMIN_PASSWORD)

ZONE_A = 1
ZONE_B = 2


@pytest.fixture
def client():
    """A clean database with two zones and one admin, for every test."""
    SQLModel.metadata.drop_all(engine)
    create_db_and_tables()
    reset_rate_limit()

    with Session(engine) as session:
        session.add(Zone(name="Zona A"))
        session.add(Zone(name="Zona B"))
        session.add(AdminUser(email=ADMIN_EMAIL, password_hash=ADMIN_PASSWORD_HASH))
        session.commit()

    yield TestClient(app)

    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def guest(client):
    """A second browser: same app and database, its own cookie jar.

    `admin` and `client` are the same object, so they share cookies. Any test
    that needs two live sessions at once must use this.
    """
    return TestClient(app)


@pytest.fixture
def admin(client):
    """The same client, already logged in."""
    response = client.post(
        "/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200
    return client


def make_team(admin, zone_id=ZONE_A, name="Ana") -> int:
    response = admin.post(
        "/admin/teams",
        json={"zone_id": zone_id, "player_one_name": name, "player_two_name": name + "2"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def make_match(admin, team_a_id: int, team_b_id: int, date="2026-09-01") -> int:
    response = admin.post(
        "/admin/matches",
        json={"team_a_id": team_a_id, "team_b_id": team_b_id, "date": date},
    )
    assert response.status_code == 201
    return response.json()["id"]


def sets_payload(*scores: tuple[int, int]) -> dict:
    return {
        "sets": [
            {"set_number": number, "team_a_games": a, "team_b_games": b}
            for number, (a, b) in enumerate(scores, start=1)
        ]
    }


STRAIGHT_WIN_A = sets_payload((6, 4), (6, 4))
STRAIGHT_WIN_B = sets_payload((4, 6), (4, 6))
