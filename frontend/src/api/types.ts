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
  status: MatchStatus
  sets: MatchSet[]
  winner_team_id: number | null
  photo_url: string | null
  comment: string | null
}

/** Mirrors COMMENT_MAX_LENGTH in backend/src/app/matches/models.py. */
export const COMMENT_MAX_LENGTH = 280

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
