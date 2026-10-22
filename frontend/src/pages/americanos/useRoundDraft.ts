import { useCallback, useState } from 'react'
import type {
  GroupGames, RoundDraftRow, RoundDraftState, RoundResponse, SaveRoundRequest, ScoreInput, Side,
} from '../../api/americano-types'

function rowsFrom(round: RoundResponse): RoundDraftRow[] {
  return [...round.matches].sort((a, b) => a.display_order - b.display_order).map(match => ({
    match_id: match.id,
    games_a: match.games_a === null ? '' : String(match.games_a) as ScoreInput,
    games_b: match.games_b === null ? '' : String(match.games_b) as ScoreInput,
  }))
}

function initialState(round: RoundResponse) {
  return { baseline: round, rows: rowsFrom(round), errors: {} as RoundDraftState['errors'] }
}

export function useRoundDraft(round: RoundResponse): RoundDraftState {
  const [state, setState] = useState(() => initialState(round))
  // Same-round refreshes cannot replace an in-progress edit. Saves call accept explicitly.
  if (state.baseline.event_id !== round.event_id || state.baseline.number !== round.number) {
    setState(initialState(round))
  }
  const baselineRows = rowsFrom(state.baseline)
  const dirty = state.rows.length !== baselineRows.length || state.rows.some(row => {
    const saved = baselineRows.find(value => value.match_id === row.match_id)
    return !saved || row.match_id !== saved.match_id || row.games_a !== saved.games_a || row.games_b !== saved.games_b
  })

  const setScore = useCallback((matchId: number, side: Side, value: ScoreInput) => {
    if (!/^[0-9]?$/.test(value)) return
    setState(current => {
      if (current.baseline.read_only || current.baseline.locked || !['groups', 'review'].includes(current.baseline.state)) return current
      const errors = { ...current.errors, [matchId]: { ...current.errors[matchId], [side]: undefined } }
      return {
        ...current, errors,
        rows: current.rows.map(row => row.match_id === matchId ? { ...row, [side === 'a' ? 'games_a' : 'games_b']: value } : row),
      }
    })
  }, [])

  const validate = useCallback((): SaveRoundRequest | null => {
    if (state.baseline.read_only || state.baseline.locked || !['groups', 'review'].includes(state.baseline.state)) return null
    const errors: RoundDraftState['errors'] = {}
    for (const row of state.rows) {
      for (const side of ['a', 'b'] as const) {
        if (!/^[0-9]$/.test(row[side === 'a' ? 'games_a' : 'games_b'])) {
          errors[row.match_id] = { ...errors[row.match_id], [side]: 'Completá los games (0 a 9).' }
        }
      }
    }
    setState(current => ({ ...current, errors }))
    if (Object.keys(errors).length || state.rows.length === 0) return null
    return {
      expected_revision: state.baseline.revision,
      results: state.rows.map(row => ({
        match_id: row.match_id,
        games_a: Number(row.games_a) as GroupGames,
        games_b: Number(row.games_b) as GroupGames,
      })),
    }
  }, [state])

  const reset = useCallback(() => setState(current => initialState(current.baseline)), [])
  const accept = useCallback((canonical: RoundResponse) => setState(initialState(canonical)), [])
  const rebase = useCallback((canonical: RoundResponse) => setState(current => ({
    baseline: canonical,
    rows: rowsFrom(canonical).map(saved => current.rows.find(row => row.match_id === saved.match_id) ?? saved),
    errors: {},
  })), [])
  return { rows: state.rows, dirty, errors: state.errors, setScore, validate, reset, accept, rebase }
}
