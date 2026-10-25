// Component contract v3.0.0; HTTP/DTO unchanged from v2.1.0. Type exports only.
// Source: openspec/changes/admin-americanos/contracts.md.
export type AmericanoId = number
export type EventState = 'draft' | 'groups' | 'review' | 'playoffs' | 'completed'
export type StartStage = 'quarterfinal' | 'semifinal' | 'final'
export type ZoneLabel = 'A' | 'B'
export type ZoneCount = 1 | 2
export type Side = 'a' | 'b'
export type GroupGames = 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9
export type ScoreInput = '' | '0' | '1' | '2' | '3' | '4' | '5' | '6' | '7' | '8' | '9'
export type DecisionStatus = 'approved' | 'proposed'

export interface RevisionRequest { expected_revision: number }
export interface GroupSourceRequest extends RevisionRequest { source_groups_revision: number }
export interface CreateEventRequest { name: string; zone_count: ZoneCount; start_stage: StartStage }
export interface UpdateEventRequest extends RevisionRequest {
  name?: string
  zone_count?: ZoneCount
  start_stage?: StartStage
}
export interface RegistrationRequest extends RevisionRequest { player1_name: string; player2_name: string }
export interface RegistrationInput { player1_name: string; player2_name: string }
export interface BulkRegistrationRequest extends RevisionRequest { registrations: RegistrationInput[] }
export interface UpdateRegistrationRequest extends RevisionRequest {
  player1_name?: string
  player2_name?: string
}
export interface SetZonesRequest extends RevisionRequest {
  zone_count: ZoneCount
  zone_a_registration_ids: AmericanoId[]
}
export interface Zone { id: AmericanoId; label: ZoneLabel }
export interface Registration {
  id: AmericanoId
  zone_id: AmericanoId | null
  player1_name: string
  player2_name: string
  registration_order: number
}
export type Continuation =
  | { kind: 'setup' }
  | { kind: 'round'; round_number: number }
  | { kind: 'qualification' }
  | { kind: 'playoffs' }
export type AmericanoNavigation =
  | { kind: 'list' }
  | { kind: 'event'; event_id: AmericanoId }
  | { kind: 'setup'; event_id: AmericanoId }
  | { kind: 'round'; event_id: AmericanoId; round_number: number }
  | { kind: 'qualification'; event_id: AmericanoId }
  | { kind: 'playoffs'; event_id: AmericanoId }

export interface EventSummary {
  id: AmericanoId
  name: string
  state: EventState
  zone_count: ZoneCount
  start_stage: StartStage
  revision: number
  groups_revision: number
  registration_count: number
  total_rounds: number
  saved_rounds: number
  max_unlocked_round: number
  continuation: Continuation
}
export interface ZoneQuota {
  zone_id: AmericanoId
  required: number
  registered: number
  sufficient: boolean
}
export interface ConfigurationIssue {
  code: 'insufficient_registrations' | 'unassigned_registrations'
  zone_id: AmericanoId | null
  registration_ids: AmericanoId[]
  message: string
}
export interface EventDetail extends EventSummary {
  zones: Zone[]
  registrations: Registration[]
  quotas: ZoneQuota[]
  can_generate: boolean
  configuration_issues: ConfigurationIssue[]
  confirmed_at: string | null
  champion_registration_id: AmericanoId | null
}
export type ListEventsResponse = EventSummary[]

export type GroupScore =
  | { games_a: null; games_b: null }
  | { games_a: GroupGames; games_b: GroupGames }
export type GroupMatch = GroupScore & {
  id: AmericanoId
  zone_id: AmericanoId
  display_order: number
  registration_a: Registration
  registration_b: Registration
}
export interface RestingRegistration {
  registration: Registration
  reason: 'bye' | 'capacity' | 'zone_finished'
}
export interface RoundResponse {
  event_id: AmericanoId
  event_name: string
  state: EventState
  revision: number
  groups_revision: number
  number: number
  total_rounds: number
  max_unlocked_round: number
  saved: boolean
  locked: boolean
  read_only: boolean
  zones: Zone[]
  matches: GroupMatch[]
  resting: RestingRegistration[]
}
export interface GroupResult { match_id: AmericanoId; games_a: GroupGames; games_b: GroupGames }
export interface SaveRoundRequest extends RevisionRequest { results: GroupResult[] }
export interface StandingRow {
  registration: Registration
  played: number
  won: number
  drawn: number
  lost: number
  games_for: number
  games_against: number
  games_diff: number
  points_half_units: number
}
export interface StandingBlock {
  position_from: number
  position_to: number
  points_half_units: number
  games_diff: number
  rows: StandingRow[]
}
export interface ZoneStandings { zone: Zone; blocks: StandingBlock[] }
export interface StandingsResponse {
  event_id: AmericanoId
  state: EventState
  revision: number
  groups_revision: number
  frozen: boolean
  zones: ZoneStandings[]
}
export interface SaveRoundResponse { round: RoundResponse; standings: StandingsResponse }
export interface GenerateFixtureResponse { event: EventDetail; first_round: RoundResponse | null }

export interface SeedRef { zone_id: AmericanoId; position: number }
export interface NodeRef { stage: StartStage; slot: number }
export interface TieResolution extends SeedRef { registration_id: AmericanoId }
export interface SaveTieResolutionsRequest extends GroupSourceRequest { resolutions: TieResolution[] }
export interface QualificationSlot extends SeedRef {
  candidate_registration_ids: AmericanoId[]
  registration_id: AmericanoId | null
  requires_resolution: boolean
}
export interface ResolvedSeed extends SeedRef { registration_id: AmericanoId }
export type BracketSource =
  | ({ kind: 'seed' } & SeedRef)
  | ({ kind: 'winner' } & NodeRef)
export interface BracketDestination extends NodeRef { side: Side }
export interface BracketPreviewNode extends NodeRef {
  source_a: BracketSource
  source_b: BracketSource
  registration_a_id: AmericanoId | null
  registration_b_id: AmericanoId | null
  next: BracketDestination | null
}
export interface SeedingTemplate {
  key: string
  status: DecisionStatus
  start_stage: StartStage
  zone_count: ZoneCount
  opening_pairs: { a: SeedRef; b: SeedRef }[]
}
export interface QualificationBlocker {
  code: 'groups_incomplete' | 'configuration_invalid' | 'unresolved_ties' | 'seeding_pending_approval'
  message: string
}
export interface QualificationResponse {
  event_id: AmericanoId
  state: EventState
  revision: number
  source_groups_revision: number
  standings: ZoneStandings[]
  quotas: ZoneQuota[]
  slots: QualificationSlot[]
  missing_slots: SeedRef[]
  resolved_seeds: ResolvedSeed[]
  seeding_template: SeedingTemplate
  bracket: BracketPreviewNode[]
  blockers: QualificationBlocker[]
  can_confirm: boolean
  frozen: boolean
}
export interface ConfirmQualifiersRequest extends GroupSourceRequest { confirmation_key: string }
export interface QualifierSnapshot extends ResolvedSeed {
  player1_name: string
  player2_name: string
  points_half_units: number
  games_diff: number
  source_groups_revision: number
}
export type KnockoutScore =
  | { games_a: null; games_b: null; set_complete: false }
  | { games_a: number; games_b: number; set_complete: true }
export type KnockoutNode = KnockoutScore & NodeRef & {
  id: AmericanoId
  registration_a: Registration | null
  registration_b: Registration | null
  next_match_id: AmericanoId | null
  next_side: Side | null
  winner_registration_id: AmericanoId | null
  can_edit: boolean
  edit_block_reason: 'participants_pending' | 'rules_pending_approval' | 'descendant_played' | null
}
export interface PlayoffsResponse {
  event_id: AmericanoId
  event_name: string
  state: 'playoffs' | 'completed'
  revision: number
  groups_revision: number
  start_stage: StartStage
  zones: Zone[]
  snapshots: QualifierSnapshot[]
  nodes: KnockoutNode[]
  champion: Registration | null
}
export interface ConfirmationResponse {
  event: EventDetail
  confirmation_key: string
  confirmed_source_revision: number
  confirmed_at: string
  playoffs: PlayoffsResponse
}
export interface SaveKnockoutRequest extends RevisionRequest {
  games_a: number
  games_b: number
  set_complete: true
}

export type AmericanoErrorCode =
  | 'validation_error' | 'invalid_configuration' | 'invalid_reference'
  | 'invalid_round_results' | 'invalid_tie_resolution' | 'invalid_set'
  | 'not_found' | 'revision_conflict' | 'groups_revision_conflict'
  | 'state_conflict' | 'round_locked' | 'already_confirmed'
  | 'descendant_played' | 'participants_pending' | 'decision_pending'
export interface AmericanoFieldError { path: (string | number)[]; code: string; message: string }
export interface AmericanoErrorBody {
  detail: string
  code: AmericanoErrorCode
  message: string
  current_revision?: number
  fields?: AmericanoFieldError[]
}

// Full future port; live clients publish only their implemented capabilities.
export interface AmericanoOperations {
  listEvents(): Promise<ListEventsResponse>
  createEvent(request: CreateEventRequest): Promise<EventDetail>
  loadEvent(eventId: AmericanoId): Promise<EventDetail>
  updateEvent(eventId: AmericanoId, request: UpdateEventRequest): Promise<EventDetail>
  addRegistration(eventId: AmericanoId, request: RegistrationRequest): Promise<EventDetail>
  addRegistrations(eventId: AmericanoId, request: BulkRegistrationRequest): Promise<EventDetail>
  updateRegistration(eventId: AmericanoId, registrationId: AmericanoId, request: UpdateRegistrationRequest): Promise<EventDetail>
  deleteRegistration(eventId: AmericanoId, registrationId: AmericanoId, request: RevisionRequest): Promise<EventDetail>
  setZones(eventId: AmericanoId, request: SetZonesRequest): Promise<EventDetail>
  clearZones(eventId: AmericanoId, request: RevisionRequest): Promise<EventDetail>
  randomizeZones(eventId: AmericanoId, request: RevisionRequest): Promise<EventDetail>
  generateFixture(eventId: AmericanoId, request: RevisionRequest): Promise<GenerateFixtureResponse>
  loadRound(eventId: AmericanoId, roundNumber: number): Promise<RoundResponse>
  saveRound(eventId: AmericanoId, roundNumber: number, request: SaveRoundRequest): Promise<SaveRoundResponse>
  loadStandings(eventId: AmericanoId): Promise<StandingsResponse>
  loadQualification(eventId: AmericanoId): Promise<QualificationResponse>
  saveTieResolutions(eventId: AmericanoId, request: SaveTieResolutionsRequest): Promise<QualificationResponse>
  confirmQualifiers(eventId: AmericanoId, request: ConfirmQualifiersRequest): Promise<ConfirmationResponse>
  loadPlayoffs(eventId: AmericanoId): Promise<PlayoffsResponse>
  saveKnockout(eventId: AmericanoId, nodeId: AmericanoId, request: SaveKnockoutRequest): Promise<PlayoffsResponse>
}

export interface AmericanoPageProps {
  operations: AmericanoOperations
  onNavigate: (target: AmericanoNavigation) => void
}
export type AmericanoDraftOperations = Pick<AmericanoOperations,
  'listEvents' | 'createEvent' | 'loadEvent' | 'updateEvent' |
  'addRegistration' | 'updateRegistration' | 'deleteRegistration'>
export type AmericanoSetupCapabilities = Pick<AmericanoOperations,
  'addRegistrations' | 'setZones' | 'clearZones' | 'randomizeZones' | 'generateFixture'>
export type AmericanoRoundReadOperations = Pick<AmericanoOperations,
  'loadEvent' | 'loadRound' | 'loadStandings'>
export type AmericanoRoundOperations = AmericanoRoundReadOperations & Pick<AmericanoOperations, 'saveRound'>
export type AmericanoQualificationOperations = Pick<AmericanoOperations,
  'loadEvent' | 'loadQualification' | 'saveTieResolutions' | 'confirmQualifiers'>
export type AmericanoPlayoffsReadOperations = Pick<AmericanoOperations, 'loadEvent' | 'loadPlayoffs'>
export type AmericanoPlayoffsOperations = AmericanoPlayoffsReadOperations & Pick<AmericanoOperations, 'saveKnockout'>
export interface AmericanoListPageProps {
  operations: Pick<AmericanoDraftOperations, 'listEvents' | 'createEvent'>
  onNavigate: (target: AmericanoNavigation) => void
}
export interface AmericanoSetupPageProps {
  operations: Pick<AmericanoDraftOperations,
    'loadEvent' | 'updateEvent' | 'addRegistration' | 'updateRegistration' | 'deleteRegistration'>
    & Partial<AmericanoSetupCapabilities>
  onNavigate: (target: AmericanoNavigation) => void
  eventId: AmericanoId
}
export interface AmericanoEventPageProps extends AmericanoPageProps { eventId: AmericanoId }
export interface AmericanoQualificationPageProps extends Omit<AmericanoEventPageProps, 'operations'> {
  operations: AmericanoQualificationOperations
}
export interface AmericanoPlayoffsPageProps extends Omit<AmericanoEventPageProps, 'operations'> {
  operations: AmericanoPlayoffsOperations
  onDirtyChange: (draft: DirtyNavigationDraft | null) => void
}
export interface DirtyNavigationDraft {
  dirty: boolean
  // Live even before a render: write in flight or canonical reconciliation unresolved.
  readonly pending: boolean
  save: () => Promise<boolean>
  // false means navigation/logout MUST remain blocked.
  discard: () => boolean
}
export interface AmericanoRoundPageProps extends Omit<AmericanoEventPageProps, 'operations'> {
  operations: AmericanoRoundOperations
  roundNumber: number
  onDirtyChange: (draft: DirtyNavigationDraft | null) => void
  mode?: 'editable' | 'consultation'
}
export interface RoundDraftRow { match_id: AmericanoId; games_a: ScoreInput; games_b: ScoreInput }
export interface ScoreRowProps {
  match: GroupMatch
  zoneLabel: ZoneLabel
  value: RoundDraftRow
  readOnly: boolean
  errors: Partial<Record<Side, string>>
  onChange: (matchId: AmericanoId, side: Side, value: ScoreInput) => void
  onAdvance: (matchId: AmericanoId, side: Side) => void
  onInvalidInput?: () => void
  registerInput: (matchId: AmericanoId, side: Side, element: HTMLInputElement | null) => void
}
export interface StandingsDrawerProps {
  open: boolean
  standings: StandingsResponse | null
  loading: boolean
  error: string | null
  onClose: () => void
  returnFocusTo: HTMLElement | null
}
export interface QualificationSlotsProps {
  preview: QualificationResponse
  registrations: Registration[]
  resolutions: TieResolution[]
  disabled: boolean
  onChange: (resolutions: TieResolution[]) => void
}
export interface RoundDraftState {
  rows: RoundDraftRow[]
  dirty: boolean
  errors: Record<number, Partial<Record<Side, string>>>
  setScore: (matchId: AmericanoId, side: Side, value: ScoreInput) => void
  validate: () => SaveRoundRequest | null
  reset: () => void
  accept: (round: RoundResponse) => void
  // Caller must review canonical scores and verify unchanged match membership first.
  rebase: (round: RoundResponse) => void
}
