"""The playoff bracket: generation from standings, byes, and advancement.

Zones in these tests are built WITHOUT playing any group-stage matches. With
nothing played, every team in a zone ties on points, set difference and game
difference, so `calculate_standings`'s tie-break falls all the way through to
"sets won, then team id ascending" — meaning position 1 is simply the first
team created in that zone, position 2 the second, and so on. That gives fully
deterministic seeding for free, without needing a round robin.
"""

import itertools

import pytest
from sqlmodel import Session, select

from app.database.session import engine
from app.matches.models import Match
from app.playoffs.models import PlayoffMatch, PlayoffRound, PlayoffSeed
from app.playoffs.service import DRAW_ORDER

from .conftest import STRAIGHT_WIN_A, STRAIGHT_WIN_B, ZONE_A, ZONE_B, make_match, make_team

TOTAL_NODES = 19


def _make_zone(admin, zone_id: int, count: int, prefix: str) -> list[int]:
    """`count` teams in `zone_id`, in creation order — team at `result[i]` is seed `i + 1`."""
    return [make_team(admin, zone_id, f"{prefix}{n}") for n in range(1, count + 1)]


def _play_every_pairing(admin, team_ids: list[int]) -> None:
    """Creates and plays a match for every unordered pair in `team_ids`.

    For finishing a zone's group stage in a guard test: the pairing itself is
    what the guard counts (see `app.playoffs.service._group_stage_pairings`),
    so this mirrors it exactly rather than looping some other way.
    """
    for team_a_id, team_b_id in itertools.combinations(team_ids, 2):
        match_id = make_match(admin, team_a_id, team_b_id)
        admin.post(f"/admin/matches/{match_id}/result", json=STRAIGHT_WIN_A)


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


@pytest.fixture
def small_league(admin):
    """Two pairs in each zone — exactly one cross-pairing per zone, small
    enough to assert the full pending-pairings list by hand. Used only by the
    pending-group-stage guard tests below, which care about pairing-level
    behaviour, not about a realistic bracket shape."""
    zone_a = _make_zone(admin, ZONE_A, 2, "A")
    zone_b = _make_zone(admin, ZONE_B, 2, "B")
    return zone_a, zone_b


# --- Generation -----------------------------------------------------------------


def test_generating_the_bracket_creates_nineteen_nodes(admin, full_league):
    response = admin.post("/playoffs/generate", json={"force": True})

    assert response.status_code == 201
    total = sum(len(r["nodes"]) for r in response.json()["rounds"])
    assert total == TOTAL_NODES


def test_generating_the_bracket_twice_is_rejected(admin, full_league):
    admin.post("/playoffs/generate", json={"force": True})

    response = admin.post("/playoffs/generate")

    assert response.status_code == 409


def test_round_1_pairings_match_the_documented_cross(admin, full_league):
    zone_a, zone_b = full_league
    admin.post("/playoffs/generate", json={"force": True})

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
    admin.post("/playoffs/generate", json={"force": True})

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

    admin.post("/playoffs/generate", json={"force": True})
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


def test_generate_is_refused_while_group_stage_matches_are_pending(admin, small_league):
    zone_a, zone_b = small_league
    pending_id = make_match(admin, zone_a[0], zone_a[1])
    # zone_b's only pairing (B1, B2) never gets a `Match` row at all — the
    # exact case that used to be invisible to this guard: a pairing with no
    # match row is exactly as unplayed as one stuck in `pending`.

    response = admin.post("/playoffs/generate")

    assert response.status_code == 409
    body = response.json()["detail"]
    assert body["pending_count"] == 2
    by_id = {m["id"]: m for m in body["pending_matches"]}
    assert set(by_id) == {pending_id, None}
    assert by_id[pending_id]["team_a"] == {
        "id": zone_a[0],
        "player_one_name": "A1",
        "player_two_name": "A12",
        "photo_url": None,
        "seed": "1A",
    }
    assert by_id[pending_id]["team_b"] == {
        "id": zone_a[1],
        "player_one_name": "A2",
        "player_two_name": "A22",
        "photo_url": None,
        "seed": "2A",
    }
    assert {by_id[None]["team_a"]["id"], by_id[None]["team_b"]["id"]} == {zone_b[0], zone_b[1]}
    # Refused before anything is written: still a projection, not a bracket.
    assert admin.get("/playoffs/bracket").json()["mode"] == "projection"


def test_a_played_pairing_is_not_counted_pending(admin, small_league):
    zone_a, zone_b = small_league
    match_id = make_match(admin, zone_a[0], zone_a[1])
    admin.post(f"/admin/matches/{match_id}/result", json=STRAIGHT_WIN_A)

    response = admin.post("/playoffs/generate")

    assert response.status_code == 409
    body = response.json()["detail"]
    # Only zone B's pairing remains — zone A's is PLAYED now.
    assert body["pending_count"] == 1
    assert body["pending_matches"][0]["id"] is None
    assert {body["pending_matches"][0]["team_a"]["id"], body["pending_matches"][0]["team_b"]["id"]} == {
        zone_b[0],
        zone_b[1],
    }


def test_a_withdrawn_teams_pairing_is_never_counted_pending(admin, small_league):
    zone_a, zone_b = small_league
    admin.patch(f"/admin/teams/{zone_a[1]}", json={"status": "withdrawn"})

    response = admin.post("/playoffs/generate")

    assert response.status_code == 409
    body = response.json()["detail"]
    # Zone A's only pairing involves the withdrawn team and is excluded
    # entirely — it can never be played, so it must never demand `force`.
    assert body["pending_count"] == 1
    remaining = body["pending_matches"][0]
    assert {remaining["team_a"]["id"], remaining["team_b"]["id"]} == {zone_b[0], zone_b[1]}


def test_pending_count_agrees_between_projection_and_generate_guard(admin, small_league):
    zone_a, _ = small_league
    make_match(admin, zone_a[0], zone_a[1])

    projection = admin.get("/playoffs/bracket").json()
    guard_body = admin.post("/playoffs/generate").json()["detail"]

    assert projection["mode"] == "projection"
    assert projection["pending_group_matches"] == guard_body["pending_count"] == 2


def test_generate_succeeds_without_force_once_every_pairing_is_played(admin, small_league):
    """The guard's other half: once the group stage has genuinely finished,
    no `force` should be needed at all. This is the test a permanently-closed
    guard — say, a pairing computation that always reports something
    outstanding — would fail while every 409-only test above stayed green."""
    zone_a, zone_b = small_league
    _play_every_pairing(admin, zone_a)
    _play_every_pairing(admin, zone_b)

    assert admin.get("/playoffs/bracket").json()["pending_group_matches"] == 0

    response = admin.post("/playoffs/generate")

    assert response.status_code == 201
    assert admin.get("/playoffs/bracket").json()["mode"] == "official"


def test_generate_succeeds_without_force_when_only_a_withdrawn_pairing_remains(admin, small_league):
    """Pins the product decision as behaviour, not just as a comment on
    `_group_stage_pairings`: a withdrawn team's own pairing must never keep
    the guard closed, even with no `force` at all."""
    zone_a, zone_b = small_league
    _play_every_pairing(admin, zone_b)
    # Zone A's only pairing (A1 vs A2) is left unplayed, with no match row —
    # instead one of the two is withdrawn, so that pairing can never be
    # played and must never count.
    admin.patch(f"/admin/teams/{zone_a[1]}", json={"status": "withdrawn"})

    response = admin.post("/playoffs/generate")

    assert response.status_code == 201
    assert admin.get("/playoffs/bracket").json()["mode"] == "official"


def test_generate_with_force_ignores_pending_group_stage_matches(admin, full_league):
    zone_a, _ = full_league
    make_match(admin, zone_a[0], zone_a[1])

    response = admin.post("/playoffs/generate", json={"force": True})

    assert response.status_code == 201
    total = sum(len(r["nodes"]) for r in response.json()["rounds"])
    assert total == TOTAL_NODES


# --- Advance ----------------------------------------------------------------------


def test_advancing_fills_the_right_round_2_slot(admin, full_league):
    admin.post("/playoffs/generate", json={"force": True})
    round_1 = _round(admin.get("/playoffs/bracket").json(), "round_1")
    slot8 = _node(round_1, 8)  # (A,10) vs (B,3) -> round_2 slot 2, side a

    admin.post(f"/admin/matches/{slot8['match']['id']}/result", json=STRAIGHT_WIN_A)

    round_2 = _round(admin.get("/playoffs/bracket").json(), "round_2")
    destination = _node(round_2, 2)

    assert destination["team_a"]["id"] == slot8["team_a"]["id"]
    assert destination["team_b"] is None
    assert destination["match"] is None


def test_the_round_2_match_is_created_only_once_both_sides_are_known(admin, full_league):
    admin.post("/playoffs/generate", json={"force": True})
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
    admin.post("/playoffs/generate", json={"force": True})
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
    admin.post("/playoffs/generate", json={"force": True})
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
    admin.post("/playoffs/generate", json={"force": True})

    response = admin.delete("/playoffs")

    assert response.status_code == 204
    assert admin.post("/playoffs/generate", json={"force": True}).status_code == 201


def test_delete_is_refused_once_a_bracket_result_is_loaded(admin, full_league):
    admin.post("/playoffs/generate", json={"force": True})
    slot1 = _node(_round(admin.get("/playoffs/bracket").json(), "round_1"), 1)
    admin.post(f"/admin/matches/{slot1['match']['id']}/result", json=STRAIGHT_WIN_A)

    response = admin.delete("/playoffs")

    assert response.status_code == 409
    assert response.json()["detail"]["played_count"] == 1
    # Refused: the bracket (with its result) is still there.
    assert admin.get("/playoffs/bracket").status_code == 200


def test_delete_with_force_wipes_a_bracket_that_has_results(admin, full_league):
    admin.post("/playoffs/generate", json={"force": True})
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

    admin.post("/playoffs/generate", json={"force": True})

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


# --- Draw order --------------------------------------------------------------------

ROUND_1_DRAW_ORDER = (7, 3, 1, 5, 8, 4, 2, 6)
ROUND_2_DRAW_ORDER = (4, 1, 2, 3)


def test_official_bracket_returns_round_1_and_round_2_in_draw_order(admin, full_league):
    admin.post("/playoffs/generate", json={"force": True})

    bracket = admin.get("/playoffs/bracket").json()

    assert [n["slot"] for n in _round(bracket, "round_1")["nodes"]] == list(ROUND_1_DRAW_ORDER)
    assert [n["slot"] for n in _round(bracket, "round_2")["nodes"]] == list(ROUND_2_DRAW_ORDER)


def test_projection_bracket_returns_round_1_and_round_2_in_draw_order(admin, full_league):
    bracket = admin.get("/playoffs/bracket").json()
    assert bracket["mode"] == "projection"

    assert [n["slot"] for n in _round(bracket, "round_1")["nodes"]] == list(ROUND_1_DRAW_ORDER)
    assert [n["slot"] for n in _round(bracket, "round_2")["nodes"]] == list(ROUND_2_DRAW_ORDER)


def test_draw_order_constant_matches_the_documented_sequence():
    """The literal sequences above are the ones the brief hand-checked; pin them."""
    assert DRAW_ORDER[PlayoffRound.ROUND_1] == ROUND_1_DRAW_ORDER
    assert DRAW_ORDER[PlayoffRound.ROUND_2] == ROUND_2_DRAW_ORDER
    # The last three rounds coincide with slot order, per the brief.
    assert DRAW_ORDER[PlayoffRound.QUARTERFINAL] == (1, 2, 3, 4)
    assert DRAW_ORDER[PlayoffRound.SEMIFINAL] == (1, 2)
    assert DRAW_ORDER[PlayoffRound.FINAL] == (1,)


def test_draw_order_invariant_each_round_wires_straight_into_the_next(admin, full_league):
    """No crossing lines: walking a round's nodes in draw order and following
    each one's wire forward lands on the next round's nodes in ITS draw
    order too (collapsing repeats — a node fed by two of this round's nodes
    is visited twice in a row, once per feeder)."""
    admin.post("/playoffs/generate", json={"force": True})

    with Session(engine) as session:
        all_nodes = list(session.exec(select(PlayoffMatch)).all())

    nodes_by_round_slot = {(n.round, n.slot): n for n in all_nodes}
    slot_by_id = {n.id: (n.round, n.slot) for n in all_nodes}

    round_order = list(PlayoffRound)
    # PlayoffRound enum iteration order matches declaration order (round_1..final).
    for this_round, next_round in zip(round_order, round_order[1:]):
        this_order = DRAW_ORDER[this_round]
        next_order = DRAW_ORDER[next_round]

        forward_slots: list[int] = []
        for slot in this_order:
            node = nodes_by_round_slot[(this_round, slot)]
            assert node.next_match_id is not None
            _, dest_slot = slot_by_id[node.next_match_id]
            if not forward_slots or forward_slots[-1] != dest_slot:
                forward_slots.append(dest_slot)

        assert tuple(forward_slots) == next_order


# --- Team photo -----------------------------------------------------------------


def test_bracket_nodes_carry_each_teams_photo_url(admin, full_league):
    """No second request needed: the bracket modal shows a pair's photo straight
    from this payload."""
    zone_a, _ = full_league
    photographed_team_id = _seed(zone_a, 3)  # seeds round_1 slot 1, side a
    response = admin.patch(
        f"/admin/teams/{photographed_team_id}",
        json={"photo_url": "https://example.com/foto.jpg"},
    )
    assert response.status_code == 200

    bracket = admin.get("/playoffs/bracket").json()
    node = _node(_round(bracket, "round_1"), 1)

    assert node["team_a"]["id"] == photographed_team_id
    assert node["team_a"]["photo_url"] == "https://example.com/foto.jpg"
    assert node["team_b"]["photo_url"] is None


# --- Seed labels -----------------------------------------------------------------
#
# The seed is a property of the TEAM, not of the node it currently occupies:
# these tests specifically reach into rounds `BRACKET_TEMPLATE` never seeds
# directly (round 2, the semifinal) to prove the label follows the team
# through advancement, not just the handful of slots a per-node table could
# have covered.


def test_official_bracket_gives_every_resolved_team_its_seed_through_every_round(admin, full_league):
    admin.post("/playoffs/generate", json={"force": True})

    round_1 = _round(admin.get("/playoffs/bracket").json(), "round_1")
    slot1 = _node(round_1, 1)  # (A,3) vs (B,10) -> round_2 slot 1, side a
    slot5 = _node(round_1, 5)  # (A,7) vs (B,6) -> round_2 slot 1, side b
    admin.post(f"/admin/matches/{slot1['match']['id']}/result", json=STRAIGHT_WIN_A)  # A3 advances
    admin.post(f"/admin/matches/{slot5['match']['id']}/result", json=STRAIGHT_WIN_A)  # A7 advances

    round_2 = _round(admin.get("/playoffs/bracket").json(), "round_2")
    r2_node = _node(round_2, 1)
    assert r2_node["team_a"]["seed"] == "3A"
    assert r2_node["team_b"]["seed"] == "7A"

    admin.post(f"/admin/matches/{r2_node['match']['id']}/result", json=STRAIGHT_WIN_A)  # A3 advances again

    quarterfinal = _round(admin.get("/playoffs/bracket").json(), "quarterfinal")
    qf2 = _node(quarterfinal, 2)  # side a = seed (B,2); side b = round-2 slot-1 winner
    assert qf2["team_a"]["seed"] == "2B"
    assert qf2["team_b"]["seed"] == "3A"

    admin.post(f"/admin/matches/{qf2['match']['id']}/result", json=STRAIGHT_WIN_A)  # B2 advances

    semifinal = _round(admin.get("/playoffs/bracket").json(), "semifinal")
    sf1 = _node(semifinal, 1)  # side b = quarterfinal-2 winner
    assert sf1["team_b"]["seed"] == "2B"


def test_bye_survivor_carries_its_own_seed(admin):
    zone_a = _make_zone(admin, ZONE_A, 10, "A")
    _make_zone(admin, ZONE_B, 9, "B")  # no position 10

    admin.post("/playoffs/generate", json={"force": True})
    bracket = admin.get("/playoffs/bracket").json()
    orphan = _node(_round(bracket, "round_1"), 1)  # (A,3) vs (B,10) — B10 does not exist

    assert orphan["status"] == "bye"
    assert orphan["team_a"]["seed"] == "3A"

    destination = _node(_round(bracket, "round_2"), 1)
    assert destination["team_a"]["seed"] == "3A"


def test_projection_labels_teams_from_live_standings(admin, full_league):
    bracket = admin.get("/playoffs/bracket").json()
    assert bracket["mode"] == "projection"

    node = _node(_round(bracket, "round_1"), 1)  # (A,3) vs (B,10)
    assert node["team_a"]["seed"] == "3A"
    assert node["team_b"]["seed"] == "10B"


def test_projection_seed_follows_the_standings_not_a_fixed_team(admin, full_league):
    zone_a, _ = full_league
    before = _node(_round(admin.get("/playoffs/bracket").json(), "round_1"), 1)
    assert before["team_a"]["seed"] == "3A"

    # zone_a[9] (currently seed 10, last by the tie-break) beats zone_a[2]
    # (currently seed 3): zone_a[9] jumps to seed 1, and seed 3 becomes
    # whoever was seed 2 before — a different physical team.
    match_id = make_match(admin, zone_a[9], zone_a[2])
    admin.post(f"/admin/matches/{match_id}/result", json=STRAIGHT_WIN_A)

    after = _node(_round(admin.get("/playoffs/bracket").json(), "round_1"), 1)
    assert after["team_a"]["seed"] == "3A"  # the label is still "3A"…
    assert after["team_a"]["id"] != before["team_a"]["id"]  # …but a different team now holds it
