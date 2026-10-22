"""Contract DTO tests; run with --noconftest (no app, engine or database)."""

import json
from uuid import UUID

import pytest
from pydantic import TypeAdapter, ValidationError

from app.americanos import schemas


CONFIRMATION_KEY = "e182cb1e-d179-4b1e-97d1-54cb12ac3977"
MAX_SAFE_ID = 9_007_199_254_740_991


def test_create_event_trims_name_and_serializes_the_contract():
    event = schemas.CreateEventRequest(
        name="  Amistad de octubre  ", zone_count=2, start_stage="semifinal"
    )

    assert event.model_dump(mode="json") == {
        "name": "Amistad de octubre",
        "zone_count": 2,
        "start_stage": "semifinal",
    }


REQUESTS = [
    ("RevisionRequest", {"expected_revision": 1}),
    ("GroupSourceRequest", {"expected_revision": 2, "source_groups_revision": 0}),
    ("CreateEventRequest", {"name": "Copa", "zone_count": 1, "start_stage": "final"}),
    ("UpdateEventRequest", {"expected_revision": 3, "zone_count": 2}),
    ("RegistrationRequest", {"expected_revision": 4, "player1_name": "Ana", "player2_name": "Ana"}),
    ("UpdateRegistrationRequest", {"expected_revision": 5, "player2_name": "Luz"}),
    ("SetZonesRequest", {"expected_revision": 6, "zone_count": 2, "zone_a_registration_ids": [1, 3]}),
    ("SaveRoundRequest", {"expected_revision": 7, "results": [
        {"match_id": 101, "games_a": 0, "games_b": 0},
        {"match_id": 102, "games_a": 9, "games_b": 1},
    ]}),
    ("SaveTieResolutionsRequest", {"expected_revision": 8, "source_groups_revision": 3, "resolutions": [
        {"zone_id": 10, "position": 1, "registration_id": 3},
        {"zone_id": 10, "position": 2, "registration_id": 1},
    ]}),
    ("ConfirmQualifiersRequest", {"expected_revision": 9, "source_groups_revision": 3,
                                  "confirmation_key": CONFIRMATION_KEY}),
    ("SaveKnockoutRequest", {"expected_revision": 10, "games_a": 12, "games_b": 10, "set_complete": True}),
]


@pytest.mark.parametrize("model_name,payload", REQUESTS)
def test_each_request_serializes_exact_contract_fields(model_name, payload):
    dto = getattr(schemas, model_name).model_validate(payload)
    assert dto.model_dump(mode="json", exclude_unset=True) == payload


@pytest.mark.parametrize("model_name,payload", REQUESTS)
def test_each_request_is_closed(model_name, payload):
    with pytest.raises(ValidationError) as error:
        getattr(schemas, model_name).model_validate({**payload, "unexpected": 1})
    assert error.value.errors()[0]["loc"] == ("unexpected",)


@pytest.mark.parametrize("bad", [True, False, 1.0, 1.5, "1", 0, -1, None])
def test_expected_revision_is_a_required_strict_positive_integer(bad):
    with pytest.raises(ValidationError):
        schemas.RevisionRequest(expected_revision=bad)


def test_expected_revision_cannot_be_omitted():
    with pytest.raises(ValidationError):
        schemas.RevisionRequest()


@pytest.mark.parametrize("bad", [True, False, 0.0, 0.5, "0", -1, None])
def test_source_revision_is_strict_and_nonnegative(bad):
    with pytest.raises(ValidationError):
        schemas.GroupSourceRequest(expected_revision=1, source_groups_revision=bad)


@pytest.mark.parametrize("revision", [0, 11])
def test_source_revision_preserves_zero_and_later_revisions(revision):
    dto = schemas.GroupSourceRequest(expected_revision=12, source_groups_revision=revision)
    assert dto.model_dump() == {"expected_revision": 12, "source_groups_revision": revision}


@pytest.mark.parametrize("bad", ["", " \t\n", None, 8])
def test_event_names_reject_blank_null_and_nonstring(bad):
    with pytest.raises(ValidationError):
        schemas.CreateEventRequest(name=bad, zone_count=1, start_stage="final")


@pytest.mark.parametrize("bad", [True, False, 1.0, "2", 0, 3, None])
def test_zone_count_is_exactly_one_or_two_strict_integers(bad):
    with pytest.raises(ValidationError):
        schemas.CreateEventRequest(name="Copa", zone_count=bad, start_stage="final")


@pytest.mark.parametrize("stage", ["quarterfinal", "semifinal", "final"])
def test_all_three_g0_stage_values_are_preserved(stage):
    dto = schemas.CreateEventRequest(name="Copa", zone_count=1, start_stage=stage)
    assert dto.model_dump()["start_stage"] == stage


@pytest.mark.parametrize("bad", ["quarters", "semi", "semifinals", "cuartos", "", None, 1])
def test_stage_aliases_and_invalid_types_are_rejected(bad):
    with pytest.raises(ValidationError):
        schemas.CreateEventRequest(name="Copa", zone_count=1, start_stage=bad)


@pytest.mark.parametrize("model_name,changes,expected", [
    ("UpdateEventRequest", {"name": "  Nueva copa  "}, {"name": "Nueva copa"}),
    ("UpdateEventRequest", {"start_stage": "quarterfinal", "zone_count": 1},
     {"start_stage": "quarterfinal", "zone_count": 1}),
    ("UpdateRegistrationRequest", {"player1_name": "  José  "}, {"player1_name": "José"}),
    ("UpdateRegistrationRequest", {"player1_name": "Ana", "player2_name": "Ana"},
     {"player1_name": "Ana", "player2_name": "Ana"}),
])
def test_patch_fields_can_be_omitted_and_names_are_trimmed(model_name, changes, expected):
    dto = getattr(schemas, model_name)(expected_revision=1, **changes)
    assert dto.model_dump(exclude_unset=True) == {"expected_revision": 1, **expected}


@pytest.mark.parametrize("model_name,field", [
    ("UpdateEventRequest", "name"), ("UpdateEventRequest", "zone_count"),
    ("UpdateEventRequest", "start_stage"), ("UpdateRegistrationRequest", "player1_name"),
    ("UpdateRegistrationRequest", "player2_name"),
])
def test_patch_requires_a_change_and_rejects_explicit_null(model_name, field):
    model = getattr(schemas, model_name)
    with pytest.raises(ValidationError):
        model(expected_revision=1)
    with pytest.raises(ValidationError):
        model(expected_revision=1, **{field: None})


@pytest.mark.parametrize("field", ["player1_name", "player2_name"])
@pytest.mark.parametrize("bad", ["", " \t", None, True])
def test_registration_names_are_required_trimmed_nonempty_strings(field, bad):
    payload = {"expected_revision": 1, "player1_name": "Ana", "player2_name": "Luz"}
    payload[field] = bad
    with pytest.raises(ValidationError):
        schemas.RegistrationRequest(**payload)
    del payload[field]
    with pytest.raises(ValidationError):
        schemas.RegistrationRequest(**payload)


def test_registration_trims_both_names_without_nominal_uniqueness():
    dto = schemas.RegistrationRequest(expected_revision=1, player1_name=" Ana ", player2_name=" Ana ")
    assert dto.model_dump() == {"expected_revision": 1, "player1_name": "Ana", "player2_name": "Ana"}


@pytest.mark.parametrize("ids", [[], [2, 4, MAX_SAFE_ID]])
def test_zone_selection_preserves_manual_selection_without_assuming_membership(ids):
    dto = schemas.SetZonesRequest(expected_revision=1, zone_count=2, zone_a_registration_ids=ids)
    assert dto.model_dump()["zone_a_registration_ids"] == ids


@pytest.mark.parametrize("ids", [[1, 1], [True], [1.0], ["1"], [0], [-1], [MAX_SAFE_ID + 1]])
def test_zone_selection_rejects_duplicate_or_invalid_ids(ids):
    with pytest.raises(ValidationError):
        schemas.SetZonesRequest(expected_revision=1, zone_count=2, zone_a_registration_ids=ids)


@pytest.mark.parametrize("games_a,games_b", [(0, 0), (9, 0), (3, 8)])
def test_group_results_preserve_complete_scores_including_zero(games_a, games_b):
    payload = {"expected_revision": 1, "results": [{"match_id": 101, "games_a": games_a, "games_b": games_b}]}
    assert schemas.SaveRoundRequest(**payload).model_dump() == payload


@pytest.mark.parametrize("field", ["games_a", "games_b"])
@pytest.mark.parametrize("bad", [None, "", True, False, 0.0, 1.5, "0", -1, 10])
def test_group_result_rejects_invalid_or_missing_score(field, bad):
    result = {"match_id": 101, "games_a": 0, "games_b": 0, field: bad}
    with pytest.raises(ValidationError):
        schemas.SaveRoundRequest(expected_revision=1, results=[result])
    del result[field]
    with pytest.raises(ValidationError):
        schemas.SaveRoundRequest(expected_revision=1, results=[result])


@pytest.mark.parametrize("match_id", [True, 1.0, "1", 0, -1, MAX_SAFE_ID + 1])
def test_group_match_ids_are_strict_safe_positive_integers(match_id):
    with pytest.raises(ValidationError):
        schemas.SaveRoundRequest(expected_revision=1, results=[{"match_id": match_id, "games_a": 0, "games_b": 0}])


def test_round_rejects_duplicate_ids_and_nested_extra_fields():
    result = {"match_id": 101, "games_a": 0, "games_b": 0}
    with pytest.raises(ValidationError):
        schemas.SaveRoundRequest(expected_revision=1, results=[result, result])
    with pytest.raises(ValidationError):
        schemas.SaveRoundRequest(expected_revision=1, results=[{**result, "winner_id": 1}])


def test_round_dto_leaves_exact_fixture_set_validation_to_service():
    # A DTO has no knowledge of stored matches; neither invent IDs nor reject an empty list here.
    assert schemas.SaveRoundRequest(expected_revision=1, results=[]).model_dump() == {
        "expected_revision": 1, "results": [],
    }


@pytest.mark.parametrize("resolutions", [[], [
    {"zone_id": 10, "position": 1, "registration_id": 5},
    {"zone_id": 20, "position": 1, "registration_id": 8},
]])
def test_tie_resolution_uses_real_ids_and_zone_scoped_slots(resolutions):
    payload = {"expected_revision": 2, "source_groups_revision": 0, "resolutions": resolutions}
    assert schemas.SaveTieResolutionsRequest(**payload).model_dump() == payload


@pytest.mark.parametrize("second", [
    {"zone_id": 10, "position": 1, "registration_id": 8},
    {"zone_id": 10, "position": 2, "registration_id": 5},
    {"zone_id": 20, "position": 1, "registration_id": 5},
])
def test_resolution_rejects_repeated_slot_or_registration(second):
    with pytest.raises(ValidationError):
        schemas.SaveTieResolutionsRequest(expected_revision=1, source_groups_revision=0, resolutions=[
            {"zone_id": 10, "position": 1, "registration_id": 5}, second,
        ])


@pytest.mark.parametrize("field", ["zone_id", "position", "registration_id"])
@pytest.mark.parametrize("bad", [True, 1.0, "1", 0, None])
def test_resolution_identifiers_and_positions_are_strict_positive(field, bad):
    resolution = {"zone_id": 10, "position": 1, "registration_id": 5, field: bad}
    with pytest.raises(ValidationError):
        schemas.SaveTieResolutionsRequest(expected_revision=1, source_groups_revision=0, resolutions=[resolution])


@pytest.mark.parametrize("key", [CONFIRMATION_KEY, "00000000-0000-0000-0000-000000000000"])
def test_confirmation_key_is_a_uuid_string_without_imposing_uuid_version(key):
    payload = {"expected_revision": 1, "source_groups_revision": 0, "confirmation_key": key}
    assert schemas.ConfirmQualifiersRequest(**payload).model_dump(mode="json") == payload


@pytest.mark.parametrize("canonical_key", [
    CONFIRMATION_KEY,
    "9d0b7c2f-32a6-4d89-a1eb-b306e8d6425a",
    "00000000-0000-0000-0000-000000000000",
])
@pytest.mark.parametrize("representation", ["canonical", "uppercase", "braced", "urn", "hex"])
def test_confirmation_key_is_canonical_in_the_dto_and_serialized_output(canonical_key, representation):
    key = {
        "canonical": canonical_key,
        "uppercase": canonical_key.upper(),
        "braced": "{" + canonical_key + "}",
        "urn": "urn:uuid:" + canonical_key,
        "hex": canonical_key.replace("-", ""),
    }[representation]
    dto = schemas.ConfirmQualifiersRequest(
        expected_revision=1, source_groups_revision=0, confirmation_key=key
    )

    assert dto.confirmation_key == canonical_key
    assert dto.model_dump()["confirmation_key"] == canonical_key
    assert dto.model_dump(mode="json")["confirmation_key"] == canonical_key
    assert json.loads(dto.model_dump_json())["confirmation_key"] == canonical_key


@pytest.mark.parametrize("other_key", [
    "9d0b7c2f-32a6-4d89-a1eb-b306e8d6425a",
    "00000000-0000-0000-0000-000000000000",
])
def test_confirmation_key_canonicalization_keeps_distinct_uuids_distinct(other_key):
    first = schemas.ConfirmQualifiersRequest(
        expected_revision=1, source_groups_revision=0, confirmation_key=CONFIRMATION_KEY.upper()
    )
    second = schemas.ConfirmQualifiersRequest(
        expected_revision=1, source_groups_revision=0, confirmation_key="urn:uuid:" + other_key
    )

    assert first.confirmation_key == CONFIRMATION_KEY
    assert second.confirmation_key == other_key
    assert first.confirmation_key != second.confirmation_key


@pytest.mark.parametrize("bad", ["", "not-a-uuid", "e182cb1e-d179-4b1e-97d1", None, True, UUID(CONFIRMATION_KEY)])
def test_confirmation_key_rejects_invalid_uuid_or_nonstring(bad):
    with pytest.raises(ValidationError):
        schemas.ConfirmQualifiersRequest(expected_revision=1, source_groups_revision=0, confirmation_key=bad)


@pytest.mark.parametrize("games_a,games_b", [(6, 0), (0, 6), (12, 10), (5, 3)])
def test_knockout_only_validates_transport_not_unapproved_terminal_rules(games_a, games_b):
    payload = {"expected_revision": 1, "games_a": games_a, "games_b": games_b, "set_complete": True}
    assert schemas.SaveKnockoutRequest(**payload).model_dump() == payload


@pytest.mark.parametrize("field", ["games_a", "games_b"])
@pytest.mark.parametrize("bad", [None, "", True, False, 6.0, 6.5, "6", -1])
def test_knockout_games_reject_incomplete_or_nonstrict_values(field, bad):
    payload = {"expected_revision": 1, "games_a": 6, "games_b": 4, "set_complete": True, field: bad}
    with pytest.raises(ValidationError):
        schemas.SaveKnockoutRequest(**payload)
    del payload[field]
    with pytest.raises(ValidationError):
        schemas.SaveKnockoutRequest(**payload)


@pytest.mark.parametrize("bad", [False, 1, 1.0, "true", None])
def test_knockout_requires_literal_boolean_true(bad):
    with pytest.raises(ValidationError):
        schemas.SaveKnockoutRequest(expected_revision=1, games_a=6, games_b=4, set_complete=bad)


@pytest.mark.parametrize("score", [0, 6])
def test_knockout_rejects_ties(score):
    with pytest.raises(ValidationError):
        schemas.SaveKnockoutRequest(expected_revision=1, games_a=score, games_b=score, set_complete=True)


def registration(registration_id=1):
    return {"id": registration_id, "zone_id": 10, "player1_name": "Ana", "player2_name": "Luz",
            "registration_order": registration_id}


def event_detail():
    return {
        "id": 100, "name": "Copa", "state": "review", "zone_count": 1, "start_stage": "semifinal",
        "revision": 8, "groups_revision": 3, "registration_count": 4, "total_rounds": 3,
        "saved_rounds": 3, "max_unlocked_round": 3, "continuation": {"kind": "qualification"},
        "zones": [{"id": 10, "label": "A"}], "registrations": [registration(i) for i in range(1, 5)],
        "quotas": [{"zone_id": 10, "required": 4, "registered": 4, "sufficient": True}],
        "can_generate": False, "configuration_issues": [], "confirmed_at": None,
        "champion_registration_id": None,
    }


def group_match():
    return {"id": 101, "zone_id": 10, "display_order": 1, "registration_a": registration(1),
            "registration_b": registration(2), "games_a": None, "games_b": None}


def round_response():
    return {"event_id": 100, "event_name": "Copa", "state": "groups", "revision": 8,
            "groups_revision": 2, "number": 3, "total_rounds": 3, "max_unlocked_round": 3,
            "saved": False, "locked": False, "read_only": False, "zones": [{"id": 10, "label": "A"}],
            "matches": [group_match()], "resting": [{"registration": registration(3), "reason": "capacity"}]}


def standing_row(registration_id=1):
    return {"registration": registration(registration_id), "played": 3, "won": 0, "drawn": 3, "lost": 0,
            "games_for": 0, "games_against": 0, "games_diff": 0, "points_half_units": 3}


def zone_standings():
    return {"zone": {"id": 10, "label": "A"}, "blocks": [{"position_from": 1, "position_to": 4,
            "points_half_units": 3, "games_diff": 0, "rows": [standing_row(i) for i in range(1, 5)]}]}


def standings_response():
    return {"event_id": 100, "state": "review", "revision": 8, "groups_revision": 3,
            "frozen": False, "zones": [zone_standings()]}


def qualification_response():
    def seed(position):
        return {"zone_id": 10, "position": position}

    def seed_source(position):
        return {"kind": "seed", **seed(position)}

    return {
        "event_id": 100, "state": "review", "revision": 8, "source_groups_revision": 3,
        "standings": [zone_standings()], "quotas": event_detail()["quotas"],
        "slots": [{**seed(i), "candidate_registration_ids": [1, 2, 3, 4], "registration_id": None,
                   "requires_resolution": True} for i in range(1, 5)],
        "missing_slots": [seed(i) for i in range(1, 5)], "resolved_seeds": [],
        "seeding_template": {"key": "semifinal-one-zone-v1", "status": "approved", "start_stage": "semifinal",
                             "zone_count": 1, "opening_pairs": [{"a": seed(1), "b": seed(4)},
                                                                 {"a": seed(2), "b": seed(3)}]},
        "bracket": [
            {"stage": "semifinal", "slot": 1, "source_a": seed_source(1), "source_b": seed_source(4),
             "registration_a_id": None, "registration_b_id": None, "next": {"stage": "final", "slot": 1, "side": "a"}},
            {"stage": "semifinal", "slot": 2, "source_a": seed_source(2), "source_b": seed_source(3),
             "registration_a_id": None, "registration_b_id": None, "next": {"stage": "final", "slot": 1, "side": "b"}},
            {"stage": "final", "slot": 1, "source_a": {"kind": "winner", "stage": "semifinal", "slot": 1},
             "source_b": {"kind": "winner", "stage": "semifinal", "slot": 2},
             "registration_a_id": None, "registration_b_id": None, "next": None},
        ],
        "blockers": [{"code": "unresolved_ties", "message": "Seleccioná las cuatro plazas."}],
        "can_confirm": False, "frozen": False,
    }


def knockout_node():
    return {"id": 201, "stage": "semifinal", "slot": 1, "registration_a": registration(1),
            "registration_b": registration(4), "games_a": None, "games_b": None, "set_complete": False,
            "next_match_id": 203, "next_side": "a", "winner_registration_id": None,
            "can_edit": False, "edit_block_reason": "rules_pending_approval"}


def playoffs_response():
    second = {**knockout_node(), "id": 202, "slot": 2, "registration_a": registration(2),
              "registration_b": registration(3), "next_side": "b"}
    final = {**knockout_node(), "id": 203, "stage": "final", "registration_a": None, "registration_b": None,
             "next_match_id": None, "next_side": None, "edit_block_reason": "participants_pending"}
    return {"event_id": 100, "event_name": "Copa", "state": "playoffs", "revision": 9, "groups_revision": 3,
            "start_stage": "semifinal", "zones": [{"id": 10, "label": "A"}],
            "snapshots": [{"zone_id": 10, "position": i, "registration_id": i, "player1_name": "Ana",
                           "player2_name": "Luz", "points_half_units": 3, "games_diff": 0,
                           "source_groups_revision": 3} for i in range(1, 5)],
            "nodes": [knockout_node(), second, final], "champion": None}


def confirmation_response():
    event = {**event_detail(), "state": "playoffs", "revision": 9, "continuation": {"kind": "playoffs"},
             "confirmed_at": "2026-10-20T12:00:00Z"}
    return {"event": event, "confirmation_key": CONFIRMATION_KEY, "confirmed_source_revision": 3,
            "confirmed_at": "2026-10-20T12:00:00Z", "playoffs": playoffs_response()}


@pytest.mark.parametrize("key,canonical_key", [
    ("{" + CONFIRMATION_KEY + "}", CONFIRMATION_KEY),
    ("urn:uuid:9d0b7c2f-32a6-4d89-a1eb-b306e8d6425a", "9d0b7c2f-32a6-4d89-a1eb-b306e8d6425a"),
])
def test_confirmation_response_serializes_the_canonical_key(key, canonical_key):
    payload = {**confirmation_response(), "confirmation_key": key}
    dto = schemas.ConfirmationResponse.model_validate(payload)

    assert dto.confirmation_key == canonical_key
    assert dto.model_dump(mode="json") == {**payload, "confirmation_key": canonical_key}
    assert json.loads(dto.model_dump_json()) == {**payload, "confirmation_key": canonical_key}


RESPONSE_FACTORIES = [
    ("EventDetail", event_detail), ("RoundResponse", round_response),
    ("StandingsResponse", standings_response), ("QualificationResponse", qualification_response),
    ("PlayoffsResponse", playoffs_response), ("ConfirmationResponse", confirmation_response),
    ("GenerateFixtureResponse", lambda: {"event": event_detail(), "first_round": round_response()}),
    ("SaveRoundResponse", lambda: {"round": {**round_response(), "state": "review", "groups_revision": 3,
                                            "saved": True, "matches": [{**group_match(), "games_a": 0, "games_b": 0}]},
                                    "standings": standings_response()}),
    ("GroupMatch", group_match), ("KnockoutNode", knockout_node),
    ("StandingRow", standing_row), ("ZoneStandings", zone_standings),
]


@pytest.mark.parametrize("model_name,factory", RESPONSE_FACTORIES)
def test_responses_serialize_meaningful_nested_payloads_exactly(model_name, factory):
    payload = factory()
    model = getattr(schemas, model_name)
    assert model.model_validate(payload).model_dump(mode="json") == payload
    assert model.model_validate_json(json.dumps(payload)).model_dump(mode="json") == payload


@pytest.mark.parametrize("model_name,factory", RESPONSE_FACTORIES)
def test_response_fields_are_closed_and_declared_fields_cannot_be_omitted(model_name, factory):
    payload = factory()
    model = getattr(schemas, model_name)
    with pytest.raises(ValidationError):
        model.model_validate({**payload, "league_id": 3})
    for field in payload:
        missing_field = {key: value for key, value in payload.items() if key != field}
        with pytest.raises(ValidationError):
            model.model_validate(missing_field)


def test_summary_list_is_a_bare_array_and_empty_draft_is_valid():
    draft = {**event_detail(), "state": "draft", "groups_revision": 0, "registration_count": 0,
             "total_rounds": 0, "saved_rounds": 0, "max_unlocked_round": 0, "continuation": {"kind": "setup"},
             "registrations": [], "quotas": [{"zone_id": 10, "required": 4, "registered": 0, "sufficient": False}],
             "configuration_issues": [{"code": "insufficient_registrations", "zone_id": 10,
                                       "registration_ids": [], "message": "Se necesitan cuatro parejas."}]}
    assert schemas.EventDetail(**draft).model_dump(mode="json") == draft
    summary = {key: draft[key] for key in ["id", "name", "state", "zone_count", "start_stage", "revision",
               "groups_revision", "registration_count", "total_rounds", "saved_rounds", "max_unlocked_round", "continuation"]}
    adapter = TypeAdapter(schemas.ListEventsResponse)
    assert adapter.dump_python(adapter.validate_python([summary]), mode="json") == [summary]
    assert adapter.validate_python([]) == []


@pytest.mark.parametrize("continuation", [{"kind": "setup"}, {"kind": "round", "round_number": 2},
                                         {"kind": "qualification"}, {"kind": "playoffs"}])
def test_continuation_is_a_closed_discriminated_union(continuation):
    dto = schemas.EventDetail(**{**event_detail(), "continuation": continuation})
    assert dto.model_dump()["continuation"] == continuation


@pytest.mark.parametrize("continuation", [{"kind": "round"}, {"kind": "round", "round_number": 0},
    {"kind": "round", "round_number": True}, {"kind": "round", "round_number": "1"},
    {"kind": "setup", "round_number": 1}, {"kind": "unknown"}, {"kind": "playoffs", "url": "/secret"}])
def test_invalid_continuation_shapes_are_rejected(continuation):
    with pytest.raises(ValidationError):
        schemas.EventDetail(**{**event_detail(), "continuation": continuation})


@pytest.mark.parametrize("games_a,games_b", [(None, None), (0, 0), (9, 2)])
def test_group_read_distinguishes_explicit_pending_and_complete_zero(games_a, games_b):
    payload = {**group_match(), "games_a": games_a, "games_b": games_b}
    assert schemas.GroupMatch(**payload).model_dump(mode="json") == payload


@pytest.mark.parametrize("games_a,games_b", [(None, 0), (0, None), (True, 0), (0.0, 0), ("0", 0), (10, 0)])
def test_group_read_rejects_partial_or_nonstrict_scores(games_a, games_b):
    with pytest.raises(ValidationError):
        schemas.GroupMatch(**{**group_match(), "games_a": games_a, "games_b": games_b})


@pytest.mark.parametrize("other_id", [1, 0])
def test_group_read_requires_canonical_distinct_registration_ids(other_id):
    with pytest.raises(ValidationError):
        schemas.GroupMatch(**{**group_match(), "registration_b": registration(other_id)})


@pytest.mark.parametrize("reason", ["bye", "capacity", "zone_finished"])
def test_all_rest_reasons_serialize_without_losing_registration(reason):
    payload = {"registration": registration(3), "reason": reason}
    assert schemas.RestingRegistration(**payload).model_dump() == payload


@pytest.mark.parametrize("bad", [True, 3.0, 1.5, "3", -1])
def test_standings_half_units_are_strict_nonnegative_integers(bad):
    with pytest.raises(ValidationError):
        schemas.StandingRow(**{**standing_row(), "points_half_units": bad})


def test_standing_blocks_preserve_ties_and_signed_games_difference():
    payload = {"position_from": 3, "position_to": 4, "points_half_units": 0, "games_diff": -2,
               "rows": [{**standing_row(i), "played": 1, "drawn": 0, "lost": 1, "games_against": 2,
                         "games_diff": -2, "points_half_units": 0} for i in [3, 4]]}
    assert schemas.StandingBlock(**payload).model_dump() == payload
    singleton = {"position_from": 1, "position_to": 1, "points_half_units": 3, "games_diff": 0,
                 "rows": [standing_row()]}
    assert schemas.StandingBlock(**singleton).model_dump() == singleton


@pytest.mark.parametrize("changes", [{"position_to": 3}, {"position_from": 5}, {"points_half_units": 2},
                                     {"games_diff": 1}])
def test_standing_block_range_and_shared_metrics_are_coherent(changes):
    payload = {**zone_standings()["blocks"][0], **changes}
    with pytest.raises(ValidationError):
        schemas.StandingBlock(**payload)


def test_zero_round_fixture_response_has_null_first_round():
    event = {**event_detail(), "start_stage": "final", "zone_count": 2, "total_rounds": 0,
             "saved_rounds": 0, "max_unlocked_round": 0, "groups_revision": 0}
    payload = {"event": event, "first_round": None}
    assert schemas.GenerateFixtureResponse(**payload).model_dump() == payload


def test_resolved_qualification_keeps_the_full_candidate_block():
    payload = qualification_response()
    for slot, chosen in zip(payload["slots"], [2, 1, 4, 3], strict=True):
        slot["registration_id"] = chosen
    payload["resolved_seeds"] = [{"zone_id": 10, "position": i, "registration_id": chosen}
                                 for i, chosen in enumerate([2, 1, 4, 3], 1)]
    payload.update(missing_slots=[], blockers=[], can_confirm=True)
    assert schemas.QualificationResponse(**payload).model_dump() == payload


@pytest.mark.parametrize("source", [{"kind": "seed", "zone_id": 10, "position": 1},
                                    {"kind": "winner", "stage": "semifinal", "slot": 2}])
def test_bracket_sources_preserve_their_distinct_shapes(source):
    adapter = TypeAdapter(schemas.BracketSource)
    assert adapter.dump_python(adapter.validate_python(source)) == source


@pytest.mark.parametrize("source", [{"kind": "seed", "zone_id": 10, "position": 1, "stage": "final"},
    {"kind": "winner", "stage": "semi", "slot": 1}, {"kind": "winner", "stage": "semifinal", "slot": 0},
    {"kind": "winner", "zone_id": 10, "position": 1}, {"kind": "unknown"}])
def test_invalid_bracket_sources_are_rejected(source):
    with pytest.raises(ValidationError):
        TypeAdapter(schemas.BracketSource).validate_python(source)


@pytest.mark.parametrize("games_a,games_b,complete", [(None, None, False), (0, 6, True), (12, 10, True)])
def test_knockout_read_pending_and_complete_transport_shapes(games_a, games_b, complete):
    payload = {**knockout_node(), "games_a": games_a, "games_b": games_b, "set_complete": complete}
    if complete:
        payload["winner_registration_id"] = 1 if games_a > games_b else 4
    assert schemas.KnockoutNode(**payload).model_dump() == payload


@pytest.mark.parametrize("changes", [
    {"games_a": 0}, {"games_b": 0}, {"set_complete": True},
    {"games_a": 6, "games_b": 4}, {"games_a": 6, "games_b": 6, "set_complete": True},
    {"games_a": True, "games_b": 0, "set_complete": True}, {"set_complete": 0},
    {"next_match_id": None}, {"next_side": None}, {"stage": "final"},
])
def test_knockout_read_rejects_partial_scores_flags_and_destinations(changes):
    with pytest.raises(ValidationError):
        schemas.KnockoutNode(**{**knockout_node(), **changes})


def test_completed_playoffs_and_confirmation_replay_serialize_current_champion():
    payload = confirmation_response()
    payload["event"].update(state="completed", revision=12, champion_registration_id=1)
    payload["playoffs"].update(state="completed", revision=12, champion=registration(1))
    final = payload["playoffs"]["nodes"][-1]
    final.update(registration_a=registration(1), registration_b=registration(2), games_a=12, games_b=10,
                 set_complete=True, winner_registration_id=1, edit_block_reason=None)
    assert schemas.ConfirmationResponse(**payload).model_dump(mode="json") == payload


@pytest.mark.parametrize("state", ["draft", "groups", "review", "finished"])
def test_playoffs_state_is_only_playoffs_or_completed(state):
    with pytest.raises(ValidationError):
        schemas.PlayoffsResponse(**{**playoffs_response(), "state": state})


@pytest.mark.parametrize("bad", ["2026-10-20", "2026-02-30T12:00:00Z", "2026-10-20T12:00:00",
                                 "2026-10-20T12:00:00-03:00", None, 123])
def test_confirmation_timestamps_require_valid_utc_rfc3339_strings(bad):
    with pytest.raises(ValidationError):
        schemas.ConfirmationResponse(**{**confirmation_response(), "confirmed_at": bad})


def test_structured_error_preserves_flat_body_and_indexed_field_paths():
    payload = {"detail": "Revisión obsoleta.", "message": "Revisión obsoleta.", "code": "revision_conflict",
               "current_revision": 9, "fields": [{"path": ["results", 2, "games_b"], "code": "stale",
                                                  "message": "Volvé a cargar."}]}
    assert schemas.AmericanoErrorBody(**payload).model_dump(mode="json") == payload


def test_structured_error_omits_optional_metadata_instead_of_serializing_null():
    payload = {"detail": "No existe.", "message": "No existe.", "code": "not_found"}
    assert schemas.AmericanoErrorBody(**payload).model_dump(mode="json") == payload


@pytest.mark.parametrize("changes", [{"code": "unauthorized"}, {"message": "Otra cosa."},
    {"current_revision": True}, {"current_revision": None}, {"fields": None},
    {"fields": [{"path": ["results", True], "code": "bad", "message": "No."}]}])
def test_structured_errors_reject_unknown_codes_inconsistent_detail_and_invalid_metadata(changes):
    with pytest.raises(ValidationError):
        schemas.AmericanoErrorBody(**{"detail": "No.", "message": "No.", "code": "validation_error", **changes})


@pytest.mark.parametrize("model_name,payload", REQUESTS)
def test_required_request_fields_cannot_be_omitted(model_name, payload):
    for field in payload:
        with pytest.raises(ValidationError):
            getattr(schemas, model_name).model_validate({key: value for key, value in payload.items() if key != field})


@pytest.mark.parametrize("bad", [True, 0.0, "0", -1, None])
@pytest.mark.parametrize("field", ["played", "won", "drawn", "lost", "games_for", "games_against"])
def test_standing_counts_are_strict_nonnegative_integers(field, bad):
    with pytest.raises(ValidationError):
        schemas.StandingRow(**{**standing_row(), field: bad})


@pytest.mark.parametrize("bad", [True, 0.0, "0", None])
def test_games_difference_is_a_strict_signed_integer(bad):
    with pytest.raises(ValidationError):
        schemas.StandingRow(**{**standing_row(), "games_diff": bad})


@pytest.mark.parametrize("field", ["state", "start_stage", "revision", "groups_revision", "registration_count",
                                 "total_rounds", "saved_rounds", "max_unlocked_round"])
def test_event_read_rejects_invalid_enum_or_nonstrict_counters(field):
    with pytest.raises(ValidationError):
        schemas.EventDetail(**{**event_detail(), field: True})


def test_unassigned_registration_is_explicitly_null_and_identity_is_not_a_league_team():
    payload = {**registration(), "zone_id": None}
    assert schemas.Registration(**payload).model_dump() == payload
    with pytest.raises(ValidationError):
        schemas.Registration(**{key: value for key, value in payload.items() if key != "zone_id"})
    with pytest.raises(ValidationError):
        schemas.Registration(**{**payload, "team_id": 55})


@pytest.mark.parametrize("path,value", [
    (("registrations", 0, "team_name"), "Alias"),
    (("zones", 0, "event_id"), 100),
    (("quotas", 0, "sufficient"), 1),
    (("registrations", 0, "registration_order"), 0),
])
def test_nested_event_contracts_reject_aliases_extras_and_invalid_scalar_values(path, value):
    payload = event_detail()
    payload[path[0]][path[1]][path[2]] = value
    with pytest.raises(ValidationError):
        schemas.EventDetail(**payload)


@pytest.mark.parametrize("label", ["B", "A"])
def test_zone_labels_are_exact(label):
    assert schemas.Zone(id=10, label=label).model_dump() == {"id": 10, "label": label}


@pytest.mark.parametrize("label", ["a", "Zona A", "C", 1])
def test_zone_labels_reject_aliases(label):
    with pytest.raises(ValidationError):
        schemas.Zone(id=10, label=label)


@pytest.mark.parametrize("status", ["approved", "proposed"])
def test_seeding_status_is_preserved_without_implicitly_approving_proposals(status):
    payload = {**qualification_response()["seeding_template"], "status": status}
    assert schemas.SeedingTemplate(**payload).model_dump() == payload


@pytest.mark.parametrize("code", ["groups_incomplete", "configuration_invalid", "unresolved_ties", "seeding_pending_approval"])
def test_each_qualification_blocker_code_preserves_its_message(code):
    payload = {"code": code, "message": "Revisá el evento."}
    assert schemas.QualificationBlocker(**payload).model_dump() == payload


@pytest.mark.parametrize("reason", ["participants_pending", "rules_pending_approval", "descendant_played", None])
def test_knockout_edit_block_reasons_are_preserved(reason):
    payload = {**knockout_node(), "edit_block_reason": reason}
    assert schemas.KnockoutNode(**payload).model_dump() == payload


@pytest.mark.parametrize("field,bad", [("points_half_units", 1.5), ("source_groups_revision", -1),
                                      ("position", 0), ("registration_id", True)])
def test_snapshot_rejects_invalid_metrics_revision_and_identifiers(field, bad):
    snapshot = playoffs_response()["snapshots"][0]
    with pytest.raises(ValidationError):
        schemas.QualifierSnapshot(**{**snapshot, field: bad})


@pytest.mark.parametrize("timestamp", ["2026-10-20T12:00:00Z", "2026-10-20T12:00:00.123+00:00"])
def test_confirmation_preserves_valid_utc_timestamp_strings(timestamp):
    payload = {**confirmation_response(), "confirmed_at": timestamp}
    assert schemas.ConfirmationResponse(**payload).model_dump(mode="json") == payload


@pytest.mark.parametrize("code", ["validation_error", "invalid_configuration", "invalid_reference", "invalid_round_results",
    "invalid_tie_resolution", "invalid_set", "not_found", "revision_conflict", "groups_revision_conflict",
    "state_conflict", "round_locked", "already_confirmed", "descendant_played", "participants_pending", "decision_pending"])
def test_all_g0_error_codes_are_preserved(code):
    payload = {"detail": "Error.", "message": "Error.", "code": code, "current_revision": 1, "fields": []}
    assert schemas.AmericanoErrorBody(**payload).model_dump(mode="json") == payload


def test_error_body_and_nested_fields_are_closed():
    with pytest.raises(ValidationError):
        schemas.AmericanoErrorBody(detail="No.", message="No.", code="not_found", event_id=100)
    with pytest.raises(ValidationError):
        schemas.AmericanoFieldError(path=["games_a"], code="bad", message="No.", input=7)
