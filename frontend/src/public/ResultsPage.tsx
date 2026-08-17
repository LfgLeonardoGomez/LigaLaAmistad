import { useMemo, useState } from 'react'

import type { Match, Team, Zone } from '../api/types'
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
      <PageTitle title="Resultados" lead="Partidos ya jugados, del más reciente al más viejo." />

      <div className="mb-6">
        <ZoneTabs zones={zones.data ?? []} selected={zoneId} onSelect={setZoneId} />
      </div>

      {matches.loading ? (
        <Notice>Cargando resultados…</Notice>
      ) : matches.error ? (
        <Notice tone="hot">{matches.error}</Notice>
      ) : newestFirst.length === 0 ? (
        <Notice>
          Todavía no se jugó ningún partido. Cuando se cargue el primer resultado, aparece acá.
        </Notice>
      ) : (
        // flex-col and not grid: a grid item defaults to min-width:auto, so the
        // card refuses to shrink below its content and the page scrolls
        // sideways on a phone.
        <ul className="flex flex-col gap-4">
          {newestFirst.map((match) => (
            <li key={match.id} className="min-w-0">
              <ResultCard match={match} teamsById={teamsById} zones={zones.data ?? []} />
            </li>
          ))}
        </ul>
      )}
    </>
  )
}

function ResultCard({
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
    <article style={{ border: '1px solid var(--color-rule)' }}>
      <header
        className="flex items-center justify-between gap-3 px-4 py-2.5 text-[11px] font-semibold tracking-widest uppercase"
        style={{ borderBottom: '1px solid var(--color-rule)', color: 'var(--color-fg-muted)' }}
      >
        <span>{zoneName ?? '—'}</span>
        <time dateTime={match.date}>{formatDate(match.date)}</time>
      </header>

      <div className="p-4">
        <Side
          team={teamA}
          won={match.winner_team_id === match.team_a_id}
          games={match.sets.map((set) => set.team_a_games)}
        />
        <Side
          team={teamB}
          won={match.winner_team_id === match.team_b_id}
          games={match.sets.map((set) => set.team_b_games)}
        />
      </div>
    </article>
  )
}

function Side({
  team,
  won,
  games,
}: {
  team: Team | undefined
  won: boolean
  games: number[]
}) {
  return (
    <div className="flex items-center gap-3 py-2">
      <Avatar team={team} />

      <div className="min-w-0 flex-1">
        <p
          className="truncate font-semibold"
          style={{ color: won ? 'var(--color-fg)' : 'var(--color-fg-muted)' }}
        >
          {team ? `${team.player_one_name} / ${team.player_two_name}` : '—'}
        </p>
        {won && (
          <p
            className="text-[10px] font-bold tracking-widest uppercase"
            style={{ color: 'var(--color-accent)' }}
          >
            Ganador
          </p>
        )}
      </div>

      {/* One box per set, so the two rows line up column by column. */}
      <div className="flex flex-none gap-1.5">
        {games.map((value, index) => (
          <span
            key={index}
            className="grid h-8 w-8 place-items-center text-sm font-semibold tabular-nums"
            style={{
              border: '1px solid var(--color-rule)',
              color: won ? 'var(--color-fg)' : 'var(--color-fg-muted)',
            }}
          >
            {value}
          </span>
        ))}
      </div>
    </div>
  )
}

function Avatar({ team }: { team: Team | undefined }) {
  if (team?.photo_url) {
    return (
      <img
        src={team.photo_url}
        alt=""
        loading="lazy"
        className="h-9 w-9 flex-none rounded-full object-cover"
        style={{ border: '1px solid var(--color-rule)' }}
      />
    )
  }

  return (
    <span
      aria-hidden="true"
      className="h-9 w-9 flex-none rounded-full"
      style={{
        border: '1px solid var(--color-rule)',
        backgroundImage:
          'repeating-linear-gradient(45deg, transparent, transparent 4px, var(--color-rule) 4px, var(--color-rule) 5px)',
      }}
    />
  )
}
