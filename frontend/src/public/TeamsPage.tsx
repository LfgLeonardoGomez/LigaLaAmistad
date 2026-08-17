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

  return (
    <>
      <PageTitle
        title="Parejas"
        lead="Las parejas que juegan la liga, repartidas en dos zonas. Cada una juega todos contra todos dentro de su zona."
      />

      <ZoneTabs zones={zones.data ?? []} selected={zoneId} onSelect={setZoneId} />

      {teams.loading ? (
        <Notice>Cargando parejas…</Notice>
      ) : teams.error ? (
        <Notice tone="hot">{teams.error}</Notice>
      ) : !teams.data?.length ? (
        <Notice>Todavía no hay parejas inscriptas en esta zona.</Notice>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {teams.data.map((team) => (
            <li key={team.id}>
              <TeamCard team={team} zoneName={zoneName(team.zone_id)} />
            </li>
          ))}
        </ul>
      )}
    </>
  )
}

function TeamCard({ team, zoneName }: { team: Team; zoneName: string }) {
  return (
    <article className="flex items-center gap-4 p-4" style={{ border: '1px solid var(--color-rule)' }}>
      <Photo team={team} />

      <div className="min-w-0 flex-1">
        <div
          className="mb-1 text-[11px] font-semibold tracking-widest uppercase"
          style={{ color: 'var(--color-fg-muted)' }}
        >
          {zoneName}
        </div>
        <p className="truncate font-semibold">{team.player_one_name}</p>
        <p className="truncate font-semibold">{team.player_two_name}</p>

        {/* A withdrawn pair keeps its place and its points, so it is marked, not hidden. */}
        {team.status === 'withdrawn' && (
          <span
            className="mt-2 inline-block rounded px-2 py-0.5 text-[10px] font-bold tracking-wider uppercase"
            style={{ border: '1px solid var(--color-rule)', color: 'var(--color-fg-muted)' }}
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
        className="h-16 w-16 flex-none rounded-full object-cover"
        style={{ border: '2px solid var(--color-accent)' }}
      />
    )
  }

  // photo_url is nullable, so the empty case needs to look intentional.
  return (
    <span
      aria-hidden="true"
      className="display grid h-16 w-16 flex-none place-items-center rounded-full text-lg"
      style={{ border: '2px solid var(--color-rule)', color: 'var(--color-fg-muted)' }}
    >
      {team.player_one_name.charAt(0)}
      {team.player_two_name.charAt(0)}
    </span>
  )
}
