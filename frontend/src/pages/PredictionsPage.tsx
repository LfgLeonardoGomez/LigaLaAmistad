import { useState } from 'react'

import { api } from '../api/client'
import type { PollResults, PollState } from '../api/predictions'
import { formatDeadline } from '../api/predictions'
import type { Team, Zone } from '../api/types'
import { useResource } from '../api/useResource'
import { Button } from '../components/ui'

const DEFAULT_DAYS = 7

/**
 * Opening and closing the season poll, and reading it once it is closed.
 *
 * Deliberately two buttons and no date picker: the only decision is when it
 * starts, and a week from now is the answer every time.
 */
export function PredictionsPage() {
  const poll = useResource<PollState>('/public/predictions')
  const zones = useResource<Zone[]>('/public/zones')
  const teams = useResource<Team[]>('/public/teams')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const act = async (path: string, body?: unknown) => {
    setBusy(true)
    setError(null)
    try {
      await api.post(path, body ?? {})
      poll.reload()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Error inesperado')
    } finally {
      setBusy(false)
    }
  }

  if (poll.loading) return <p className="text-sm text-ink-500">Cargando…</p>

  const state = poll.data
  const deadline = formatDeadline(state?.closes_at ?? null)
  const started = Boolean(state?.closes_at)

  return (
    <div className="max-w-3xl">
      <h1 className="mb-1 text-xl font-semibold text-ink-900">Encuesta de la temporada</h1>
      <p className="mb-6 text-sm text-ink-500">
        Los visitantes votan quiénes salen primero y segundo en cada zona. Los resultados
        quedan ocultos hasta que la votación cierra.
      </p>

      {error && (
        <p className="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      <div className="rounded-lg border border-ink-200 bg-surface p-4">
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <span
            className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
              state?.open
                ? 'bg-emerald-50 text-emerald-700'
                : 'bg-ink-100 text-ink-500'
            }`}
          >
            {state?.open ? 'Abierta' : started ? 'Cerrada' : 'Sin iniciar'}
          </span>
          {deadline && (
            <span className="text-sm text-ink-500">
              {state?.open ? 'Cierra el' : 'Cerró el'} {deadline}
            </span>
          )}
        </div>

        <div className="flex flex-wrap gap-2">
          <Button onClick={() => void act('/admin/predictions/open', { days: DEFAULT_DAYS })} disabled={busy}>
            {started ? 'Abrir una nueva (7 días)' : 'Abrir la votación (7 días)'}
          </Button>
          {state?.open && (
            <Button
              variant="secondary"
              onClick={() => void act('/admin/predictions/close')}
              disabled={busy}
            >
              Cerrar ahora
            </Button>
          )}
        </div>

        {state?.open && (
          <p className="mt-3 text-xs text-ink-500">
            Abrir una nueva empieza de cero: los pronósticos de la anterior quedan guardados
            pero dejan de contar.
          </p>
        )}
      </div>

      {started && !state?.open && (
        <Results zones={zones.data ?? []} teams={teams.data ?? []} />
      )}
    </div>
  )
}

function Results({ zones, teams }: { zones: Zone[]; teams: Team[] }) {
  const results = useResource<PollResults>('/public/predictions/results')

  if (results.loading) return null
  if (results.error) return <p className="mt-6 text-sm text-ink-500">{results.error}</p>
  if (!results.data) return null

  const nameOf = (teamId: number) => {
    const team = teams.find((option) => option.id === teamId)
    return team ? `${team.player_one_name} / ${team.player_two_name}` : `#${teamId}`
  }

  return (
    <div className="mt-6">
      <h2 className="mb-1 text-lg font-semibold text-ink-900">Resultados</h2>
      <p className="mb-4 text-sm text-ink-500">
        {results.data.voters} {results.data.voters === 1 ? 'persona votó' : 'personas votaron'}.
        Un primer puesto vale 2 puntos y un segundo, 1.
      </p>

      {results.data.zones.map((zone) => (
        <div key={zone.zone_id} className="mb-6">
          <h3 className="mb-2 text-sm font-semibold text-ink-700">
            {zones.find((option) => option.id === zone.zone_id)?.name ?? `Zona ${zone.zone_id}`}
          </h3>

          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-ink-200 text-left text-xs text-ink-500">
                <th className="py-2">Pareja</th>
                <th className="py-2 text-right">1°</th>
                <th className="py-2 text-right">2°</th>
                <th className="py-2 text-right">Puntos</th>
              </tr>
            </thead>
            <tbody>
              {zone.teams.map((team) => (
                <tr key={team.team_id} className="border-b border-ink-100">
                  <td className="py-2 text-ink-900">{nameOf(team.team_id)}</td>
                  <td className="py-2 text-right tabular-nums text-ink-500">{team.first_votes}</td>
                  <td className="py-2 text-right tabular-nums text-ink-500">{team.second_votes}</td>
                  <td className="py-2 text-right font-semibold tabular-nums text-ink-900">
                    {team.points}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  )
}
