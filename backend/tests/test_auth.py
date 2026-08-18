from app.core.config import settings

from .conftest import ADMIN_EMAIL, ADMIN_PASSWORD


def login(client, password=ADMIN_PASSWORD, email=ADMIN_EMAIL):
    return client.post("/auth/login", json={"email": email, "password": password})


def test_login_with_valid_credentials_sets_an_httponly_cookie(client):
    response = login(client)

    assert response.status_code == 200
    assert response.json()["email"] == ADMIN_EMAIL
    assert "access_token" in response.cookies
    assert "httponly" in response.headers["set-cookie"].lower()


def test_login_never_leaks_the_password_hash(client):
    assert "password_hash" not in login(client).json()


def test_wrong_password_and_unknown_email_answer_the_same(client):
    wrong_password = login(client, password="nope")
    unknown_email = login(client, email="ghost@test.com")

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json()["detail"] == unknown_email.json()["detail"]


def test_me_requires_a_session(client):
    assert client.get("/auth/me").status_code == 401


def test_me_returns_the_logged_in_admin(admin):
    assert admin.get("/auth/me").json()["email"] == ADMIN_EMAIL


def test_logout_ends_the_session(admin):
    assert admin.post("/auth/logout").status_code == 204
    assert admin.get("/auth/me").status_code == 401


def test_a_tampered_token_is_rejected(admin):
    admin.cookies.set("access_token", "not.a.real.token")

    assert admin.get("/auth/me").status_code == 401


def test_repeated_failed_logins_are_rate_limited(client, monkeypatch):
    monkeypatch.setattr(settings, "login_max_attempts", 3)

    for _ in range(3):
        assert login(client, password="nope").status_code == 401

    blocked = login(client, password="nope")
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


def test_the_rate_limit_blocks_even_the_correct_password(client, monkeypatch):
    """Otherwise an attacker learns when they guessed right."""
    monkeypatch.setattr(settings, "login_max_attempts", 2)

    login(client, password="nope")
    login(client, password="nope")

    assert login(client).status_code == 429


def test_a_successful_login_clears_the_counter(client, monkeypatch):
    monkeypatch.setattr(settings, "login_max_attempts", 3)

    login(client, password="nope")
    login(client, password="nope")
    assert login(client).status_code == 200

    assert login(client, password="nope").status_code == 401


def test_the_limit_counts_the_forwarded_address_not_the_proxy(client, monkeypatch):
    """Behind a proxy every request arrives from the proxy, and if the fleet
    rotates addresses each one looks like a new person. That is how the limit
    silently stopped working in production."""
    monkeypatch.setattr(settings, "login_max_attempts", 3)

    # Same caller, seen through three different edge servers.
    for index in range(3):
        response = client.post(
            "/auth/login",
            json={"email": "otro@test.com", "password": "nope"},
            headers={"X-Forwarded-For": f"203.0.113.7, 10.0.0.{index}"},
        )
        assert response.status_code == 401

    blocked = client.post(
        "/auth/login",
        json={"email": "otro@test.com", "password": "nope"},
        headers={"X-Forwarded-For": "203.0.113.7, 10.0.0.99"},
    )
    assert blocked.status_code == 429


def test_one_account_is_protected_even_from_many_addresses(client, monkeypatch):
    """The address bucket can be dodged by rotating addresses. The email one
    cannot, and it is the bucket that matters when someone grinds down a
    single account."""
    monkeypatch.setattr(settings, "login_max_attempts", 3)

    for index in range(3):
        response = client.post(
            "/auth/login",
            json={"email": ADMIN_EMAIL, "password": "nope"},
            headers={"X-Forwarded-For": f"198.51.100.{index}"},
        )
        assert response.status_code == 401

    blocked = client.post(
        "/auth/login",
        json={"email": ADMIN_EMAIL, "password": "nope"},
        headers={"X-Forwarded-For": "198.51.100.200"},
    )
    assert blocked.status_code == 429


def test_the_email_bucket_ignores_case_and_spacing(client, monkeypatch):
    monkeypatch.setattr(settings, "login_max_attempts", 2)

    for value in (ADMIN_EMAIL, ADMIN_EMAIL.upper()):
        client.post("/auth/login", json={"email": value, "password": "nope"})

    blocked = client.post(
        "/auth/login", json={"email": f"  {ADMIN_EMAIL}  ", "password": "nope"}
    )
    assert blocked.status_code == 429


def test_a_blocked_account_does_not_block_a_different_one(client, monkeypatch):
    monkeypatch.setattr(settings, "login_max_attempts", 2)

    for _ in range(3):
        client.post("/auth/login", json={"email": "victima@test.com", "password": "nope"})

    # The real admin must still be able to get in from another address.
    response = client.post(
        "/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        headers={"X-Forwarded-For": "203.0.113.250"},
    )
    assert response.status_code == 200
