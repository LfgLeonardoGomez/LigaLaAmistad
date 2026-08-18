import { useEffect, useMemo, useState } from 'react'

import type { Match, Team, Zone } from '../api/types'
import { useResource } from '../api/useResource'
import { Notice, PageTitle, Pagination, TeamAvatar, ZoneTabs, formatDate } from './parts'
import { imageUrl } from '../api/images'

const PER_PAGE = 20

export function PublicResultsPage() {
  const zones = useResource<Zone[]>('/public/zones')
  const teams = useResource<Team[]>('/public/teams')
  const [zoneId, setZoneId] = useState<number | null>(null)
  const [page, setPage] = useState(1)

  // /public/matches already returns played matches only; pending ones never arrive.
  const matches = useResource<Match[]>(
    zoneId === null ? '/public/matches' : `/public/matches?zone_id=${zoneId}`,
  )

  const teamsById = useMemo(
    () => new Map((teams.data ?? []).map((team) => [team.id, team])),
    [teams.data],
  )

  const newestFirst = useMemo(() => [...(matches.data ?? [])].reverse(), [matches.data])
  const pages = Math.max(1, Math.ceil(newestFirst.length / PER_PAGE))

  // Changing the zone can leave you on a page that no longer exists.
  useEffect(() => setPage(1), [zoneId])

  const visible = newestFirst.slice((page - 1) * PER_PAGE, page * PER_PAGE)

  return (
    <div className="container-page">
      <PageTitle title="Resultados" lead="Partidos ya jugados, del más reciente al más viejo." />

      <div className="mb-6 flex flex-wrap items-center gap-4">
        <ZoneTabs zones={zones.data ?? []} selected={zoneId} onSelect={setZoneId} />
        {!matches.loading && newestFirst.length > 0 && (
          <span
            className="text-[11px] font-semibold tracking-widest uppercase"
            style={{ color: 'var(--color-fg-muted)' }}
          >
            {newestFirst.length} partidos
          </span>
        )}
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
        <>
          <ul className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {/* min-w-0: a grid item will not shrink below its content, and a
                long pair of names would push the page sideways on a phone. */}
            {visible.map((match) => (
              <li key={match.id} className="min-w-0">
                <ResultCard match={match} teamsById={teamsById} zones={zones.data ?? []} />
              </li>
            ))}
          </ul>

          <Pagination page={page} pages={pages} onChange={setPage} />
        </>
      )}
    </div>
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
    <article className="card card-hover h-full">
      <header
        className="flex items-center justify-between gap-3 px-3 py-2 text-[10px] font-semibold tracking-widest uppercase"
        style={{ borderBottom: '1px solid var(--color-rule)', color: 'var(--color-fg-muted)' }}
      >
        <span>{zoneName ?? '—'}</span>
        <time dateTime={match.date}>{formatDate(match.date)}</time>
      </header>

      <div className="px-3 py-2">
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

      {/* Both are optional and most matches have neither, so each one renders
          nothing at all rather than an empty slot: a card without them has to
          look exactly like it did before the feature existed. */}
      {match.photo_url && (
        <img
          src={imageUrl(match.photo_url, { width: 600 })}
          alt=""
          loading="lazy"
          className="block aspect-[4/3] w-full object-cover"
          style={{ borderTop: '1px solid var(--color-rule)' }}
        />
      )}

      {match.comment && (
        <p
          className="px-3 py-2.5 text-[13px] leading-relaxed break-words text-pretty"
          style={{ borderTop: '1px solid var(--color-rule)', color: 'var(--color-fg)' }}
        >
          {match.comment}
        </p>
      )}
    </article>
  )
}

function Side({ team, won, games }: { team: Team | undefined; won: boolean; games: number[] }) {
  return (
    <div className="flex items-center gap-2.5 py-1.5">
      <TeamAvatar team={team} size={26} />

      <p
        className="min-w-0 flex-1 truncate text-sm"
        style={{
          color: won ? 'var(--color-fg)' : 'var(--color-fg-muted)',
          fontWeight: won ? 700 : 400,
        }}
        title={team ? `${team.player_one_name} / ${team.player_two_name}` : undefined}
      >
        {team ? `${team.player_one_name} / ${team.player_two_name}` : '—'}
      </p>

      {/* One box per set, so both rows line up column by column. */}
      <div className="flex flex-none gap-1">
        {games.map((value, index) => (
          <span
            key={index}
            className="grid h-7 w-7 place-items-center rounded text-[13px] font-semibold tabular-nums"
            style={{
              border: '1px solid var(--color-rule)',
              backgroundColor: won ? 'color-mix(in srgb, var(--color-accent) 12%, transparent)' : 'transparent',
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
