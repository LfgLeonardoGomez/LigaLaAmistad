import { useCallback, useEffect, useState } from 'react'

import { api } from './client'
import { voterKey } from './votes'

export interface ZonePick {
  zone_id: number
  first_team_id: number
  second_team_id: number
}

export interface PollState {
  open: boolean
  opens_at: string | null
  closes_at: string | null
  voted: boolean
  zones: ZonePick[]
}

export interface TeamResult {
  team_id: number
  first_votes: number
  second_votes: number
  points: number
}

export interface PollResults {
  closes_at: string
  voters: number
  zones: { zone_id: number; teams: TeamResult[] }[]
}

/** The closing date, written the way the site writes dates. */
export function formatDeadline(iso: string | null): string | null {
  if (!iso) return null
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return null

  return date.toLocaleDateString('es-AR', {
    day: 'numeric',
    month: 'long',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * The season poll as this device sees it: whether it is running, and what it
 * already answered.
 */
export function usePoll() {
  const [state, setState] = useState<PollState | null>(null)

  useEffect(() => {
    let cancelled = false
    api
      .get<PollState>(`/public/predictions?voter_key=${voterKey()}`)
      .then((result) => {
        if (!cancelled) setState(result)
      })
      // A home page must render whether or not there is a poll running.
      .catch(() => undefined)

    return () => {
      cancelled = true
    }
  }, [])

  const submit = useCallback(async (zones: ZonePick[]) => {
    const result = await api.post<PollState>('/public/predictions', {
      voter_key: voterKey(),
      zones,
    })
    setState(result)
  }, [])

  return { state, submit }
}
