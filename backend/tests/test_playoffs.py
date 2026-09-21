"""The playoff bracket: generation from standings, byes, and advancement.

Zones in these tests are built WITHOUT playing any group-stage matches. With
nothing played, every team in a zone ties on points, set difference and game
difference, so `calculate_standings`'s tie-break falls all the way through to
"sets won, then team id ascending" — meaning position 1 is simply the first
team created in that zone, position 2 the second, and so on. That gives fully
deterministic seeding for free, without needing a round robin.
"""

import pytest
from sqlmodel import Session, select

from app.database.session import engine
from app.matches.models import Match
from app.playoffs.models import PlayoffMatch, PlayoffRound, PlayoffSeed

from .conftest import STRAIGHT_WIN_A, STRAIGHT_WIN_B, ZONE_A, ZONE_B, make_match, make_team

TOTAL_NODES = 19


def _make_zone(admin, zone_id: int, count: int, prefix: str) -> list[int]:
    """`count` teams in `zone_id`, in creation order — team at `result[i]` is seed `i + 1`."""
    return [make_team(admin, zone_id, f"{prefix}{n}") for n in range(1, count + 1)]


def _seed(teams: list[int], position: int) -> int:
    return teams[position - 1]


def _round(bracket: dict, round_name: str) -> dict:
    return next(r for r in bracket["rounds"] if r["round"] == round_name)


def _node(round_body: dict, slot: int) -> dict:
    return next(n for n in round_body["nodes"] if n["slot"] == slot)


def _team_id(node: dict, side: str) -> int | None:
    team = node[side]
    return team["id"] if team else None


def _row_counts() -> tuple[int, int, int]:
    with Session(engine) as session:
        return (
            len(session.exec(select(PlayoffSeed)).all()),
            len(session.exec(select(PlayoffMatch)).all()),
            len(session.exec(select(Match)).all()),
        )


@pytest.fixture
def full_league(admin):
    """Ten pairs in each zone — every round-1 seed resolves, no byes."""
    zone_a = _make_zone(admin, ZONE_A, 10, "A")
    zone_b = _make_zone(admin, ZONE_B, 10, "B")
    return zone_a, zone_b


# --- Generation -----------------------------------------------------------------


def test_generating_the_bracket_creates_nineteen_nodes(admin, full_league):
    response = admin.post("/playoffs/generate")

    assert response.status_code == 201
    total = sum(len(r["nodes"]) for r in response.json()["rounds"])
    assert total == TOTAL_NODES


def test_generating_the_bracket_twice_is_rejected(admin, full_league):
    admin.post("/playoffs/generate")

    response = admin.post("/playoffs/generate")

    assert response.status_code == 409


def test_round_1_pairings_match_the_documented_cross(admin, full_league):
    zone_a, zone_b = full_league
    admin.post("/playoffs/generate")

    round_1 = _round(admin.get("/playoffs/bracket").json(), "round_1")

    expected = {
        1: (("A", 3), ("B", 10)),
        5: (("A", 7), ("B", 6)),
        8: (("A", 10), ("B", 3)),
        4: (("A", 6), ("B", 7)),
        2: (("A", 4), ("B", 9)),
        6: (("A", 8), ("B", 5)),
        7: (("A", 9), ("B", 4)),
        3: (("A", 5), ("B", 8)),
    }
    zones = {"A": zone_a, "B": zone_b}

    for slot, (seed_a, seed_b) in expected.items():
        node = _node(round_1, slot)
        assert node["team_a"]["id"] == _seed(zones[seed_a[0]], seed_a[1])
        assert node["team_b"]["id"] == _seed(zones[seed_b[0]], seed_b[1])
        assert node["status"] == "pending"
        assert node["match"] is not None


def test_seed_1a_and_1b_land_in_opposite_bracket_halves(admin, full_league):
    """Assert on the persisted node graph, not on a copy of the template."""
    zone_a, zone_b = full_league
    admin.post("/playoffs/generate")

    bracket = admin.get("/playoffs/bracket").json()
    quarterfinal = _round(bracket, "quarterfinal")
    qf_1a = _node(quarterfinal, 1)  # side a = (A, 1)
    qf_1b = _node(quarterfinal, 4)  # side a = (B, 1)

    assert qf_1a["team_a"]["id"] == _seed(zone_a, 1)
    assert qf_1b["team_a"]["id"] == _seed(zone_b, 1)

    with Session(engine) as session:
        node_1a = session.exec(
            select(PlayoffMatch).where(
                PlayoffMatch.round == PlayoffRound.QUARTERFINAL, PlayoffMatch.slot == 1
            )
        ).one()
        node_1b = session.exec(
            select(PlayoffMatch).where(
                PlayoffMatch.round == PlayoffRound.QUARTERFINAL, PlayoffMatch.slot == 4
            )
        ).one()

    # 1A and 1B only meet again if they both reach the final: their
    # quarterfinals must feed two DIFFERENT semifinal nodes.
    assert node_1a.next_match_id != node_1b.next_match_id


def test_a_short_zone_leaves_an_orphan_bye_that_propagates_without_a_match(admin):
    zone_a = _make_zone(admin, ZONE_A, 10, "A")
    zone_b = _make_zone(admin, ZONE_B, 9, "B")  # no position 10

    admin.post("/playoffs/generate")
    bracket = admin.get("/playoffs/bracket").json()

    round_1 = _round(bracket, "round_1")
    orphan = _node(round_1, 1)  # (A, 3) vs (B, 10) — B10 does not exist

    assert orphan["status"] == "bye"
    assert orphan["team_a"]["id"] == _seed(zone_a, 3)
    assert orphan["team_b"] is None
    assert orphan["match"] is None

    round_2 = _round(bracket, "round_2")
    destination = _node(round_2, 1)  # round-1 slot 1 feeds round-2 slot 1, side a

    assert destination["team_a"]["id"] == _seed(zone_a, 3)
    assert destination["team_b"] is None
    assert destination["match"] is None


def test_generate_is_refused_while_group_stage_matches_are_pending(admin, full_league):
    zone_a, _ = full_league
    pending_id = make_match(admin, zone_a[0], zone_a[1])

    response = admin.post("/playoffs/generate")

    assert response.status_code == 409
    body = response.json()["detail"]
    assert body["pending_count"] == 1
    assert body["pending_matches"] == [
        {
            "id": pending_id,
            "team_a": {"id": zone_a[0], "player_one_name": "A1", "player_two_name": "A12"},
            "team_b": {"id": zone_a[1], "player_one_name": "A2", "player_two_name": "A22"},
        }
    ]
    # Refused before anything is written: still a projection, not a bracket.
    assert admin.get("/playoffs/bracket").json()["mode"] == "projection"


def test_generate_with_force_ignores_pending_group_stage_matches(admin, full_league):
    zone_a, _ = full_league
    make_match(admin, zone_a[0], zone_a[1])

    response = admin.post("/playoffs/generate", json={"force": True})

    assert response.status_code == 201
    total = sum(len(r["nodes"]) for r in response.json()["rounds"])
    assert total == TOTAL_NODES


# --- Advance ----------------------------------------------------------------------


def test_advancing_fills_the_right_round_2_slot(admin, full_league):
    admin.post("/playoffs/generate")
    round_1 = _round(admin.get("/playoffs/bracket").json(), "round_1")
    slot8 = _node(round_1, 8)  # (A,10) vs (B,3) -> round_2 slot 2, side a

    admin.post(f"/admin/matches/{slot8['match']['id']}/result", json=STRAIGHT_WIN_A)

    round_2 = _round(admin.get("/playoffs/bracket").json(), "round_2")
    destination = _node(round_2, 2)

    assert destination["team_a"]["id"] == slot8["team_a"]["id"]
    assert destination["team_b"] is None
    assert destination["match"] is None


def test_the_round_2_match_is_created_only_once_both_sides_are_known(admin, full_league):
    admin.post("/playoffs/generate")
    round_1 = _round(admin.get("/playoffs/bracket").json(), "round_1")
    slot8 = _node(round_1, 8)  # -> round_2 slot 2, side a
    slot4 = _node(round_1, 4)  # -> round_2 slot 2, side b

    admin.post(f"/admin/matches/{slot8['match']['id']}/result", json=STRAIGHT_WIN_A)

    still_waiting = _node(_round(admin.get("/playoffs/bracket").json(), "round_2"), 2)
    assert still_waiting["match"] is None

    admin.post(f"/admin/matches/{slot4['match']['id']}/result", json=STRAIGHT_WIN_A)

    completed = _node(_round(admin.get("/playoffs/bracket").json(), "round_2"), 2)
    assert completed["team_a"] is not None
    assert completed["team_b"] is not None
    assert completed["match"] is not None
    assert completed["match"]["status"] == "pending"


def test_correcting_a_round_1_result_updates_the_still_unplayed_round_2_pairing(admin, full_league):
    admin.post("/playoffs/generate")
    round_1 = _round(admin.get("/playoffs/bracket").json(), "round_1")
    slot8 = _node(round_1, 8)  # (A,10) vs (B,3) -> round_2 slot 2, side a
    match_id = slot8["match"]["id"]

    admin.post(f"/admin/matches/{match_id}/result", json=STRAIGHT_WIN_A)
    before = _node(_round(admin.get("/playoffs/bracket").json(), "round_2"), 2)
    assert before["team_a"]["id"] == slot8["team_a"]["id"]

    response = admin.put(f"/admin/matches/{match_id}/result", json=STRAIGHT_WIN_B)

    assert response.status_code == 200
    after = _node(_round(admin.get("/playoffs/bracket").json(), "round_2"), 2)
    assert after["team_a"]["id"] == slot8["team_b"]["id"]
    assert after["team_a"]["id"] != before["team_a"]["id"]


def test_correcting_a_result_that_already_advanced_unplays_the_downstream_match(admin, full_league):
    """The explicit correction case the design flags: undo, then redo, downstream."""
    admin.post("/playoffs/generate")
    round_1 = _round(admin.get("/playoffs/bracket").json(), "round_1")
    slot8 = _node(round_1, 8)  # -> round_2 slot 2, side a
    slot4 = _node(round_1, 4)  # -> round_2 slot 2, side b

    admin.post(f"/admin/matches/{slot8['match']['id']}/result", json=STRAIGHT_WIN_A)
    admin.post(f"/admin/matches/{slot4['match']['id']}/result", json=STRAIGHT_WIN_A)
    round_2_match_id = _node(_round(admin.get("/playoffs/bracket").json(), "round_2"), 2)["match"]["id"]
    admin.post(f"/admin/matches/{round_2_match_id}/result", json=STRAIGHT_WIN_A)

    played = _node(_round(admin.get("/playoffs/bracket").json(), "round_2"), 2)
    assert played["match"]["status"] == "played"

    # Flip who won round-1 slot 8. Round-2 slot 2 already trusted the old
    # winner and had itself been played — that result must be undone.
    response = admin.put(f"/admin/matches/{slot8['match']['id']}/result", json=STRAIGHT_WIN_B)

    assert response.status_code == 200
    unplayed = _node(_round(admin.get("/playoffs/bracket").json(), "round_2"), 2)
    assert unplayed["match"]["status"] == "pending"
    assert unplayed["match"]["sets"] == []
    assert unplayed["team_a"]["id"] == slot8["team_b"]["id"]


# --- Wipe -------------------------------------------------------------------------


def test_deleting_the_bracket_allows_regenerating_it(admin, full_league):
    admin.post("/playoffs/generate")

    response = admin.delete("/playoffs")

    assert response.status_code == 204
    assert admin.post("/playoffs/generate").status_code == 201


def test_delete_is_refused_once_a_bracket_result_is_loaded(admin, full_league):
    admin.post("/playoffs/generate")
    slot1 = _node(_round(admin.get("/playoffs/bracket").json(), "round_1"), 1)
    admin.post(f"/admin/matches/{slot1['match']['id']}/result", json=STRAIGHT_WIN_A)

    response = admin.delete("/playoffs")

    assert response.status_code == 409
    assert response.json()["detail"]["played_count"] == 1
    # Refused: the bracket (with its result) is still there.
    assert admin.get("/playoffs/bracket").status_code == 200


def test_delete_with_force_wipes_a_bracket_that_has_results(admin, full_league):
    admin.post("/playoffs/generate")
    slot1 = _node(_round(admin.get("/playoffs/bracket").json(), "round_1"), 1)
    admin.post(f"/admin/matches/{slot1['match']['id']}/result", json=STRAIGHT_WIN_A)

    response = admin.delete("/playoffs", params={"force": "true"})

    assert response.status_code == 204
    assert admin.get("/playoffs/bracket").json()["mode"] == "projection"


# --- Projection / official mode -----------------------------------------------------


def test_the_projection_writes_nothing(admin, full_league):
    zone_a, _ = full_league
    make_match(admin, zone_a[0], zone_a[1])  # a real group-stage match, so counts are non-trivial
    before = _row_counts()
    assert before[2] == 1  # sanity: the group-stage match really exists

    response = admin.get("/playoffs/bracket")

    assert response.status_code == 200
    assert response.json()["mode"] == "projection"
    assert _row_counts() == before


def test_a_group_stage_result_that_reorders_standings_changes_the_projection(admin, full_league):
    zone_a, _ = full_league
    before = _node(_round(admin.get("/playoffs/bracket").json(), "round_1"), 1)
    assert before["team_a"]["id"] == _seed(zone_a, 3)

    # zone_a[9] (currently seed 10, last by the tie-break) beats zone_a[2]
    # (currently seed 3): zone_a[9] jumps to seed 1, and seed 3 becomes
    # whoever was seed 2 before.
    match_id = make_match(admin, zone_a[9], zone_a[2])
    admin.post(f"/admin/matches/{match_id}/result", json=STRAIGHT_WIN_A)

    after = _node(_round(admin.get("/playoffs/bracket").json(), "round_1"), 1)
    assert after["team_a"]["id"] == zone_a[1]
    assert after["team_a"]["id"] != before["team_a"]["id"]


def test_projection_matches_what_generation_actually_produces(admin, full_league):
    """Compared against a real generated bracket, not a hardcoded expectation."""
    zone_a, zone_b = full_league
    # Shake up both zones' standings so this is not just testing the tie-break.
    first = make_match(admin, zone_a[9], zone_a[2])
    admin.post(f"/admin/matches/{first}/result", json=STRAIGHT_WIN_A)
    second = make_match(admin, zone_b[8], zone_b[0])
    admin.post(f"/admin/matches/{second}/result", json=STRAIGHT_WIN_A)

    projection = admin.get("/playoffs/bracket").json()
    assert projection["mode"] == "projection"

    official = admin.post("/playoffs/generate", json={"force": True}).json()
    assert official["mode"] == "official"

    proj_round_1, off_round_1 = _round(projection, "round_1"), _round(official, "round_1")
    for slot in range(1, 9):
        proj_node, off_node = _node(proj_round_1, slot), _node(off_round_1, slot)
        assert _team_id(proj_node, "team_a") == _team_id(off_node, "team_a")
        assert _team_id(proj_node, "team_b") == _team_id(off_node, "team_b")

    proj_qf, off_qf = _round(projection, "quarterfinal"), _round(official, "quarterfinal")
    for slot in range(1, 5):
        assert _team_id(_node(proj_qf, slot), "team_a") == _team_id(_node(off_qf, slot), "team_a")


def test_projection_shows_a_bye_for_a_short_zone(admin):
    zone_a = _make_zone(admin, ZONE_A, 10, "A")
    _make_zone(admin, ZONE_B, 9, "B")  # no position 10

    bracket = admin.get("/playoffs/bracket").json()
    assert bracket["mode"] == "projection"

    orphan = _node(_round(bracket, "round_1"), 1)  # (A,3) vs (B,10) — B10 does not exist
    assert orphan["status"] == "bye"
    assert orphan["team_a"]["id"] == _seed(zone_a, 3)
    assert orphan["team_b"] is None
    assert orphan["match"] is None


def test_the_bracket_endpoint_switches_to_official_after_generation_and_stays_there(admin, full_league):
    assert admin.get("/playoffs/bracket").json()["mode"] == "projection"

    admin.post("/playoffs/generate")

    response = admin.get("/playoffs/bracket").json()
    assert response["mode"] == "official"
    assert response["pending_group_matches"] is None
    # Real, persisted node ids now — a projection's nodes never carry one.
    round_1 = _round(response, "round_1")
    assert all(node["id"] is not None for node in round_1["nodes"])


def test_correcting_a_group_stage_result_after_generation_does_not_reseed_the_bracket(admin, full_league):
    zone_a, _ = full_league
    match_id = make_match(admin, zone_a[9], zone_a[2])
    admin.post(f"/admin/matches/{match_id}/result", json=STRAIGHT_WIN_A)  # zone_a[9] becomes seed 1

    admin.post("/playoffs/generate", json={"force": True})
    before = _node(_round(admin.get("/playoffs/bracket").json(), "quarterfinal"), 1)  # side a = (A, 1)
    assert before["team_a"]["id"] == zone_a[9]

    # Correct the group-stage result after the fact: flip the winner back.
    admin.put(f"/admin/matches/{match_id}/result", json=STRAIGHT_WIN_B)

    after = _node(_round(admin.get("/playoffs/bracket").json(), "quarterfinal"), 1)
    assert after["team_a"]["id"] == zone_a[9]  # unchanged: the snapshot is frozen
