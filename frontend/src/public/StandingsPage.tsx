import { useMemo, useState } from 'react'

import type { Standing, Team, Zone } from '../api/types'
import { useResource } from '../api/useResource'
import { Notice, PageTitle, TeamAvatar } from './parts'

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
      <PageTitle title="Posiciones" lead="Se actualiza automáticamente con cada resultado cargado." />

      <div role="group" aria-label="Elegir zona" className="mb-6 grid gap-3 sm:grid-cols-2">
        {(zones.data ?? []).map((zone) => {
          const active = selected === zone.id
          return (
            <button
              key={zone.id}
              type="button"
              onClick={() => setZoneId(zone.id)}
              aria-pressed={active}
              className="display px-4 py-3.5 text-sm transition-colors"
              style={{
                border: '1px solid var(--color-rule)',
                borderBottom: `2px solid ${active ? 'var(--color-accent)' : 'var(--color-rule)'}`,
                color: active ? 'var(--color-fg)' : 'var(--color-fg-muted)',
              }}
            >
              {zone.name}
            </button>
          )
        })}
      </div>

      {standings.loading ? (
        <Notice>Cargando posiciones…</Notice>
      ) : standings.error ? (
        <Notice tone="hot">{standings.error}</Notice>
      ) : !standings.data?.length ? (
        <Notice>Esta zona todavía no tiene parejas.</Notice>
      ) : (
        <>
          <div className="overflow-x-auto" style={{ border: '1px solid var(--color-rule)' }}>
            <table className="w-full min-w-[560px] text-sm">
              <caption className="sr-only">
                Tabla de posiciones de la zona seleccionada
              </caption>
              <thead>
                <tr
                  className="text-[11px] font-semibold tracking-widest uppercase"
                  style={{
                    color: 'var(--color-fg-muted)',
                    borderBottom: '1px solid var(--color-rule)',
                  }}
                >
                  <th scope="col" className="w-12 px-4 py-3 text-left">#</th>
                  <th scope="col" className="px-2 py-3 text-left">Pareja</th>
                  <th scope="col" className="w-14 px-2 py-3 text-center">PJ</th>
                  <th scope="col" className="w-14 px-2 py-3 text-center">PG</th>
                  <th scope="col" className="w-14 px-2 py-3 text-center">PP</th>
                  <th scope="col" className="w-16 px-2 py-3 text-center">Dif</th>
                  <th scope="col" className="w-16 px-4 py-3 text-center">Pts</th>
                </tr>
              </thead>
              <tbody>
                {/* The order comes from the API: it carries a tie-break cascade
                    this page does not know about. Never re-sort it here. */}
                {standings.data.map((row) => {
                  const team = teamsById.get(row.team_id)
                  const podium = row.position <= 3
                  return (
                    <tr key={row.team_id} style={{ borderTop: '1px solid var(--color-rule)' }}>
                      <td
                        className="display px-4 py-4 text-base"
                        style={{ color: podium ? 'var(--color-accent)' : 'var(--color-fg-muted)' }}
                      >
                        {row.position}
                      </td>
                      <td className="px-2 py-4">
                        <div className="flex items-center gap-3">
                          <TeamAvatar team={team} size={34} />
                          <div className="min-w-0">
                            <div className="truncate font-semibold">
                              {team?.player_one_name ?? '—'}
                            </div>
                            <div className="truncate" style={{ color: 'var(--color-fg-muted)' }}>
                              {team?.player_two_name ?? ''}
                            </div>
                            {team?.status === 'withdrawn' && (
                              <div
                                className="mt-1 text-[10px] font-bold tracking-widest uppercase"
                                style={{ color: 'var(--color-hot)' }}
                              >
                                Dada de baja
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                      <Cell>{row.played}</Cell>
                      <Cell>{row.won}</Cell>
                      <Cell>{row.lost}</Cell>
                      <Cell>{row.sets_diff > 0 ? `+${row.sets_diff}` : row.sets_diff}</Cell>
                      <td
                        className="display px-4 py-4 text-center text-lg tabular-nums"
                        style={{ color: 'var(--color-accent)' }}
                      >
                        {row.points}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          <div className="mt-4 space-y-1 text-xs" style={{ color: 'var(--color-fg-muted)' }}>
            <p>PJ jugados · PG ganados · PP perdidos · Dif diferencia de sets · Pts puntos.</p>
            <p>El orden lo define la organización con los criterios de desempate de la liga.</p>
          </div>
        </>
      )}
    </>
  )
}

function Cell({ children }: { children: React.ReactNode }) {
  return (
    <td className="px-2 py-4 text-center tabular-nums" style={{ color: 'var(--color-fg-muted)' }}>
      {children}
    </td>
  )
}
