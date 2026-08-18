import { useEffect, useMemo, useState } from 'react'

import type { Match, Team, Zone } from '../api/types'
import { useResource } from '../api/useResource'
import { MatchDetail } from './MatchDetail'
import { Notice, PageTitle, Pagination, ZoneTabs } from './parts'

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
                <MatchDetail interactive match={match} teamsById={teamsById} zones={zones.data ?? []} />
              </li>
            ))}
          </ul>

          <Pagination page={page} pages={pages} onChange={setPage} />
        </>
      )}
    </div>
  )
}
