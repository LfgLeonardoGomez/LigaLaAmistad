"""Cookie-authenticated writes require the configured UI Origin and a custom header."""

from app.core.csrf import require_same_origin
from app.main import (
    admin_users_router,
    americanos_router,
    auth_router,
    matches_router,
    playoffs_router,
    predictions_router,
    sponsors_router,
    teams_router,
)


def test_every_cookie_authenticated_mutation_router_has_csrf_dependency():
    cookie_authenticated_routers = (
        auth_router,
        admin_users_router,
        teams_router,
        matches_router,
        sponsors_router,
        predictions_router,
        playoffs_router,
        americanos_router,
    )

    assert all(
        any(dependency.dependency is require_same_origin for dependency in router.dependencies)
        for router in cookie_authenticated_routers
    )


def test_authenticated_admin_write_rejects_missing_csrf_header(admin):
    admin.headers.pop("X-Requested-With")

    response = admin.post(
        "/admin/predictions/close",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        content="",
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Cross-site request rejected"


def test_authenticated_admin_write_rejects_untrusted_origin(admin):
    response = admin.post(
        "/admin/predictions/close",
        headers={"Origin": "https://attacker.example"},
        content="",
    )

    assert response.status_code == 403


def test_authenticated_admin_write_accepts_configured_origin_and_header(admin):
    response = admin.post("/admin/predictions/open", json={"days": 1})

    assert response.status_code == 200
    assert response.json()["open"] is True


def test_auth_logout_requires_csrf_protection(admin):
    admin.headers["Origin"] = "https://attacker.example"

    response = admin.post("/auth/logout")

    assert response.status_code == 403
    assert admin.get("/auth/me").status_code == 200


def test_cors_preflight_allows_csrf_header_only_from_configured_origin(client):
    trusted = client.options(
        "/admin/teams",
        headers={
            "Origin": "http://testserver",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "x-requested-with",
        },
    )
    untrusted = client.options(
        "/admin/teams",
        headers={
            "Origin": "https://attacker.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "x-requested-with",
        },
    )

    assert trusted.status_code == 200
    assert "x-requested-with" in trusted.headers["access-control-allow-headers"].lower()
    assert untrusted.status_code == 400
