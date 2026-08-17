import { useMemo, useState } from 'react'

import type { Match, Team, Zone } from '../api/types'
import { teamName } from '../api/types'
import { useResource } from '../api/useResource'
import { Notice, PageTitle, ZoneTabs, formatDate } from './parts'

export function PublicResultsPage() {
  const zones = useResource<Zone[]>('/public/zones')
  const teams = useResource<Team[]>('/public/teams')
  const [zoneId, setZoneId] = useState<number | null>(null)

  // /public/matches already returns played matches only; pending ones never arrive.
  const matches = useResource<Match[]>(
    zoneId === null ? '/public/matches' : `/public/matches?zone_id=${zoneId}`,
  )

  const teamsById = useMemo(
    () => new Map((teams.data ?? []).map((team) => [team.id, team])),
    [teams.data],
  )

  const newestFirst = useMemo(() => [...(matches.data ?? [])].reverse(), [matches.data])

  return (
    <>
      <PageTitle
        title="Resultados"
        lead="Todos los partidos que ya se jugaron, del más reciente al más viejo. El ganador sale de los sets."
      />

      <ZoneTabs zones={zones.data ?? []} selected={zoneId} onSelect={setZoneId} />

      {matches.loading ? (
        <Notice>Cargando resultados…</Notice>
      ) : matches.error ? (
        <Notice tone="hot">{matches.error}</Notice>
      ) : newestFirst.length === 0 ? (
        <Notice>
          Todavía no se jugó ningún partido. Cuando se cargue el primer resultado, aparece acá.
        </Notice>
      ) : (
        <ul className="grid gap-3">
          {newestFirst.map((match) => (
            <li key={match.id}>
              <ResultRow
                match={match}
                teamsById={teamsById}
                zones={zones.data ?? []}
              />
            </li>
          ))}
        </ul>
      )}
    </>
  )
}

function ResultRow({
  match,
  teamsById,
  zones,
}: {
  match: Match
  teamsById: Map<number, Team>
  zones: Zone[]
}) {
  const teamA = teamsById.get(match.team_a_id)
  const teamB = teamsById.get(match.team_b_id)
  // A match stores no zone. It is the zone of its teams, which always match.
  const zoneName = zones.find((zone) => zone.id === teamA?.zone_id)?.name

  return (
    <article
      className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:gap-6"
      style={{ border: '1px solid var(--color-rule)' }}
    >
      <div
        className="flex items-center gap-3 text-[11px] font-semibold tracking-widest uppercase sm:w-32 sm:flex-none sm:flex-col sm:items-start sm:gap-1"
        style={{ color: 'var(--color-fg-muted)' }}
      >
        <span>{zoneName ?? '—'}</span>
        <time dateTime={match.date}>{formatDate(match.date)}</time>
      </div>

      <div className="min-w-0 flex-1">
        <Side team={teamA} won={match.winner_team_id === match.team_a_id} />
        <Side team={teamB} won={match.winner_team_id === match.team_b_id} />
      </div>

      <div className="flex flex-none gap-2 font-mono text-sm tabular-nums">
        {match.sets.map((set) => (
          <span
            key={set.set_number}
            className="rounded px-2 py-1"
            style={{ border: '1px solid var(--color-rule)' }}
          >
            {set.team_a_games}-{set.team_b_games}
          </span>
        ))}
      </div>
    </article>
  )
}

function Side({ team, won }: { team: Team | undefined; won: boolean }) {
  return (
    <div className="flex items-center gap-2 py-0.5">
      <span
        className="truncate"
        style={{
          color: won ? 'var(--color-fg)' : 'var(--color-fg-muted)',
          fontWeight: won ? 700 : 400,
        }}
      >
        {teamName(team)}
      </span>
      {won && (
        <span
          className="flex-none rounded px-1.5 py-0.5 text-[10px] font-bold tracking-wider uppercase"
          style={{ backgroundColor: 'var(--color-accent)', color: 'var(--color-on-accent)' }}
        >
          Ganó
        </span>
      )}
    </div>
  )
}
