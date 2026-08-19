import { useState } from 'react'

import type { PollResults, PollState, ZonePick } from '../api/predictions'
import { formatDeadline, usePollResults } from '../api/predictions'
import type { Team, Zone } from '../api/types'
import { PredictionModal } from './PredictionModal'
import { TeamAvatar } from './parts'

/** How many pairs of each zone the podium shows. */
const PODIUM = 3

/**
 * The call to vote on the season, on the home page.
 *
 * Three shapes for the same block: an invitation while the poll runs, a
 * receipt with the closing date once this device has answered, and nothing at
 * all when there is no poll. Painted with the palette tokens, so it belongs to
 * whichever theme is on.
 */
export function PredictionBanner({
  poll,
  zones,
  teams,
  onSubmit,
}: {
  poll: PollState | null
  zones: Zone[]
  teams: Team[]
  onSubmit: (picks: ZonePick[]) => Promise<void>
}) {
  const [open, setOpen] = useState(false)
  // A closed poll is the only time the counts exist, and the only time the API
  // will hand them over.
  const results = usePollResults(Boolean(poll && !poll.open && poll.closes_at))

  // No poll ever run is not an empty state worth announcing.
  if (!poll?.closes_at || zones.length === 0) return null

  // Closed: the whole point was seeing what everyone said.
  if (!poll.open) {
    if (!results) return null
    return <ClosedPoll results={results} zones={zones} teams={teams} />
  }

  const deadline = formatDeadline(poll.closes_at)

  return (
    <section className="container-page py-[clamp(20px,4vw,36px)]">
      <div
        className="card relative overflow-hidden p-[clamp(20px,4vw,32px)]"
        style={{
          borderColor: 'color-mix(in srgb, var(--color-accent) 45%, var(--color-rule))',
          background:
            'linear-gradient(135deg, color-mix(in srgb, var(--color-accent) 12%, transparent), transparent 60%)',
        }}
      >
        <p
          className="mb-2 text-[10px] font-semibold tracking-widest uppercase"
          style={{ color: 'var(--color-accent)' }}
        >
          {poll.voted ? 'Tu pronóstico' : 'Pronóstico de la temporada'}
        </p>

        <h2 className="display mb-2 text-[clamp(22px,4.5vw,36px)]">
          {poll.voted ? '¡Ya votaste!' : '¿Quiénes pasan directo a cuartos?'}
        </h2>

        <p
          className="mb-5 max-w-[52ch] text-[clamp(14px,1.8vw,16px)] leading-relaxed"
          style={{ color: 'var(--color-fg-muted)' }}
        >
          {poll.voted ? (
            <>
              Tu pronóstico quedó guardado.
              {deadline && (
                <>
                  {' '}
                  La votación cierra el{' '}
                  <strong style={{ color: 'var(--color-fg)' }}>{deadline}</strong>, y ahí se
                  revelan los resultados.
                </>
              )}
            </>
          ) : (
            <>
              Votá quiénes salen primero y segundo en cada zona.
              {deadline && (
                <>
                  {' '}
                  Tenés tiempo hasta el{' '}
                  <strong style={{ color: 'var(--color-fg)' }}>{deadline}</strong>.
                </>
              )}
            </>
          )}
        </p>

        <button
          type="button"
          onClick={() => setOpen(true)}
          className="display rounded px-6 py-3 text-sm transition-transform hover:-translate-y-0.5"
          style={{
            backgroundColor: poll.voted ? 'transparent' : 'var(--color-accent)',
            color: poll.voted ? 'var(--color-accent)' : 'var(--color-on-accent)',
            border: poll.voted ? '1px solid var(--color-accent)' : '1px solid transparent',
          }}
        >
          {poll.voted ? 'Cambiar mi pronóstico' : '¡Votar!'}
        </button>
      </div>

      {open && (
        <PredictionModal
          zones={zones}
          teams={teams}
          closesAt={poll.closes_at}
          onSubmit={onSubmit}
          onClose={() => setOpen(false)}
        />
      )}
    </section>
  )
}

/**
 * What everyone predicted, once the poll has closed.
 *
 * Replaces the invitation in the same slot. Without this the banner simply
 * vanished when the week ran out, and the answer people voted for was only
 * ever visible inside the admin panel.
 */
function ClosedPoll({
  results,
  zones,
  teams,
}: {
  results: PollResults
  zones: Zone[]
  teams: Team[]
}) {
  // Nobody voted: better to show nothing than an empty podium.
  if (results.voters === 0) return null

  const teamOf = (teamId: number) => teams.find((team) => team.id === teamId)

  return (
    <section className="container-page py-[clamp(20px,4vw,36px)]">
      <div
        className="card overflow-hidden p-[clamp(20px,4vw,32px)]"
        style={{
          borderColor: 'color-mix(in srgb, var(--color-accent) 45%, var(--color-rule))',
          background:
            'linear-gradient(135deg, color-mix(in srgb, var(--color-accent) 12%, transparent), transparent 60%)',
        }}
      >
        <p
          className="mb-2 text-[10px] font-semibold tracking-widest uppercase"
          style={{ color: 'var(--color-accent)' }}
        >
          Pronóstico de la temporada
        </p>

        <h2 className="display mb-2 text-[clamp(22px,4.5vw,36px)]">Esto dijo la gente</h2>

        <p className="mb-6 text-sm" style={{ color: 'var(--color-fg-muted)' }}>
          La votación cerró. {results.voters}{' '}
          {results.voters === 1 ? 'persona votó' : 'personas votaron'} quiénes pasan directo a
          cuartos.
        </p>

        <div className="grid gap-6 sm:grid-cols-2">
          {results.zones.map((zone) => (
            <div key={zone.zone_id}>
              <h3
                className="mb-3 text-[11px] font-semibold tracking-widest uppercase"
                style={{ color: 'var(--color-fg-muted)' }}
              >
                {zones.find((option) => option.id === zone.zone_id)?.name ?? '—'}
              </h3>

              <ol className="grid gap-2">
                {zone.teams.slice(0, PODIUM).map((entry, index) => {
                  const team = teamOf(entry.team_id)
                  const leader = index === 0
                  return (
                    <li
                      key={entry.team_id}
                      className="card flex items-center gap-2.5 px-3 py-2"
                      style={{
                        borderColor: leader ? 'var(--color-accent)' : 'var(--color-rule)',
                        backgroundColor: leader
                          ? 'color-mix(in srgb, var(--color-accent) 10%, transparent)'
                          : 'transparent',
                      }}
                    >
                      <span
                        className="display grid h-6 w-6 flex-none place-items-center rounded-full text-[11px]"
                        style={{
                          backgroundColor: leader ? 'var(--color-accent)' : 'transparent',
                          color: leader ? 'var(--color-on-accent)' : 'var(--color-fg-muted)',
                          border: leader ? 'none' : '1px solid var(--color-rule)',
                        }}
                      >
                        {index + 1}
                      </span>

                      <TeamAvatar team={team} size={28} />

                      <span className="min-w-0 flex-1 truncate text-sm">
                        {team ? `${team.player_one_name} / ${team.player_two_name}` : '—'}
                      </span>

                      <span
                        className="flex-none text-[11px] tabular-nums"
                        style={{ color: 'var(--color-fg-muted)' }}
                        title={`${entry.first_votes} para primero, ${entry.second_votes} para segundo`}
                      >
                        {entry.first_votes} · {entry.second_votes}
                      </span>
                    </li>
                  )
                })}
              </ol>
            </div>
          ))}
        </div>

        <p className="mt-4 text-[11px]" style={{ color: 'var(--color-fg-muted)' }}>
          Los números son los votos para primero y para segundo.
        </p>
      </div>
    </section>
  )
}
