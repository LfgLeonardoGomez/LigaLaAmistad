"""Private request-test database: never use the application's engine or conftest."""

import datetime
from dataclasses import dataclass

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.americanos import models  # noqa: F401 -- metadata, not DDL
from app.auth.models import AdminUser
from app.core.config import settings
from app.core.security import ALGORITHM, create_access_token
from app.database.session import get_session
from app.main import app

BASE = "/admin/americanos"


@dataclass
class AmericanoAPI:
    client: TestClient
    engine: object
    active_id: int
    inactive_id: int

    def authenticate(self, mode="active"):
        self.client.cookies.clear()
        if mode == "anonymous":
            return
        admin_id = self.inactive_id if mode == "inactive" else self.active_id
        with Session(self.engine) as session:
            admin = session.get(AdminUser, admin_id)
            assert admin is not None
            token = create_access_token(admin_id, admin.updated_at)
        if mode == "expired":
            token = jwt.encode(
                {"sub": str(admin_id), "exp": datetime.datetime.now(datetime.UTC)
                 - datetime.timedelta(minutes=1)},
                settings.secret_key, algorithm=ALGORITHM,
            )
        self.client.cookies.set("access_token", token)


@pytest.fixture
def americano_api():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        active = AdminUser(email="active@americano.test", password_hash="unused")
        inactive = AdminUser(
            email="inactive@americano.test", password_hash="unused", is_active=False,
        )
        session.add_all([active, inactive])
        session.commit()
        active_id, inactive_id = active.id, inactive.id

    def isolated_session():
        with Session(engine) as session:
            yield session

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_session] = isolated_session
    try:
        with TestClient(app, headers={
            "Origin": "http://testserver",
            "X-Requested-With": "XMLHttpRequest",
        }) as client:
            api = AmericanoAPI(client, engine, active_id, inactive_id)
            api.authenticate()
            yield api
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        engine.dispose()


def create_event(api, *, name="Encuentro", zone_count=1, start_stage="final"):
    response = api.client.post(BASE, json={
        "name": name, "zone_count": zone_count, "start_stage": start_stage,
    })
    assert response.status_code == 201, response.text
    return response.json()


def add_registration(api, detail, *, first="Ana", second="Sol"):
    response = api.client.post(f"{BASE}/{detail['id']}/registrations", json={
        "expected_revision": detail["revision"],
        "player1_name": first, "player2_name": second,
    })
    assert response.status_code == 201, response.text
    return response.json()
