import { useMemo, useState } from 'react'

import type { ZonePick } from '../api/predictions'
import { formatDeadline } from '../api/predictions'
import type { Team, Zone } from '../api/types'
import { PublicModal, TeamAvatar } from './parts'

/** The picks made so far in one zone, in the order they were tapped. */
type Picks = number[]

/**
 * The ballot: first and second place of every zone, one zone per step.
 *
 * Tapping a pair adds it, tapping it again takes it back. Two taps fill a
 * zone, which is the whole interaction — no dragging, no ordering controls,
 * nothing that needs a mouse.
 */
export function PredictionModal({
  zones,
  teams,
  closesAt,
  onSubmit,
  onClose,
}: {
  zones: Zone[]
  teams: Team[]
  closesAt: string | null
  onSubmit: (picks: ZonePick[]) => Promise<void>
  onClose: () => void
}) {
  const [step, setStep] = useState(0)
  const [byZone, setByZone] = useState<Record<number, Picks>>({})
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  const zone = zones[step]
  const picks = (zone && byZone[zone.id]) || []

  const inZone = useMemo(
    () => teams.filter((team) => team.zone_id === zone?.id),
    [teams, zone?.id],
  )

  const toggle = (teamId: number) => {
    if (!zone) return
    setByZone((previous) => {
      const current = previous[zone.id] ?? []
      const next = current.includes(teamId)
        ? current.filter((id) => id !== teamId)
        : current.length < 2
          ? [...current, teamId]
          : current
      return { ...previous, [zone.id]: next }
    })
  }

  const complete = zones.every((option) => (byZone[option.id] ?? []).length === 2)
  const last = step === zones.length - 1

  const send = async () => {
    // Built one zone at a time rather than mapped: the button is disabled
    // while anything is missing, but nothing in the types says so, and a
    // half-filled ballot must never reach the API.
    const ballot: ZonePick[] = []
    for (const option of zones) {
      const [first, second] = byZone[option.id] ?? []
      if (first === undefined || second === undefined) return
      ballot.push({ zone_id: option.id, first_team_id: first, second_team_id: second })
    }

    setSending(true)
    setError(null)
    try {
      await onSubmit(ballot)
      setDone(true)
    } catch {
      setError('No se pudo guardar tu pronóstico. Probá de nuevo.')
    } finally {
      setSending(false)
    }
  }

  if (done) {
    const deadline = formatDeadline(closesAt)
    return (
      <PublicModal title="Pronóstico guardado" onClose={onClose}>
        <div className="p-4 text-center">
          <p className="display mb-3 text-[clamp(20px,4vw,30px)]">¡Listo!</p>
          <p className="text-sm" style={{ color: 'var(--color-fg-muted)' }}>
            Ya quedó tu pronóstico.
            {deadline && (
              <>
                {' '}
                La votación cierra el{' '}
                <strong style={{ color: 'var(--color-accent)' }}>{deadline}</strong> y ahí se
                revelan los resultados.
              </>
            )}
          </p>
          <p className="mt-3 text-xs" style={{ color: 'var(--color-fg-muted)' }}>
            Podés cambiarlo hasta esa fecha.
          </p>

          <button
            type="button"
            onClick={onClose}
            className="display mt-5 rounded px-5 py-2.5 text-sm"
            style={{
              backgroundColor: 'var(--color-accent)',
              color: 'var(--color-on-accent)',
            }}
          >
            Cerrar
          </button>
        </div>
      </PublicModal>
    )
  }

  return (
    <PublicModal title="Pronóstico" onClose={onClose}>
      <div className="p-4">
        <p
          className="mb-1 text-[10px] font-semibold tracking-widest uppercase"
          style={{ color: 'var(--color-fg-muted)' }}
        >
          Paso {step + 1} de {zones.length} · {zone?.name}
        </p>
        <h3 className="display mb-1 text-[clamp(17px,3vw,22px)]">
          ¿Quiénes salen 1° y 2° en {zone?.name}?
        </h3>
        <p className="mb-4 text-xs" style={{ color: 'var(--color-fg-muted)' }}>
          {picks.length === 0
            ? 'Tocá a la pareja que sale primera.'
            : picks.length === 1
              ? 'Ahora tocá a la que sale segunda.'
              : 'Listo. Tocá de nuevo para cambiar.'}
        </p>

        <ul className="grid gap-2 sm:grid-cols-2">
          {inZone.map((team) => {
            const place = picks.indexOf(team.id)
            const chosen = place !== -1
            return (
              <li key={team.id} className="min-w-0">
                <button
                  type="button"
                  onClick={() => toggle(team.id)}
                  aria-pressed={chosen}
                  className="card flex w-full items-center gap-2.5 px-3 py-2.5 text-left transition-colors"
                  style={{ borderColor: chosen ? 'var(--color-accent)' : 'var(--color-rule)' }}
                >
                  <TeamAvatar team={team} size={28} />
                  <span className="min-w-0 flex-1 truncate text-sm">
                    {team.player_one_name} / {team.player_two_name}
                  </span>
                  {chosen && (
                    <span
                      className="display grid h-6 w-6 flex-none place-items-center rounded-full text-[11px]"
                      style={{
                        backgroundColor: 'var(--color-accent)',
                        color: 'var(--color-on-accent)',
                      }}
                    >
                      {place + 1}
                    </span>
                  )}
                </button>
              </li>
            )
          })}
        </ul>

        {error && (
          <p className="mt-3 text-sm" style={{ color: 'var(--color-hot)' }}>
            {error}
          </p>
        )}

        <div className="mt-5 flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => (step === 0 ? onClose() : setStep(step - 1))}
            className="text-sm transition-opacity hover:opacity-70"
            style={{ color: 'var(--color-fg-muted)' }}
          >
            {step === 0 ? 'Cancelar' : '← Anterior'}
          </button>

          <button
            type="button"
            disabled={picks.length < 2 || sending || (last && !complete)}
            onClick={() => (last ? void send() : setStep(step + 1))}
            className="display rounded px-5 py-2.5 text-sm disabled:opacity-40"
            style={{
              backgroundColor: 'var(--color-accent)',
              color: 'var(--color-on-accent)',
            }}
          >
            {last ? (sending ? 'Guardando…' : 'Enviar') : 'Siguiente'}
          </button>
        </div>
      </div>
    </PublicModal>
  )
}
