// Mirrors backend/src/app/playoffs/schemas.py.

export type PlayoffRound = 'round_1' | 'round_2' | 'quarterfinal' | 'semifinal' | 'final'
export type PlayoffMatchStatus = 'pending' | 'bye'
export type BracketMode = 'projection' | 'official'

export interface PlayoffTeam {
  id: number
  player_one_name: string
  player_two_name: string
  photo_url: string | null
  /**
   * "3A", "10B" — the team's zone standing, not the node's. The backend
   * fills this for every team in every round (see `PlayoffTeamRead.seed`),
   * so it is always correct for a round-2, semifinal or final team too, not
   * only round 1 and a quarterfinal's direct qualifier.
   */
  seed: string
}

export interface PlayoffMatchSet {
  set_number: number
  team_a_games: number
  team_b_games: number
}

/** Shaped like `Match` in api/types.ts, but only the fields the bracket modal shows. */
export interface PlayoffTieMatch {
  id: number
  team_a_id: number
  team_b_id: number
  date: string
  time: string | null
  venue: string | null
  status: 'pending' | 'played'
  sets: PlayoffMatchSet[]
  winner_team_id: number | null
  photo_url: string | null
  comment: string | null
}

export interface PlayoffNode {
  id: number | null
  slot: number
  status: PlayoffMatchStatus
  team_a: PlayoffTeam | null
  team_b: PlayoffTeam | null
  match: PlayoffTieMatch | null
}

/** In DRAW order, not slot order — see `PlayoffRoundRead` in the backend. */
export interface PlayoffRoundData {
  round: PlayoffRound
  nodes: PlayoffNode[]
}

export interface Bracket {
  mode: BracketMode
  rounds: PlayoffRoundData[]
  pending_group_matches: number | null
}

export interface PendingGroupMatch {
  id: number
  team_a: PlayoffTeam
  team_b: PlayoffTeam
}

export interface GroupStagePendingError {
  detail: string
  pending_count: number
  pending_matches: PendingGroupMatch[]
}

export interface PlayoffResultsLoadedError {
  detail: string
  played_count: number
}

export const ROUND_LABELS: Record<PlayoffRound, string> = {
  round_1: 'Ronda 1',
  round_2: 'Ronda 2',
  quarterfinal: 'Cuartos',
  semifinal: 'Semifinal',
  final: 'Final',
}

/**
 * What an empty side of a node names itself while it waits.
 *
 * Every node fed by another node (rather than a seed) is fed by exactly one
 * round — the one right before it in the tree — so this is keyed by the
 * node's OWN round, not by the feeder. Round 1 never needs an entry: every
 * one of its sides is a seed, resolved (or ruled out as a bye) the moment
 * the bracket exists.
 */
export const WAITING_FOR_LABEL: Partial<Record<PlayoffRound, string>> = {
  round_2: 'Ganador Ronda 1',
  quarterfinal: 'Ganador Ronda 2',
  semifinal: 'Ganador cuartos',
  final: 'Ganador semifinal',
}

/** The numeric part of a seed label ("3A" -> 3), for comparisons like "is this a top-2 seed". */
function seedPosition(team: PlayoffTeam): number {
  const match = /^(\d+)/.exec(team.seed)
  return match ? Number(match[1]) : Number.POSITIVE_INFINITY
}

/**
 * Whether `team` is one of the quarterfinal's four direct qualifiers (1A,
 * 2A, 1B, 2B), rather than a round-2 winner.
 *
 * Derived from the team's own seed rather than which side of the node it
 * sits on or a hardcoded slot table: by tournament design (see
 * `BRACKET_TEMPLATE` in `backend/src/app/playoffs/models.py`) round 1 only
 * ever seeds positions 3 and below, so a position-1 or position-2 team
 * reaching the quarterfinal round can only have arrived there as a direct
 * qualifier, never by winning through round 1 and round 2.
 */
export function isDirectQualifier(round: PlayoffRound, team: PlayoffTeam): boolean {
  return round === 'quarterfinal' && seedPosition(team) <= 2
}

export function pairName(team: PlayoffTeam | null): string {
  if (!team) return '—'
  return `${team.player_one_name} / ${team.player_two_name}`
}

/** How many sets `teamId` won in a played tie. */
export function setsWonBy(match: PlayoffTieMatch, teamId: number): number {
  return match.sets.filter((set) => {
    const teamAWon = set.team_a_games > set.team_b_games
    return (match.team_a_id === teamId) === teamAWon
  }).length
}

/**
 * Reads the structured body of a 409 from `POST /playoffs/generate` without
 * `force`, or `null` if this error is not that one.
 *
 * FastAPI wraps a raised `detail=` under its own top-level `detail` key, so
 * the actual `GroupStagePendingError` fields sit one level down from the
 * response body — `{"detail": {"detail": "...", "pending_count": …}}`.
 */
export function asGroupStagePendingError(body: unknown): GroupStagePendingError | null {
  if (typeof body !== 'object' || body === null) return null
  const detail = (body as { detail?: unknown }).detail
  if (typeof detail !== 'object' || detail === null) return null
  const candidate = detail as Partial<GroupStagePendingError>
  if (typeof candidate.pending_count !== 'number' || !Array.isArray(candidate.pending_matches)) {
    return null
  }
  return candidate as GroupStagePendingError
}

/** Same idea as `asGroupStagePendingError`, for `DELETE /playoffs`'s 409. */
export function asPlayoffResultsLoadedError(body: unknown): PlayoffResultsLoadedError | null {
  if (typeof body !== 'object' || body === null) return null
  const detail = (body as { detail?: unknown }).detail
  if (typeof detail !== 'object' || detail === null) return null
  const candidate = detail as Partial<PlayoffResultsLoadedError>
  if (typeof candidate.played_count !== 'number') return null
  return candidate as PlayoffResultsLoadedError
}

/**
 * Groups `previous`'s items into however many feed each item of `next`, in
 * order — the same fact the "no crossing lines" draw order rests on: this
 * round's array, walked in groups of `previous.length / next.length`, feeds
 * the next round's array position by position. Derived from the two arrays'
 * lengths alone, never from a hardcoded pairing, so it keeps working
 * whichever rounds it is handed (round 1 into round 2 groups by two; round 2
 * into the quarterfinal is already one-to-one).
 */
export function groupFeeders<T>(previous: T[], next: unknown[]): T[][] {
  if (next.length === 0) return []
  const groupSize = previous.length / next.length
  return next.map((_, index) => previous.slice(index * groupSize, (index + 1) * groupSize))
}
