import { useState } from 'react'

import type { Team, Zone } from '../api/types'
import { useResource } from '../api/useResource'
import { Notice, PageTitle, ZoneTabs } from './parts'

export function PublicTeamsPage() {
  const zones = useResource<Zone[]>('/public/zones')
  const [zoneId, setZoneId] = useState<number | null>(null)
  const teams = useResource<Team[]>(
    zoneId === null ? '/public/teams' : `/public/teams?zone_id=${zoneId}`,
  )

  const zoneName = (id: number) => zones.data?.find((zone) => zone.id === id)?.name ?? ''
  const count = teams.data?.length ?? 0

  return (
    <div className="container-page">
      <PageTitle
        title="Las parejas"
        lead="Dos zonas. La zona se asigna al inicio y no cambia durante la temporada."
      />

      <div className="mb-6 flex flex-wrap items-center gap-4">
        <ZoneTabs zones={zones.data ?? []} selected={zoneId} onSelect={setZoneId} />
        {!teams.loading && (
          <span
            className="text-[11px] font-semibold tracking-widest uppercase"
            style={{ color: 'var(--color-fg-muted)' }}
          >
            {count} {count === 1 ? 'pareja' : 'parejas'}
          </span>
        )}
      </div>

      {teams.loading ? (
        <Notice>Cargando parejas…</Notice>
      ) : teams.error ? (
        <Notice tone="hot">{teams.error}</Notice>
      ) : count === 0 ? (
        <Notice>Todavía no hay parejas inscriptas en esta zona.</Notice>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {/* min-w-0: a grid item will not shrink below its content otherwise,
              and a long pair of names would push the page sideways. */}
          {teams.data?.map((team) => (
            <li key={team.id} className="min-w-0">
              <TeamCard team={team} zoneName={zoneName(team.zone_id)} />
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function TeamCard({ team, zoneName }: { team: Team; zoneName: string }) {
  return (
    <article className="card card-hover h-full">
      <Photo team={team} />

      <div className="p-4">
        <div
          className="mb-2 text-[11px] font-semibold tracking-widest uppercase"
          style={{ color: 'var(--color-fg-muted)' }}
        >
          {zoneName}
        </div>
        <p className="display text-[17px] leading-tight">{team.player_one_name}</p>
        <p className="display text-[17px] leading-tight" style={{ color: 'var(--color-fg-muted)' }}>
          {team.player_two_name}
        </p>

        {/* A withdrawn pair keeps its place and its points, so it is marked, not hidden. */}
        {team.status === 'withdrawn' && (
          <span
            className="mt-2 inline-block text-[10px] font-bold tracking-widest uppercase"
            style={{ color: 'var(--color-hot)' }}
          >
            Dada de baja
          </span>
        )}
      </div>
    </article>
  )
}

function Photo({ team }: { team: Team }) {
  if (team.photo_url) {
    return (
      <img
        src={team.photo_url}
        alt={`${team.player_one_name} y ${team.player_two_name}`}
        loading="lazy"
        className="aspect-4/3 w-full object-cover"
        style={{ borderBottom: '1px solid var(--color-rule)' }}
      />
    )
  }

  // photo_url is nullable and will be for most of the season, so the empty
  // state is the common case and has to look deliberate.
  return (
    <div
      aria-hidden="true"
      className="grid aspect-4/3 w-full place-items-center"
      style={{
        borderBottom: '1px solid var(--color-rule)',
        color: 'var(--color-fg-muted)',
        backgroundImage:
          'repeating-linear-gradient(45deg, transparent, transparent 7px, var(--color-rule) 7px, var(--color-rule) 8px)',
      }}
    >
      <span className="px-3 py-1 font-mono text-xs" style={{ backgroundColor: 'var(--color-canvas)' }}>
        foto de la pareja
      </span>
    </div>
  )
}
