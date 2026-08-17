import { useMemo, useState } from 'react'

import type { Standing, Team, Zone } from '../api/types'
import { teamName } from '../api/types'
import { useResource } from '../api/useResource'
import { Notice, PageTitle } from './parts'

export function PublicStandingsPage() {
  const zones = useResource<Zone[]>('/public/zones')
  const teams = useResource<Team[]>('/public/teams')
  const [zoneId, setZoneId] = useState<number | null>(null)

  const selected = zoneId ?? zones.data?.[0]?.id ?? null
  const standings = useResource<Standing[]>(
    selected === null ? null : `/public/standings?zone_id=${selected}`,
  )

  const teamsById = useMemo(
    () => new Map((teams.data ?? []).map((team) => [team.id, team])),
    [teams.data],
  )

  return (
    <>
      <PageTitle
        title="Tabla"
        lead="Se calcula sola con cada resultado que se carga. Ganar 2-0 suma 3 puntos, ganar 2-1 suma 2, y perder 1-2 suma 1."
      />

      <div role="group" aria-label="Elegir zona" className="mb-6 flex flex-wrap gap-2">
        {(zones.data ?? []).map((zone) => {
          const active = selected === zone.id
          return (
            <button
              key={zone.id}
              type="button"
              onClick={() => setZoneId(zone.id)}
              aria-pressed={active}
              className="display rounded px-4 py-2 text-xs transition-colors"
              style={{
                backgroundColor: active ? 'var(--color-accent)' : 'transparent',
                color: active ? 'var(--color-on-accent)' : 'var(--color-fg-muted)',
                border: `1px solid ${active ? 'var(--color-accent)' : 'var(--color-rule)'}`,
              }}
            >
              {zone.name}
            </button>
          )
        })}
      </div>

      {standings.loading ? (
        <Notice>Cargando tabla…</Notice>
      ) : standings.error ? (
        <Notice tone="hot">{standings.error}</Notice>
      ) : !standings.data?.length ? (
        <Notice>Esta zona todavía no tiene parejas.</Notice>
      ) : (
        <div className="overflow-x-auto" style={{ border: '1px solid var(--color-rule)' }}>
          <table className="w-full min-w-[520px] text-sm">
            <caption className="sr-only">
              Tabla de posiciones, ordenada por puntos, diferencia de sets y diferencia de games
            </caption>
            <thead>
              <tr
                className="text-[11px] font-semibold tracking-widest uppercase"
                style={{ color: 'var(--color-fg-muted)', borderBottom: '1px solid var(--color-rule)' }}
              >
                <th scope="col" className="w-12 px-3 py-3 text-left">
                  #
                </th>
                <th scope="col" className="px-3 py-3 text-left">
                  Pareja
                </th>
                <th scope="col" className="px-3 py-3 text-center">PJ</th>
                <th scope="col" className="px-3 py-3 text-center">PG</th>
                <th scope="col" className="px-3 py-3 text-center">PP</th>
                <th scope="col" className="px-3 py-3 text-center">Dif. sets</th>
                <th scope="col" className="px-3 py-3 text-center">Pts</th>
              </tr>
            </thead>
            <tbody>
              {/* The order comes from the API: it includes a tie-break cascade
                  this page does not know about. Never re-sort it here. */}
              {standings.data.map((row) => {
                const team = teamsById.get(row.team_id)
                const podium = row.position <= 3
                return (
                  <tr key={row.team_id} style={{ borderTop: '1px solid var(--color-rule)' }}>
                    <td
                      className="px-3 py-3 font-semibold tabular-nums"
                      style={{ color: podium ? 'var(--color-accent)' : 'var(--color-fg-muted)' }}
                    >
                      {row.position}
                    </td>
                    <td className="px-3 py-3 font-semibold">
                      {teamName(team)}
                      {team?.status === 'withdrawn' && (
                        <span className="ml-2 text-xs font-normal" style={{ color: 'var(--color-fg-muted)' }}>
                          dada de baja
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-3 text-center tabular-nums" style={{ color: 'var(--color-fg-muted)' }}>
                      {row.played}
                    </td>
                    <td className="px-3 py-3 text-center tabular-nums" style={{ color: 'var(--color-fg-muted)' }}>
                      {row.won}
                    </td>
                    <td className="px-3 py-3 text-center tabular-nums" style={{ color: 'var(--color-fg-muted)' }}>
                      {row.lost}
                    </td>
                    <td className="px-3 py-3 text-center tabular-nums" style={{ color: 'var(--color-fg-muted)' }}>
                      {row.sets_diff > 0 ? `+${row.sets_diff}` : row.sets_diff}
                    </td>
                    <td className="px-3 py-3 text-center font-bold tabular-nums">{row.points}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
