from .conftest import ADMIN_EMAIL, ADMIN_PASSWORD

NEW_ADMIN = {"email": "segundo@test.com", "password": "another-password"}


def test_managing_admins_requires_a_session(client):
    assert client.get("/admin/users").status_code == 401
    assert client.post("/admin/users", json=NEW_ADMIN).status_code == 401


def test_an_admin_can_create_another_admin(admin):
    response = admin.post("/admin/users", json=NEW_ADMIN)

    assert response.status_code == 201
    assert response.json()["email"] == NEW_ADMIN["email"]
    assert response.json()["is_active"] is True


def test_the_created_admin_can_log_in(admin, client):
    admin.post("/admin/users", json=NEW_ADMIN)
    admin.post("/auth/logout")

    response = client.post("/auth/login", json=NEW_ADMIN)

    assert response.status_code == 200
    assert client.get("/auth/me").json()["email"] == NEW_ADMIN["email"]


def test_the_password_hash_is_never_returned(admin):
    body = admin.post("/admin/users", json=NEW_ADMIN).json()

    assert "password_hash" not in body
    assert "password" not in body


def test_emails_cannot_be_reused(admin):
    admin.post("/admin/users", json=NEW_ADMIN)

    response = admin.post("/admin/users", json=NEW_ADMIN)

    assert response.status_code == 409


def test_a_malformed_email_is_rejected(admin):
    response = admin.post("/admin/users", json={**NEW_ADMIN, "email": "not-an-email"})

    assert response.status_code == 422


def test_a_short_password_is_rejected(admin):
    response = admin.post("/admin/users", json={**NEW_ADMIN, "password": "corta"})

    assert response.status_code == 422


def test_list_admins(admin):
    admin.post("/admin/users", json=NEW_ADMIN)

    emails = [row["email"] for row in admin.get("/admin/users").json()]

    assert emails == [ADMIN_EMAIL, NEW_ADMIN["email"]]


def test_resetting_a_password_replaces_the_old_one(admin, client):
    created = admin.post("/admin/users", json=NEW_ADMIN).json()

    admin.patch(f"/admin/users/{created['id']}", json={"password": "brand-new-password"})
    admin.post("/auth/logout")

    assert client.post("/auth/login", json=NEW_ADMIN).status_code == 401
    assert (
        client.post(
            "/auth/login",
            json={"email": NEW_ADMIN["email"], "password": "brand-new-password"},
        ).status_code
        == 200
    )


def test_a_deactivated_admin_cannot_log_in(admin, client):
    created = admin.post("/admin/users", json=NEW_ADMIN).json()

    admin.patch(f"/admin/users/{created['id']}", json={"is_active": False})
    admin.post("/auth/logout")

    assert client.post("/auth/login", json=NEW_ADMIN).status_code == 401


def test_a_deactivated_admin_loses_an_open_session(admin, guest):
    """Deactivating must cut the session immediately, not at token expiry."""
    created = admin.post("/admin/users", json=NEW_ADMIN).json()

    guest.post("/auth/login", json=NEW_ADMIN)
    assert guest.get("/auth/me").status_code == 200

    admin.patch(f"/admin/users/{created['id']}", json={"is_active": False})

    assert guest.get("/auth/me").status_code == 401


def test_you_cannot_lock_yourself_out(admin):
    me = admin.get("/auth/me").json()

    response = admin.patch(f"/admin/users/{me['id']}", json={"is_active": False})

    assert response.status_code == 400
    assert admin.get("/auth/me").status_code == 200


def test_updating_an_unknown_admin(admin):
    assert admin.patch("/admin/users/999", json={"is_active": False}).status_code == 404


def test_an_unknown_field_is_rejected(admin):
    me = admin.get("/auth/me").json()

    assert admin.patch(f"/admin/users/{me['id']}", json={"email": "x@y.com"}).status_code == 422
