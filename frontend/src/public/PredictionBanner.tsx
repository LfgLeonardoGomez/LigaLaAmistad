import { useState } from 'react'

import type { PollState, ZonePick } from '../api/predictions'
import { formatDeadline } from '../api/predictions'
import type { Team, Zone } from '../api/types'
import { PredictionModal } from './PredictionModal'

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

  // No poll running is not an empty state worth announcing.
  if (!poll?.open || zones.length === 0) return null

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
