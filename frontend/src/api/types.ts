// Mirrors the response schemas in backend/src/app/*/schemas.py.

export type TeamStatus = 'active' | 'withdrawn'
export type MatchStatus = 'pending' | 'played'

export interface Zone {
  id: number
  name: string
}

export interface Team {
  id: number
  zone_id: number
  player_one_name: string
  player_two_name: string
  photo_url: string | null
  status: TeamStatus
}

export interface MatchSet {
  set_number: number
  team_a_games: number
  team_b_games: number
}

export interface Match {
  id: number
  team_a_id: number
  team_b_id: number
  date: string
  /** `HH:MM:SS`, or null while the pairs have not agreed on one. */
  time: string | null
  /**
   * The club, or null while it is not decided. `string` stays in the union on
   * purpose: it keeps autocomplete for the clubs we know while still accepting
   * one the API adds before this file catches up.
   */
  venue: MatchVenue | (string & {}) | null
  status: MatchStatus
  sets: MatchSet[]
  winner_team_id: number | null
  photo_url: string | null
  comment: string | null
}

/** Mirrors COMMENT_MAX_LENGTH in backend/src/app/matches/models.py. */
export const COMMENT_MAX_LENGTH = 280

/** The clubs of `MatchVenue` in backend/src/app/matches/models.py. */
export type MatchVenue =
  | 'boss_padel'
  | 'cofam'
  | 'arena'
  | 'indoor'
  | 'padelon'
  | 'punto_de_oro'
  | 'otro'

/**
 * The label the site shows for each club. Declared once: the form, the panel
 * table and the public cards all read the name from here, so no club gets two
 * spellings.
 *
 * Typing it against `MatchVenue` rather than `string` is what keeps the two
 * lists from drifting: adding a club to the union without a label here stops
 * compiling.
 */
export const VENUE_LABELS: Record<MatchVenue, string> = {
  boss_padel: 'Boss Pádel',
  cofam: 'Cofam',
  arena: 'Arena',
  indoor: 'Indoor',
  padelon: 'Padelón',
  punto_de_oro: 'Punto de Oro',
  otro: 'Otro',
}

/** The club's name, or null when there is none to show. */
export function venueLabel(venue: string | null): string | null {
  if (!venue) return null
  // A venue the front end does not know yet is shown raw rather than hidden:
  // a new club added to the API is still better information than nothing.
  return VENUE_LABELS[venue as MatchVenue] ?? venue
}

/** `HH:MM:SS` as `HH:MM`. Seconds are noise in a fixture. */
export function formatTime(time: string | null): string | null {
  if (!time) return null
  return time.slice(0, 5)
}

export interface Sponsor {
  id: number
  name: string
  logo_url: string
  url: string | null
  is_active: boolean
}

export interface Admin {
  id: number
  email: string
  is_active: boolean
}

export interface Standing {
  position: number
  team_id: number
  played: number
  won: number
  lost: number
  points: number
  sets_won: number
  sets_lost: number
  sets_diff: number
  games_won: number
  games_lost: number
  games_diff: number
  points_average: number
}

export function teamName(team: Team | undefined): string {
  if (!team) return '—'
  return `${team.player_one_name} / ${team.player_two_name}`
}
