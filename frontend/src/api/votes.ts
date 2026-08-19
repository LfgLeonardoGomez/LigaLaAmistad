import { useCallback, useEffect, useState } from 'react'

import { api } from './client'

export interface VoteTally {
  match_id: number
  team_a_votes: number
  team_b_votes: number
  total: number
  /** What this device picked, or null if it has not voted. */
  voted_team_id: number | null
  /** Whether the match still accepts votes. */
  open: boolean
}

const STORAGE_KEY = 'liga:voter-key'

/** Kept for the session when localStorage is unavailable (private browsing,
    storage disabled). Voting still works; it just will not survive a reload. */
let fallbackKey: string | null = null

/**
 * A key that identifies this browser and nothing else.
 *
 * Not a person and not an account: it is a random value the browser makes up
 * so the API can tell one vote from fifty by the same visitor. Whoever clears
 * their storage gets a new one and may vote again, and that is a deliberate
 * trade — asking people to register in order to guess a padel result would
 * cost more than the stuffing it prevents.
 */
export function voterKey(): string {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) return stored

    const created = crypto.randomUUID()
    localStorage.setItem(STORAGE_KEY, created)
    return created
  } catch {
    fallbackKey ??= crypto.randomUUID()
    return fallbackKey
  }
}

/**
 * Vote counts for a set of matches, and the way to add one.
 *
 * Asks for every match on the page in a single request, because the home
 * shows six cards and the results list twenty, and one call each would be
 * twenty calls.
 */
export function useMatchVotes(matchIds: number[]) {
  // The ids are joined into the dependency so the effect re-runs when the page
  // changes matches, and not on every render because the array is new.
  const ids = matchIds.join(',')
  const [tallies, setTallies] = useState<Map<number, VoteTally>>(new Map())

  useEffect(() => {
    if (!ids) {
      setTallies(new Map())
      return
    }

    let cancelled = false
    api
      .get<VoteTally[]>(`/public/matches/votes?ids=${ids}&voter_key=${voterKey()}`)
      .then((rows) => {
        if (cancelled) return
        setTallies(new Map(rows.map((row) => [row.match_id, row])))
      })
      // The tally is decoration on a page that has to render anyway, so a
      // failure here leaves the cards without the bar instead of breaking them.
      .catch(() => undefined)

    return () => {
      cancelled = true
    }
  }, [ids])

  const vote = useCallback(async (matchId: number, teamId: number) => {
    const row = await api.post<VoteTally>(`/public/matches/${matchId}/votes`, {
      team_id: teamId,
      voter_key: voterKey(),
    })
    // The answer carries the new counts, which is what "updates in real time"
    // means here: no polling, no sockets, the numbers come back with the vote.
    setTallies((previous) => new Map(previous).set(matchId, row))
  }, [])

  return { tallies, vote }
}
