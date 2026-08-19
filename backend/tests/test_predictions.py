"""The season prediction: who finishes first and second in each zone.

Runs inside a window the admin opens. Results stay hidden until it closes,
because showing a running count while people vote turns a prediction into a
bandwagon.
"""

import pytest

from .conftest import ZONE_A, ZONE_B, make_team

DEVICE = "device-key-aaaaaaaaaaaa"
OTHER_DEVICE = "device-key-bbbbbbbbbbbb"


@pytest.fixture
def zone_a(admin):
    return [make_team(admin, ZONE_A, name) for name in ("Ana", "Beto", "Caro")]


@pytest.fixture
def zone_b(admin):
    return [make_team(admin, ZONE_B, name) for name in ("Dani", "Eli", "Fabi")]


@pytest.fixture
def open_poll(admin):
    response = admin.post("/admin/predictions/open", json={"days": 7})
    assert response.status_code == 200
    return response.json()


def predict(client, zone_id, first, second, device=DEVICE):
    return client.post(
        "/public/predictions",
        json={
            "voter_key": device,
            "zones": [
                {"zone_id": zone_id, "first_team_id": first, "second_team_id": second}
            ],
        },
    )


def test_without_a_window_the_poll_is_closed(client):
    body = client.get("/public/predictions").json()

    assert body["open"] is False
    assert body["closes_at"] is None


def test_opening_the_poll_sets_a_closing_date(client, open_poll):
    body = client.get("/public/predictions").json()

    assert body["open"] is True
    assert body["closes_at"] is not None


def test_a_prediction_is_recorded(client, open_poll, zone_a):
    response = predict(client, ZONE_A, zone_a[0], zone_a[1])

    assert response.status_code == 200
    assert response.json()["voted"] is True


def test_the_device_gets_its_own_picks_back(client, open_poll, zone_a):
    predict(client, ZONE_A, zone_a[0], zone_a[1])

    body = client.get(f"/public/predictions?voter_key={DEVICE}").json()

    assert body["voted"] is True
    assert body["zones"] == [
        {"zone_id": ZONE_A, "first_team_id": zone_a[0], "second_team_id": zone_a[1]}
    ]


def test_another_device_sees_no_picks(client, open_poll, zone_a):
    predict(client, ZONE_A, zone_a[0], zone_a[1])

    body = client.get(f"/public/predictions?voter_key={OTHER_DEVICE}").json()

    assert body["voted"] is False
    assert body["zones"] == []


def test_predicting_again_replaces_the_previous_pick(client, open_poll, zone_a):
    predict(client, ZONE_A, zone_a[0], zone_a[1])
    predict(client, ZONE_A, zone_a[2], zone_a[0])

    admin_view = client.get(f"/public/predictions?voter_key={DEVICE}").json()

    assert admin_view["zones"] == [
        {"zone_id": ZONE_A, "first_team_id": zone_a[2], "second_team_id": zone_a[0]}
    ]


def test_the_same_pair_cannot_be_first_and_second(client, open_poll, zone_a):
    assert predict(client, ZONE_A, zone_a[0], zone_a[0]).status_code == 400


def test_a_pair_from_another_zone_is_rejected(client, open_poll, zone_a, zone_b):
    assert predict(client, ZONE_A, zone_a[0], zone_b[0]).status_code == 400


def test_voting_with_the_poll_closed_is_rejected(admin, client, zone_a):
    assert predict(client, ZONE_A, zone_a[0], zone_a[1]).status_code == 409


def test_closing_the_poll_stops_new_votes(admin, client, open_poll, zone_a):
    admin.post("/admin/predictions/close")

    assert predict(client, ZONE_A, zone_a[0], zone_a[1]).status_code == 409


def test_results_are_hidden_while_the_poll_is_open(client, open_poll, zone_a):
    predict(client, ZONE_A, zone_a[0], zone_a[1])

    assert client.get("/public/predictions/results").status_code == 409


def test_results_appear_once_the_poll_closes(admin, client, open_poll, zone_a):
    predict(client, ZONE_A, zone_a[0], zone_a[1], DEVICE)
    predict(client, ZONE_A, zone_a[0], zone_a[2], OTHER_DEVICE)
    admin.post("/admin/predictions/close")

    body = client.get("/public/predictions/results").json()
    zone = next(row for row in body["zones"] if row["zone_id"] == ZONE_A)
    winner = next(team for team in zone["teams"] if team["team_id"] == zone_a[0])

    assert body["voters"] == 2
    # Two firsts and no seconds: first is worth two points, second one.
    assert winner["first_votes"] == 2
    assert winner["second_votes"] == 0
    assert winner["points"] == 4


def test_the_ranking_is_ordered_by_points(admin, client, open_poll, zone_a):
    predict(client, ZONE_A, zone_a[1], zone_a[0], DEVICE)
    predict(client, ZONE_A, zone_a[1], zone_a[2], OTHER_DEVICE)
    admin.post("/admin/predictions/close")

    zone = next(
        row
        for row in client.get("/public/predictions/results").json()["zones"]
        if row["zone_id"] == ZONE_A
    )

    assert zone["teams"][0]["team_id"] == zone_a[1]
    assert zone["teams"][0]["points"] == 4


def test_only_an_admin_can_open_the_poll(client):
    assert client.post("/admin/predictions/open", json={"days": 7}).status_code == 401


def test_only_an_admin_can_close_the_poll(guest, open_poll):
    # `guest` and not `client`: opening the poll logged the shared client in.
    assert guest.post("/admin/predictions/close").status_code == 401
