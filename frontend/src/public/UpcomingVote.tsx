import { useState } from 'react'

import type { Team } from '../api/types'
import type { VoteTally } from '../api/votes'
import { TeamAvatar } from './parts'

/**
 * The two pairs of a fixture, as the two things you tap.
 *
 * The card used to list the pairs and then repeat both names on a pair of
 * buttons underneath. Same names twice, twice the reading. Here the pair *is*
 * the button: photo, names, and the share of the vote once there is one.
 */
export function UpcomingVote({
  tally,
  teamA,
  teamB,
  onVote,
}: {
  tally: VoteTally | undefined
  teamA: Team | undefined
  teamB: Team | undefined
  onVote: (teamId: number) => Promise<void>
}) {
  const [sending, setSending] = useState(false)
  const [failed, setFailed] = useState(false)

  if (!teamA || !teamB) return null

  const voted = tally?.voted_team_id != null

  // Rounding one side and taking the remainder is what keeps the two at 100.
  const total = tally?.total ?? 0
  const percentA = total === 0 ? 0 : Math.round(((tally?.team_a_votes ?? 0) / total) * 100)
  const percentB = total === 0 ? 0 : 100 - percentA

  const cast = async (teamId: number) => {
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

  return (
    <div className="mt-3">
      <div className="mb-2 flex items-baseline justify-between gap-2">
        <p
          className="text-[10px] font-semibold tracking-widest uppercase"
          style={{ color: 'var(--color-fg-muted)' }}
        >
          {voted ? 'Tu voto' : '¿Quién gana?'}
        </p>
        {voted && (
          <span className="text-[10px]" style={{ color: 'var(--color-fg-muted)' }}>
            {total} {total === 1 ? 'voto' : 'votos'}
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-2">
        <PairButton
          team={teamA}
          percent={percentA}
          mine={tally?.voted_team_id === teamA.id}
          showPercent={voted}
          disabled={sending}
          onClick={() => void cast(teamA.id)}
        />
        <PairButton
          team={teamB}
          percent={percentB}
          mine={tally?.voted_team_id === teamB.id}
          showPercent={voted}
          disabled={sending}
          onClick={() => void cast(teamB.id)}
        />
      </div>

      {failed && (
        <p className="mt-2 text-[11px]" style={{ color: 'var(--color-hot)' }}>
          No se pudo registrar el voto. Probá de nuevo.
        </p>
      )}
    </div>
  )
}

function PairButton({
  team,
  percent,
  mine,
  showPercent,
  disabled,
  onClick,
}: {
  team: Team
  percent: number
  mine: boolean
  showPercent: boolean
  disabled: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-pressed={mine}
      className="card card-hover flex flex-col items-center gap-2 p-3 text-center disabled:opacity-60"
      style={{
        borderColor: mine ? 'var(--color-accent)' : 'var(--color-rule)',
        backgroundColor: mine
          ? 'color-mix(in srgb, var(--color-accent) 10%, transparent)'
          : 'transparent',
      }}
    >
      <TeamAvatar team={team} size={64} />

      <span className="min-w-0 text-[13px] leading-tight">
        <span className="block truncate">{team.player_one_name}</span>
        <span className="block truncate">{team.player_two_name}</span>
      </span>

      {showPercent && (
        <span className="w-full">
          <span
            className="block text-sm font-semibold tabular-nums"
            style={{ color: mine ? 'var(--color-accent)' : 'var(--color-fg)' }}
          >
            {percent}%
          </span>
          <span
            className="mt-1 block h-1.5 overflow-hidden rounded-full"
            style={{ backgroundColor: 'color-mix(in srgb, var(--color-rule) 70%, transparent)' }}
          >
            <span
              className="block h-full rounded-full transition-[width] duration-300"
              style={{
                width: `${percent}%`,
                backgroundColor: mine ? 'var(--color-accent)' : 'var(--color-fg-muted)',
              }}
            />
          </span>
        </span>
      )}
    </button>
  )
}
