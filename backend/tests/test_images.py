import io

import pytest

from app.core.config import settings

from .conftest import STRAIGHT_WIN_A, make_match, make_team

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100


def image(name="photo.png", content=PNG, content_type="image/png"):
    return {"file": (name, io.BytesIO(content), content_type)}


@pytest.fixture
def configured(monkeypatch):
    """Credentials that look valid but point nowhere."""
    monkeypatch.setattr(settings, "cloudinary_cloud_name", "demo")
    monkeypatch.setattr(settings, "cloudinary_api_key", "key")
    monkeypatch.setattr(settings, "cloudinary_api_secret", "secret")


def test_upload_needs_a_session(client):
    assert client.post("/admin/teams/1/photo", files=image()).status_code == 401


def test_without_credentials_the_answer_is_explicit(admin):
    team_id = make_team(admin)

    response = admin.post(f"/admin/teams/{team_id}/photo", files=image())

    assert response.status_code == 503
    assert response.json()["detail"] == "Image upload is not configured"


def test_an_unknown_team_fails_before_the_upload(admin, configured):
    assert admin.post("/admin/teams/999/photo", files=image()).status_code == 404


def test_an_unknown_sponsor_fails_before_the_upload(admin, configured):
    assert admin.post("/admin/sponsors/999/logo", files=image()).status_code == 404


def test_an_unknown_match_fails_before_the_upload(admin, configured):
    assert admin.post("/admin/matches/999/result/photo", files=image()).status_code == 404


def test_a_match_without_a_result_fails_before_the_upload(admin, configured):
    """The photo belongs to the result, and undoing the result would drop it."""
    match = make_match(admin, make_team(admin, name="Ana"), make_team(admin, name="Bea"))

    assert admin.post(f"/admin/matches/{match}/result/photo", files=image()).status_code == 400


def test_a_failed_upload_leaves_the_match_photo_untouched(admin, configured):
    match = make_match(admin, make_team(admin, name="Ana"), make_team(admin, name="Bea"))
    admin.post(f"/admin/matches/{match}/result", json=STRAIGHT_WIN_A)

    response = admin.post(f"/admin/matches/{match}/result/photo", files=image())

    assert response.status_code == 502
    assert admin.get(f"/admin/matches/{match}").json()["photo_url"] is None


def test_a_non_image_is_rejected(admin, configured):
    team_id = make_team(admin)

    response = admin.post(
        f"/admin/teams/{team_id}/photo",
        files=image("bad.pdf", b"%PDF", "application/pdf"),
    )

    assert response.status_code == 400


def test_an_oversized_image_is_rejected(admin, configured):
    team_id = make_team(admin)

    response = admin.post(
        f"/admin/teams/{team_id}/photo",
        files=image(content=b"0" * (6 * 1024 * 1024)),
    )

    assert response.status_code == 413


def test_a_failing_upload_does_not_leak_the_internal_error(admin, configured):
    team_id = make_team(admin)

    response = admin.post(f"/admin/teams/{team_id}/photo", files=image())

    assert response.status_code == 502
    assert response.json()["detail"] == "Image upload failed"


def test_a_failed_upload_leaves_the_photo_untouched(admin, configured):
    team_id = make_team(admin)

    admin.post(f"/admin/teams/{team_id}/photo", files=image())

    assert admin.get(f"/admin/teams/{team_id}").json()["photo_url"] is None
