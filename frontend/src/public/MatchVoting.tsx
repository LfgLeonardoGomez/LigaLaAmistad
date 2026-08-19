import { useState } from 'react'

import type { VoteTally } from '../api/votes'
import type { Team } from '../api/types'

/** A pair's name, short enough for a button. */
function nameOf(team: Team | undefined): string {
  return team ? `${team.player_one_name} / ${team.player_two_name}` : '—'
}

/**
 * "¿Quién gana?" on a match card.
 *
 * Three states in one component, because they are the same three numbers seen
 * at different moments:
 *
 *  - open and not voted  → two buttons
 *  - open and voted      → the split, with the pick marked and changeable
 *  - closed              → the split, plus whether the public called it right
 */
export function MatchVoting({
  tally,
  teamA,
  teamB,
  winnerTeamId,
  onVote,
}: {
  tally: VoteTally | undefined
  teamA: Team | undefined
  teamB: Team | undefined
  winnerTeamId?: number | null
  /** Absent where voting is not offered, such as a finished match. */
  onVote?: (teamId: number) => Promise<void>
}) {
  const [sending, setSending] = useState(false)
  const [failed, setFailed] = useState(false)

  // No tally means the counts never arrived. The card is still a card.
  if (!tally || !teamA || !teamB) return null

  const closed = !tally.open
  const voted = tally.voted_team_id !== null

  // Nothing to say about a finished match nobody voted on.
  if (closed && tally.total === 0) return null

  const cast = async (teamId: number) => {
    if (!onVote) return
    setSending(true)
    setFailed(false)
    try {
      await onVote(teamId)
    } catch {
      setFailed(true)
    } finally {
      setSending(false)
    }
  }

  // An open match nobody can vote on has nothing to show yet.
  if (!closed && !voted && !onVote) return null

  if (!closed && !voted) {
    return (
      <div className="mt-3 border-t pt-3" style={{ borderColor: 'var(--color-rule)' }}>
        <p
          className="mb-2 text-[10px] font-semibold tracking-widest uppercase"
          style={{ color: 'var(--color-fg-muted)' }}
        >
          ¿Quién gana?
        </p>

        <div className="grid gap-2 sm:grid-cols-2">
          {[teamA, teamB].map((team) => (
            <button
              key={team.id}
              type="button"
              disabled={sending}
              onClick={() => void cast(team.id)}
              className="truncate rounded border px-2.5 py-2 text-xs transition-colors disabled:opacity-50"
              style={{ borderColor: 'var(--color-rule)', color: 'var(--color-fg)' }}
            >
              {nameOf(team)}
            </button>
          ))}
        </div>

        {failed && (
          <p className="mt-2 text-[11px]" style={{ color: 'var(--color-hot)' }}>
            No se pudo registrar el voto. Probá de nuevo.
          </p>
        )}
      </div>
    )
  }

  // Rounding one side and taking the remainder guarantees the two read as 100,
  // which rounding both separately does not (33 + 67 is luck, not arithmetic).
  const percentA = tally.total === 0 ? 0 : Math.round((tally.team_a_votes / tally.total) * 100)
  const percentB = tally.total === 0 ? 0 : 100 - percentA

  const favouriteId =
    tally.team_a_votes === tally.team_b_votes
      ? null
      : tally.team_a_votes > tally.team_b_votes
        ? teamA.id
        : teamB.id

  return (
    <div className="mt-3 border-t pt-3" style={{ borderColor: 'var(--color-rule)' }}>
      <div className="mb-2 flex items-baseline justify-between gap-2">
        <p
          className="text-[10px] font-semibold tracking-widest uppercase"
          style={{ color: 'var(--color-fg-muted)' }}
        >
          {closed ? 'La gente dijo' : 'Tu voto'}
        </p>
        <span className="text-[10px]" style={{ color: 'var(--color-fg-muted)' }}>
          {tally.total} {tally.total === 1 ? 'voto' : 'votos'}
        </span>
      </div>

      <Bar team={teamA} percent={percentA} mine={tally.voted_team_id === teamA.id} />
      <Bar team={teamB} percent={percentB} mine={tally.voted_team_id === teamB.id} />

      {closed && winnerTeamId != null && favouriteId != null && (
        <p className="mt-2 text-[11px]" style={{ color: 'var(--color-fg-muted)' }}>
          {favouriteId === winnerTeamId ? 'La gente le acertó.' : 'La gente se equivocó.'}
        </p>
      )}

      {!closed && onVote && (
        <button
          type="button"
          disabled={sending}
          onClick={() => void cast(tally.voted_team_id === teamA.id ? teamB.id : teamA.id)}
          className="mt-2 text-[11px] underline transition-opacity hover:opacity-70 disabled:opacity-50"
          style={{ color: 'var(--color-fg-muted)' }}
        >
          Cambiar mi voto
        </button>
      )}
    </div>
  )
}

function Bar({
  team,
  percent,
  mine,
}: {
  team: Team | undefined
  percent: number
  mine: boolean
}) {
  return (
    <div className="py-1">
      <div className="mb-1 flex items-baseline justify-between gap-2 text-[11px]">
        <span className="min-w-0 truncate" style={{ color: mine ? 'var(--color-fg)' : 'var(--color-fg-muted)' }}>
          {nameOf(team)}
          {mine && ' ·  tu voto'}
        </span>
        <span className="flex-none font-semibold tabular-nums" style={{ color: 'var(--color-fg)' }}>
          {percent}%
        </span>
      </div>

      <div
        className="h-1.5 overflow-hidden rounded-full"
        style={{ backgroundColor: 'color-mix(in srgb, var(--color-rule) 70%, transparent)' }}
      >
        <div
          className="h-full rounded-full transition-[width] duration-300"
          style={{
            width: `${percent}%`,
            backgroundColor: mine ? 'var(--color-accent)' : 'var(--color-fg-muted)',
          }}
        />
      </div>
    </div>
  )
}
