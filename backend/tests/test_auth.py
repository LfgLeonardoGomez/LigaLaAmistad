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
    copied_cookie = admin.cookies.get("access_token")
    assert admin.post("/auth/logout").status_code == 204
    assert admin.get("/auth/me").status_code == 401
    # Clearing the browser cookie alone is insufficient if it was copied.
    admin.cookies.set("access_token", copied_cookie)
    assert admin.get("/auth/me").status_code == 401


def test_password_change_revokes_existing_sessions(admin):
    stale_cookie = admin.cookies.get("access_token")
    response = admin.patch(
        "/admin/users/1", json={"password": "new-password-123"}
    )
    assert response.status_code == 200
    admin.cookies.set("access_token", stale_cookie)
    assert admin.get("/auth/me").status_code == 401
    assert login(admin, password="new-password-123").status_code == 200


def test_oversized_password_returns_same_auth_error_for_known_and_unknown_email(client):
    password = "Ã©" * 37  # 74 UTF-8 bytes; under the character limit, over bcrypt's byte limit.
    known = login(client, password=password)
    unknown = login(client, password=password, email="ghost@test.com")
    assert known.status_code == unknown.status_code == 401
    assert known.json()["detail"] == unknown.json()["detail"]


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


def test_forwarded_address_is_not_trusted_for_rate_limiting(client, monkeypatch):
    """An untrusted caller cannot evade the peer-address bucket by spoofing XFF."""
    monkeypatch.setattr(settings, "login_max_attempts", 3)

    # Spoofed forwarded addresses do not create distinct address buckets.
    for index in range(3):
        response = client.post(
            "/auth/login",
            json={"email": "otro@test.com", "password": "nope"},
            headers={"X-Forwarded-For": f"203.0.113.{index}"},
        )
        assert response.status_code == 401

    blocked = client.post(
        "/auth/login",
        json={"email": "otro@test.com", "password": "nope"},
        headers={"X-Forwarded-For": "203.0.113.99"},
    )
    assert blocked.status_code == 429


def test_failures_from_other_peers_do_not_lock_out_the_account(client, monkeypatch):
    """A targeted attacker cannot consume a victim-specific login quota."""
    monkeypatch.setattr(settings, "login_max_attempts", 3)
    from app.auth import router as auth_router
    monkeypatch.setattr(
        auth_router, "client_key", lambda request: request.headers["x-test-peer"]
    )

    for index in range(3):
        response = client.post(
            "/auth/login",
            json={"email": ADMIN_EMAIL, "password": "nope"},
            headers={"X-Test-Peer": f"attacker-peer-{index}"},
        )
        assert response.status_code == 401

    success = client.post(
        "/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        headers={"X-Test-Peer": "administrator-peer"},
    )
    assert success.status_code == 200


def test_expired_rate_limit_buckets_are_garbage_collected(client, monkeypatch):
    from app.core import ratelimit

    now = [100.0]
    monkeypatch.setattr(ratelimit.time, "monotonic", lambda: now[0])
    ratelimit.check_rate_limit("email:arbitrary@example.test", 2, 10)
    assert "email:arbitrary@example.test" in ratelimit._attempts

    # The opportunistic sweep runs at least once per GC interval, even if this
    # particular expired key is never requested again.
    now[0] += ratelimit._GC_INTERVAL_SECONDS + 1
    ratelimit.check_rate_limit("ip:next-peer", 2, 10)
    assert "email:arbitrary@example.test" not in ratelimit._attempts
