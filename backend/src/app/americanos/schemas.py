"""Closed transport DTOs for the Americano shared contract v2.0.0.

Transport shapes are unchanged by the v2.0.0 frontend component contract delta.

No persistence/domain imports: event membership, complete stored match/seed sets,
state transitions and approved terminal set rules belong to the service layer.
Sparse PATCH payloads should be read with ``model_dump(exclude_unset=True)``.
"""

from collections.abc import Hashable, Sequence
from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    StringConstraints,
    model_serializer,
    model_validator,
)


StartStage = Literal["quarterfinal", "semifinal", "final"]
EventState = Literal["draft", "groups", "review", "playoffs", "completed"]
ZoneLabel = Literal["A", "B"]
Side = Literal["a", "b"]
DecisionStatus = Literal["approved", "proposed"]
ZoneCount = Annotated[int, Field(strict=True, ge=1, le=2)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
PositiveInt = Annotated[int, Field(strict=True, ge=1)]
NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
AmericanoId = Annotated[int, Field(strict=True, ge=1, le=9_007_199_254_740_991)]
GroupGames = Annotated[int, Field(strict=True, ge=0, le=9)]
StrictInt = Annotated[int, Field(strict=True)]


def _uuid_string(value: str) -> str:
    return str(UUID(value))


def _literal_true(value: object) -> object:
    if value is not True:
        raise ValueError("set_complete must be the boolean true")
    return value


ConfirmationKey = Annotated[str, AfterValidator(_uuid_string)]
CompleteSet = Annotated[Literal[True], BeforeValidator(_literal_true)]


def _utc_timestamp(value: str) -> str:
    datetime.fromisoformat(value)
    return value


UtcTimestamp = Annotated[
    str,
    StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|\+00:00)$"),
    AfterValidator(_utc_timestamp),
]


def _unique(values: Sequence[Hashable], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"Duplicate {label}")


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class RevisionRequest(ContractModel):
    expected_revision: PositiveInt


class GroupSourceRequest(RevisionRequest):
    source_groups_revision: NonNegativeInt


class CreateEventRequest(ContractModel):
    name: Name
    zone_count: ZoneCount
    start_stage: StartStage


class _PatchRequest(RevisionRequest):
    @model_validator(mode="after")
    def require_nonnull_change(self) -> Self:
        changes = self.model_fields_set - {"expected_revision"}
        if not changes or any(getattr(self, field) is None for field in changes):
            raise ValueError("At least one non-null changed field is required")
        return self


class UpdateEventRequest(_PatchRequest):
    name: Name | None = None
    zone_count: ZoneCount | None = None
    start_stage: StartStage | None = None


class RegistrationRequest(RevisionRequest):
    player1_name: Name
    player2_name: Name


class UpdateRegistrationRequest(_PatchRequest):
    player1_name: Name | None = None
    player2_name: Name | None = None


class SetZonesRequest(RevisionRequest):
    zone_count: ZoneCount
    zone_a_registration_ids: list[AmericanoId]

    @model_validator(mode="after")
    def unique_selection(self) -> Self:
        _unique(self.zone_a_registration_ids, "registration IDs")
        return self


class GroupResult(ContractModel):
    match_id: AmericanoId
    games_a: GroupGames
    games_b: GroupGames


class SaveRoundRequest(RevisionRequest):
    results: list[GroupResult]

    @model_validator(mode="after")
    def unique_matches(self) -> Self:
        # Exact membership/completeness requires the service's persisted round.
        _unique([result.match_id for result in self.results], "match IDs")
        return self


class SeedRef(ContractModel):
    zone_id: AmericanoId
    position: PositiveInt


class TieResolution(SeedRef):
    registration_id: AmericanoId


class SaveTieResolutionsRequest(GroupSourceRequest):
    resolutions: list[TieResolution]

    @model_validator(mode="after")
    def unique_resolutions(self) -> Self:
        _unique([(item.zone_id, item.position) for item in self.resolutions], "seed slots")
        _unique([item.registration_id for item in self.resolutions], "registration IDs")
        return self


class ConfirmQualifiersRequest(GroupSourceRequest):
    confirmation_key: ConfirmationKey


class SaveKnockoutRequest(RevisionRequest):
    games_a: NonNegativeInt
    games_b: NonNegativeInt
    set_complete: CompleteSet

    @model_validator(mode="after")
    def unequal_games(self) -> Self:
        # This checks transport only. Terminal sports rules remain pending D8.
        if self.games_a == self.games_b:
            raise ValueError("A completed knockout score cannot be tied")
        return self


class Zone(ContractModel):
    id: AmericanoId
    label: ZoneLabel


class Registration(ContractModel):
    id: AmericanoId
    zone_id: AmericanoId | None
    player1_name: Name
    player2_name: Name
    registration_order: PositiveInt


class SetupContinuation(ContractModel):
    kind: Literal["setup"]


class RoundContinuation(ContractModel):
    kind: Literal["round"]
    round_number: PositiveInt


class QualificationContinuation(ContractModel):
    kind: Literal["qualification"]


class PlayoffsContinuation(ContractModel):
    kind: Literal["playoffs"]


Continuation = Annotated[
    SetupContinuation | RoundContinuation | QualificationContinuation | PlayoffsContinuation,
    Field(discriminator="kind"),
]


class EventSummary(ContractModel):
    id: AmericanoId
    name: Name
    state: EventState
    zone_count: ZoneCount
    start_stage: StartStage
    revision: PositiveInt
    groups_revision: NonNegativeInt
    registration_count: NonNegativeInt
    total_rounds: NonNegativeInt
    saved_rounds: NonNegativeInt
    max_unlocked_round: NonNegativeInt
    continuation: Continuation


class ZoneQuota(ContractModel):
    zone_id: AmericanoId
    required: PositiveInt
    registered: NonNegativeInt
    sufficient: bool


class ConfigurationIssue(ContractModel):
    code: Literal["insufficient_registrations", "unassigned_registrations"]
    zone_id: AmericanoId | None
    registration_ids: list[AmericanoId]
    message: str


class EventDetail(EventSummary):
    zones: list[Zone]
    registrations: list[Registration]
    quotas: list[ZoneQuota]
    can_generate: bool
    configuration_issues: list[ConfigurationIssue]
    confirmed_at: UtcTimestamp | None
    champion_registration_id: AmericanoId | None


ListEventsResponse = list[EventSummary]


class GroupScore(ContractModel):
    games_a: GroupGames | None
    games_b: GroupGames | None

    @model_validator(mode="after")
    def paired_games(self) -> Self:
        if (self.games_a is None) != (self.games_b is None):
            raise ValueError("Group scores must be both null or both complete")
        return self


class GroupMatch(GroupScore):
    id: AmericanoId
    zone_id: AmericanoId
    display_order: PositiveInt
    registration_a: Registration
    registration_b: Registration

    @model_validator(mode="after")
    def canonical_sides(self) -> Self:
        if self.registration_a.id >= self.registration_b.id:
            raise ValueError("Group registration IDs must be canonical: a < b")
        return self


class RestingRegistration(ContractModel):
    registration: Registration
    reason: Literal["bye", "capacity", "zone_finished"]


class RoundResponse(ContractModel):
    event_id: AmericanoId
    event_name: Name
    state: EventState
    revision: PositiveInt
    groups_revision: NonNegativeInt
    number: PositiveInt
    total_rounds: NonNegativeInt
    max_unlocked_round: NonNegativeInt
    saved: bool
    locked: bool
    read_only: bool
    zones: list[Zone]
    matches: list[GroupMatch]
    resting: list[RestingRegistration]


class GenerateFixtureResponse(ContractModel):
    event: EventDetail
    first_round: RoundResponse | None


class StandingRow(ContractModel):
    registration: Registration
    played: NonNegativeInt
    won: NonNegativeInt
    drawn: NonNegativeInt
    lost: NonNegativeInt
    games_for: NonNegativeInt
    games_against: NonNegativeInt
    games_diff: StrictInt
    points_half_units: NonNegativeInt


class StandingBlock(ContractModel):
    position_from: PositiveInt
    position_to: PositiveInt
    points_half_units: NonNegativeInt
    games_diff: StrictInt
    rows: list[StandingRow]

    @model_validator(mode="after")
    def coherent_block(self) -> Self:
        expected_size = self.position_to - self.position_from + 1
        if expected_size < 1 or len(self.rows) != expected_size:
            raise ValueError("Standing block rows must cover its inclusive position range")
        metrics = (self.points_half_units, self.games_diff)
        if any((row.points_half_units, row.games_diff) != metrics for row in self.rows):
            raise ValueError("Standing block rows must share its points and games difference")
        return self


class ZoneStandings(ContractModel):
    zone: Zone
    blocks: list[StandingBlock]


class StandingsResponse(ContractModel):
    event_id: AmericanoId
    state: EventState
    revision: PositiveInt
    groups_revision: NonNegativeInt
    frozen: bool
    zones: list[ZoneStandings]


class SaveRoundResponse(ContractModel):
    round: RoundResponse
    standings: StandingsResponse


class NodeRef(ContractModel):
    stage: StartStage
    slot: PositiveInt


class QualificationSlot(SeedRef):
    candidate_registration_ids: list[AmericanoId]
    registration_id: AmericanoId | None
    requires_resolution: bool


class ResolvedSeed(SeedRef):
    registration_id: AmericanoId


class SeedSource(SeedRef):
    kind: Literal["seed"]


class WinnerSource(NodeRef):
    kind: Literal["winner"]


BracketSource = Annotated[SeedSource | WinnerSource, Field(discriminator="kind")]


class BracketDestination(NodeRef):
    side: Side


class BracketPreviewNode(NodeRef):
    source_a: BracketSource
    source_b: BracketSource
    registration_a_id: AmericanoId | None
    registration_b_id: AmericanoId | None
    next: BracketDestination | None


class OpeningPair(ContractModel):
    a: SeedRef
    b: SeedRef


class SeedingTemplate(ContractModel):
    key: str
    status: DecisionStatus
    start_stage: StartStage
    zone_count: ZoneCount
    opening_pairs: list[OpeningPair]


class QualificationBlocker(ContractModel):
    code: Literal["groups_incomplete", "configuration_invalid", "unresolved_ties", "seeding_pending_approval"]
    message: str


class QualificationResponse(ContractModel):
    event_id: AmericanoId
    state: EventState
    revision: PositiveInt
    source_groups_revision: NonNegativeInt
    standings: list[ZoneStandings]
    quotas: list[ZoneQuota]
    slots: list[QualificationSlot]
    missing_slots: list[SeedRef]
    resolved_seeds: list[ResolvedSeed]
    seeding_template: SeedingTemplate
    bracket: list[BracketPreviewNode]
    blockers: list[QualificationBlocker]
    can_confirm: bool
    frozen: bool


class QualifierSnapshot(ResolvedSeed):
    player1_name: Name
    player2_name: Name
    points_half_units: NonNegativeInt
    games_diff: StrictInt
    source_groups_revision: NonNegativeInt


class KnockoutScore(ContractModel):
    games_a: NonNegativeInt | None
    games_b: NonNegativeInt | None
    set_complete: bool

    @model_validator(mode="after")
    def coherent_score(self) -> Self:
        if self.set_complete:
            if self.games_a is None or self.games_b is None or self.games_a == self.games_b:
                raise ValueError("Completed knockout scores require two unequal games values")
        elif self.games_a is not None or self.games_b is not None:
            raise ValueError("Pending knockout scores require both games null")
        return self


class KnockoutNode(KnockoutScore):
    id: AmericanoId
    stage: StartStage
    slot: PositiveInt
    registration_a: Registration | None
    registration_b: Registration | None
    next_match_id: AmericanoId | None
    next_side: Side | None
    winner_registration_id: AmericanoId | None
    can_edit: bool
    edit_block_reason: Literal["participants_pending", "rules_pending_approval", "descendant_played"] | None

    @model_validator(mode="after")
    def coherent_destination(self) -> Self:
        if self.stage == "final":
            if self.next_match_id is not None or self.next_side is not None:
                raise ValueError("The final has no destination")
        elif self.next_match_id is None or self.next_side is None:
            raise ValueError("Non-final nodes require both destination ID and side")
        return self


class PlayoffsResponse(ContractModel):
    event_id: AmericanoId
    event_name: Name
    state: Literal["playoffs", "completed"]
    revision: PositiveInt
    groups_revision: NonNegativeInt
    start_stage: StartStage
    zones: list[Zone]
    snapshots: list[QualifierSnapshot]
    nodes: list[KnockoutNode]
    champion: Registration | None


class ConfirmationResponse(ContractModel):
    event: EventDetail
    confirmation_key: ConfirmationKey
    confirmed_source_revision: NonNegativeInt
    confirmed_at: UtcTimestamp
    playoffs: PlayoffsResponse


AmericanoErrorCode = Literal[
    "validation_error", "invalid_configuration", "invalid_reference", "invalid_round_results",
    "invalid_tie_resolution", "invalid_set", "not_found", "revision_conflict", "groups_revision_conflict",
    "state_conflict", "round_locked", "already_confirmed", "descendant_played", "participants_pending",
    "decision_pending",
]


class AmericanoFieldError(ContractModel):
    path: list[str | StrictInt]
    code: str
    message: str


class AmericanoErrorBody(ContractModel):
    detail: str
    code: AmericanoErrorCode
    message: str
    current_revision: PositiveInt | None = None
    fields: list[AmericanoFieldError] | None = None

    @model_validator(mode="after")
    def coherent_error(self) -> Self:
        if self.detail != self.message:
            raise ValueError("Error detail must equal message")
        metadata = self.model_fields_set & {"current_revision", "fields"}
        if any(getattr(self, field) is None for field in metadata):
            raise ValueError("Optional error metadata may be omitted, not null")
        return self

    @model_serializer(mode="wrap")
    def omit_absent_metadata(self, handler: SerializerFunctionWrapHandler) -> dict[str, object]:
        body = handler(self)
        return {key: value for key, value in body.items() if value is not None}
