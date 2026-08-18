import { useMemo, useState } from 'react'

import type { Standing, Team, Zone } from '../api/types'
import { teamName } from '../api/types'
import { useResource } from '../api/useResource'
import {
  Alert,
  Card,
  EmptyState,
  PageHeader,
  Spinner,
  Table,
  Td,
  Th,
} from '../components/ui'

export function StandingsPage() {
  const zones = useResource<Zone[]>('/public/zones')
  const teams = useResource<Team[]>('/admin/teams')
  const [zoneId, setZoneId] = useState<number | null>(null)

  // Until the zones arrive there is no zone to ask about, so the request is
  // held back rather than aimed at a placeholder endpoint.
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
      <PageHeader
        title="Tabla de posiciones"
        description="Se calcula al vuelo desde los partidos jugados. Corregir un resultado la actualiza sola."
      />

      <div className="mb-4 flex gap-1">
        {(zones.data ?? []).map((zone) => (
          <button
            key={zone.id}
            type="button"
            onClick={() => setZoneId(zone.id)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              selected === zone.id ? 'bg-ink-900 text-surface' : 'text-ink-600 hover:bg-ink-200'
            }`}
          >
            {zone.name}
          </button>
        ))}
      </div>

      {standings.error && (
        <div className="mb-4">
          <Alert>{standings.error}</Alert>
        </div>
      )}

      <Card>
        {standings.loading ? (
          <Spinner />
        ) : !standings.data?.length ? (
          <EmptyState>Esta zona todavía no tiene parejas.</EmptyState>
        ) : (
          <Table
            head={
              <tr>
                <Th className="w-12">#</Th>
                <Th>Pareja</Th>
                <Th className="text-center">PJ</Th>
                <Th className="text-center">G</Th>
                <Th className="text-center">P</Th>
                <Th className="text-center">Sets</Th>
                <Th className="text-center">Dif. sets</Th>
                <Th className="text-center">Dif. games</Th>
                <Th className="text-center">Prom.</Th>
                <Th className="text-center">Pts</Th>
              </tr>
            }
          >
            {standings.data.map((row) => {
              const team = teamsById.get(row.team_id)
              return (
                <tr key={row.team_id} className="hover:bg-ink-50">
                  <Td className="font-medium text-ink-400">{row.position}</Td>
                  <Td>
                    <span className="font-medium text-ink-900">{teamName(team)}</span>
                    {team?.status === 'withdrawn' && (
                      <span className="ml-2 text-xs text-ink-400">dada de baja</span>
                    )}
                  </Td>
                  <Td className="text-center text-ink-600">{row.played}</Td>
                  <Td className="text-center text-ink-600">{row.won}</Td>
                  <Td className="text-center text-ink-600">{row.lost}</Td>
                  <Td className="text-center text-ink-600">
                    {row.sets_won}-{row.sets_lost}
                  </Td>
                  <Td className="text-center text-ink-600">{signed(row.sets_diff)}</Td>
                  <Td className="text-center text-ink-600">{signed(row.games_diff)}</Td>
                  <Td className="text-center text-ink-500">{row.points_average.toFixed(2)}</Td>
                  <Td className="text-center font-semibold text-ink-900">{row.points}</Td>
                </tr>
              )
            })}
          </Table>
        )}
      </Card>
    </>
  )
}

function signed(value: number): string {
  return value > 0 ? `+${value}` : String(value)
}
