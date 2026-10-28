// Development harness input only. Never import from production pages or routes.
// Static examples, not a mock service, algorithm implementation, or network fallback.
import type {
  ConfirmationResponse, EventDetail, PlayoffsResponse, QualificationResponse,
  Registration, RoundDraftRow, RoundResponse, StandingsResponse, StandingRow,
} from '../../../api/americano-types'

const zoneA = { id: 201, label: 'A' } as const
const zoneB = { id: 202, label: 'B' } as const
const p1: Registration = { id: 1, zone_id: 201, player1_name: 'Ana', player2_name: 'Luz', registration_order: 1 }
const p2: Registration = { id: 2, zone_id: 201, player1_name: 'Eva', player2_name: 'Sol', registration_order: 2 }
const p3: Registration = { id: 3, zone_id: 201, player1_name: 'Leo', player2_name: 'Juan', registration_order: 3 }
const p4: Registration = { id: 4, zone_id: 201, player1_name: 'Paz', player2_name: 'Mar', registration_order: 4 }
const p5: Registration = { id: 5, zone_id: 201, player1_name: 'Nico', player2_name: 'Teo', registration_order: 5 }
const p6: Registration = { id: 6, zone_id: 201, player1_name: 'Ivo', player2_name: 'Max', registration_order: 6 }
const p7: Registration = { id: 7, zone_id: 201, player1_name: 'Lola', player2_name: 'Mía', registration_order: 7 }
const p8: Registration = { id: 8, zone_id: 202, player1_name: 'Flor', player2_name: 'Vera', registration_order: 8 }
const p9: Registration = { id: 9, zone_id: 202, player1_name: 'Dani', player2_name: 'Fran', registration_order: 9 }
const p10: Registration = { id: 10, zone_id: 202, player1_name: 'Inés', player2_name: 'Alma', registration_order: 10 }
const p11: Registration = { id: 11, zone_id: 202, player1_name: 'Bruno', player2_name: 'Ciro', registration_order: 11 }
const p12: Registration = { id: 12, zone_id: 202, player1_name: 'Emma', player2_name: 'Sara', registration_order: 12 }
const p13: Registration = { id: 13, zone_id: 202, player1_name: 'Fede', player2_name: 'Tomi', registration_order: 13 }
const p14: Registration = { id: 14, zone_id: 202, player1_name: 'Rita', player2_name: 'Noa', registration_order: 14 }

export const draftEvent: EventDetail = {
  champion: null,
  courts: [1, 2, 3, 4, 5, 6],
  id: 101, name: 'Borrador vacío', state: 'draft', zone_count: 1, start_stage: 'semifinal',
  revision: 1, groups_revision: 0, registration_count: 0, total_rounds: 0, saved_rounds: 0,
  max_unlocked_round: 0, continuation: { kind: 'setup' }, zones: [zoneA], registrations: [],
  quotas: [{ zone_id: 201, required: 4, registered: 0, sufficient: false }], can_generate: false,
  configuration_issues: [{ code: 'insufficient_registrations', zone_id: 201, registration_ids: [], message: 'Zona A requiere 4 parejas.' }],
  confirmed_at: null, champion_registration_id: null,
}
export const roundEvent: EventDetail = {
  ...draftEvent, id: 102, name: 'Americano de cuatro', state: 'groups', revision: 2,
  registration_count: 4, total_rounds: 3, max_unlocked_round: 1, continuation: { kind: 'round', round_number: 1 },
  registrations: [p1, p2, p3, p4], quotas: [{ zone_id: 201, required: 4, registered: 4, sufficient: true }],
  configuration_issues: [],
}
export const emptyRound: RoundResponse = {
  event_id: 102, event_name: 'Americano de cuatro', state: 'groups', revision: 2, groups_revision: 0,
  number: 1, total_rounds: 3, max_unlocked_round: 1, saved: false, locked: false, read_only: false,
  zones: [zoneA], resting: [], matches: [
    { id: 301, zone_id: 201, display_order: 1, registration_a: p1, registration_b: p4, games_a: null, games_b: null },
    { id: 302, zone_id: 201, display_order: 2, registration_a: p2, registration_b: p3, games_a: null, games_b: null },
  ].map(match => ({ ...match, court_number: match.display_order })),
}
export const zeroZeroRound: RoundResponse = {
  ...emptyRound, revision: 3, groups_revision: 1, saved: true, max_unlocked_round: 2, matches: [
    { id: 301, zone_id: 201, display_order: 1, registration_a: p1, registration_b: p4, games_a: 0 as const, games_b: 0 as const },
    { id: 302, zone_id: 201, display_order: 2, registration_a: p2, registration_b: p3, games_a: 0 as const, games_b: 0 as const },
  ].map(match => ({ ...match, court_number: match.display_order })),
}
export const sixMatchesRound: RoundResponse = {
  ...emptyRound, event_id: 103, event_name: 'Dos zonas de siete', total_rounds: 7, zones: [zoneA, zoneB],
  matches: [
    { id: 311, zone_id: 201, display_order: 1, registration_a: p1, registration_b: p2, games_a: null, games_b: null },
    { id: 312, zone_id: 201, display_order: 2, registration_a: p3, registration_b: p4, games_a: null, games_b: null },
    { id: 313, zone_id: 201, display_order: 3, registration_a: p5, registration_b: p6, games_a: null, games_b: null },
    { id: 314, zone_id: 202, display_order: 4, registration_a: p8, registration_b: p9, games_a: null, games_b: null },
    { id: 315, zone_id: 202, display_order: 5, registration_a: p10, registration_b: p11, games_a: null, games_b: null },
    { id: 316, zone_id: 202, display_order: 6, registration_a: p12, registration_b: p13, games_a: null, games_b: null },
  ].map(match => ({ ...match, court_number: match.display_order })), resting: [{ registration: p7, reason: 'bye' }, { registration: p14, reason: 'bye' }],
}
export const byesRound: RoundResponse = { ...sixMatchesRound }
export const elevenFieldsDraft: RoundDraftRow[] = [
  { match_id: 311, games_a: '0', games_b: '0' }, { match_id: 312, games_a: '5', games_b: '3' },
  { match_id: 313, games_a: '2', games_b: '2' }, { match_id: 314, games_a: '9', games_b: '0' },
  { match_id: 315, games_a: '1', games_b: '4' }, { match_id: 316, games_a: '3', games_b: '' },
]

// Four pairs, all six matches drawn 0-0: each played 3, earned 3 half-units.
const row1: StandingRow = { registration: p1, played: 3, won: 0, drawn: 3, lost: 0, games_for: 0, games_against: 0, games_diff: 0, points_half_units: 3 }
const row2: StandingRow = { ...row1, registration: p2 }
const row3: StandingRow = { ...row1, registration: p3 }
const row4: StandingRow = { ...row1, registration: p4 }
export const tiedStandings: StandingsResponse = {
  event_id: 102, state: 'review', revision: 5, groups_revision: 3, frozen: false,
  zones: [{ zone: zoneA, blocks: [{ position_from: 1, position_to: 4, points_half_units: 3, games_diff: 0, rows: [row1, row2, row3, row4] }] }],
}
// Replace 1-v-3 and 2-v-4 with 1-0 wins; other four games remain 0-0.
export const twoWayTies: StandingsResponse = {
  ...tiedStandings, revision: 6, groups_revision: 4, zones: [{ zone: zoneA, blocks: [
    { position_from: 1, position_to: 2, points_half_units: 4, games_diff: 1, rows: [
      { ...row1, won: 1, drawn: 2, games_for: 1, games_diff: 1, points_half_units: 4 },
      { ...row2, won: 1, drawn: 2, games_for: 1, games_diff: 1, points_half_units: 4 },
    ] },
    { position_from: 3, position_to: 4, points_half_units: 2, games_diff: -1, rows: [
      { ...row3, lost: 1, drawn: 2, games_against: 1, games_diff: -1, points_half_units: 2 },
      { ...row4, lost: 1, drawn: 2, games_against: 1, games_diff: -1, points_half_units: 2 },
    ] },
  ] }],
}
export const reviewEvent: EventDetail = {
  ...roundEvent, state: 'review', revision: 5, groups_revision: 3, saved_rounds: 3,
  max_unlocked_round: 3, continuation: { kind: 'qualification' },
}
export const review: QualificationResponse = {
  event_id: 102, state: 'review', revision: 5, source_groups_revision: 3,
  standings: tiedStandings.zones, quotas: reviewEvent.quotas, frozen: false,
  slots: [
    { zone_id: 201, position: 1, candidate_registration_ids: [1, 2, 3, 4], registration_id: null, requires_resolution: true },
    { zone_id: 201, position: 2, candidate_registration_ids: [1, 2, 3, 4], registration_id: null, requires_resolution: true },
    { zone_id: 201, position: 3, candidate_registration_ids: [1, 2, 3, 4], registration_id: null, requires_resolution: true },
    { zone_id: 201, position: 4, candidate_registration_ids: [1, 2, 3, 4], registration_id: null, requires_resolution: true },
  ], missing_slots: [{ zone_id: 201, position: 1 }, { zone_id: 201, position: 2 }, { zone_id: 201, position: 3 }, { zone_id: 201, position: 4 }],
  resolved_seeds: [], seeding_template: {
    key: 'semifinal-one-zone-v1', status: 'approved', start_stage: 'semifinal', zone_count: 1,
    opening_pairs: [
      { a: { zone_id: 201, position: 1 }, b: { zone_id: 201, position: 4 } },
      { a: { zone_id: 201, position: 2 }, b: { zone_id: 201, position: 3 } },
    ],
  }, bracket: [
    { stage: 'semifinal', slot: 1, source_a: { kind: 'seed', zone_id: 201, position: 1 }, source_b: { kind: 'seed', zone_id: 201, position: 4 }, registration_a_id: null, registration_b_id: null, next: { stage: 'final', slot: 1, side: 'a' } },
    { stage: 'semifinal', slot: 2, source_a: { kind: 'seed', zone_id: 201, position: 2 }, source_b: { kind: 'seed', zone_id: 201, position: 3 }, registration_a_id: null, registration_b_id: null, next: { stage: 'final', slot: 1, side: 'b' } },
    { stage: 'final', slot: 1, source_a: { kind: 'winner', stage: 'semifinal', slot: 1 }, source_b: { kind: 'winner', stage: 'semifinal', slot: 2 }, registration_a_id: null, registration_b_id: null, next: null },
  ], blockers: [{ code: 'unresolved_ties', message: 'Seleccioná las cuatro plazas según el sorteo humano.' }], can_confirm: false,
}
export const resolvedReview: QualificationResponse = {
  ...review, revision: 6, can_confirm: true, blockers: [], missing_slots: [], slots: [
    { zone_id: 201, position: 1, candidate_registration_ids: [1, 2, 3, 4], registration_id: 2, requires_resolution: true },
    { zone_id: 201, position: 2, candidate_registration_ids: [1, 2, 3, 4], registration_id: 1, requires_resolution: true },
    { zone_id: 201, position: 3, candidate_registration_ids: [1, 2, 3, 4], registration_id: 4, requires_resolution: true },
    { zone_id: 201, position: 4, candidate_registration_ids: [1, 2, 3, 4], registration_id: 3, requires_resolution: true },
  ], resolved_seeds: [
    { zone_id: 201, position: 1, registration_id: 2 }, { zone_id: 201, position: 2, registration_id: 1 },
    { zone_id: 201, position: 3, registration_id: 4 }, { zone_id: 201, position: 4, registration_id: 3 },
  ], bracket: [
    { stage: 'semifinal', slot: 1, source_a: { kind: 'seed', zone_id: 201, position: 1 }, source_b: { kind: 'seed', zone_id: 201, position: 4 }, registration_a_id: 2, registration_b_id: 3, next: { stage: 'final', slot: 1, side: 'a' } },
    { stage: 'semifinal', slot: 2, source_a: { kind: 'seed', zone_id: 201, position: 2 }, source_b: { kind: 'seed', zone_id: 201, position: 3 }, registration_a_id: 1, registration_b_id: 4, next: { stage: 'final', slot: 1, side: 'b' } },
    { stage: 'final', slot: 1, source_a: { kind: 'winner', stage: 'semifinal', slot: 1 }, source_b: { kind: 'winner', stage: 'semifinal', slot: 2 }, registration_a_id: null, registration_b_id: null, next: null },
  ],
}
export const bracket: PlayoffsResponse = {
  courts: [1, 2, 3, 4, 5, 6],
  event_id: 102, event_name: 'Americano de cuatro', state: 'playoffs', revision: 7, groups_revision: 3,
  start_stage: 'semifinal', zones: [zoneA], champion: null, snapshots: [
    { zone_id: 201, position: 1, registration_id: 2, player1_name: 'Eva', player2_name: 'Sol', points_half_units: 3, games_diff: 0, source_groups_revision: 3 },
    { zone_id: 201, position: 2, registration_id: 1, player1_name: 'Ana', player2_name: 'Luz', points_half_units: 3, games_diff: 0, source_groups_revision: 3 },
    { zone_id: 201, position: 3, registration_id: 4, player1_name: 'Paz', player2_name: 'Mar', points_half_units: 3, games_diff: 0, source_groups_revision: 3 },
    { zone_id: 201, position: 4, registration_id: 3, player1_name: 'Leo', player2_name: 'Juan', points_half_units: 3, games_diff: 0, source_groups_revision: 3 },
  ], nodes: [
    { id: 401, stage: 'semifinal', slot: 1, court_number: 1, registration_a: p2, registration_b: p3, games_a: null, games_b: null, set_complete: false, next_match_id: 403, next_side: 'a', winner_registration_id: null, can_edit: true, edit_block_reason: null },
    { id: 402, stage: 'semifinal', slot: 2, court_number: 2, registration_a: p1, registration_b: p4, games_a: null, games_b: null, set_complete: false, next_match_id: 403, next_side: 'b', winner_registration_id: null, can_edit: true, edit_block_reason: null },
    { id: 403, stage: 'final', slot: 1, court_number: 1, registration_a: null, registration_b: null, games_a: null, games_b: null, set_complete: false, next_match_id: null, next_side: null, winner_registration_id: null, can_edit: false, edit_block_reason: 'participants_pending' },
  ],
}
export const snapshot: ConfirmationResponse = {
  event: { ...reviewEvent, state: 'playoffs', revision: 7, continuation: { kind: 'playoffs' }, confirmed_at: '2026-10-20T12:00:00Z' },
  confirmation_key: '00000000-0000-4000-8000-000000000001', confirmed_source_revision: 3,
  confirmed_at: '2026-10-20T12:00:00Z', playoffs: bracket,
}
export const scenarios = {
  draft: draftEvent, empty: emptyRound, zeroZero: zeroZeroRound, sixMatches: sixMatchesRound,
  byes: byesRound, elevenFieldsDraft, ties: tiedStandings, twoWayTies, review, resolvedReview,
  snapshot, bracket,
}
