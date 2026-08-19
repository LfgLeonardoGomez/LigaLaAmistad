import { useMemo, useState } from 'react'

import type { Match, Team, Zone } from '../api/types'
import { formatTime, venueLabel } from '../api/types'
import { useResource } from '../api/useResource'
import { Notice, PageTitle, TeamAvatar, formatDate } from './parts'

/** What is known about one pairing inside a zone. */
interface Fixture {
  rival: Team
  match: Match | null
}

export function PublicFixturesPage() {
  const zones = useResource<Zone[]>('/public/zones')
  const [zoneId, setZoneId] = useState<number | null>(null)
  const [teamId, setTeamId] = useState<number | null>(null)

  // Nothing is asked for until a zone is chosen, so the first screen costs one
  // request instead of four.
  const teams = useResource<Team[]>(zoneId === null ? null : `/public/teams?zone_id=${zoneId}`)
  const played = useResource<Match[]>(zoneId === null ? null : `/public/matches?zone_id=${zoneId}`)
  const scheduled = useResource<Match[]>(
    zoneId === null ? null : `/public/matches?status=pending&zone_id=${zoneId}`,
  )

  const team = teams.data?.find((t) => t.id === teamId) ?? null

  const fixtures = useMemo<Fixture[]>(() => {
    if (!team || !teams.data) return []

    const rivalOf = (match: Match) =>
      match.team_a_id === team.id ? match.team_b_id : match.team_a_id
    const involves = (match: Match) =>
      match.team_a_id === team.id || match.team_b_id === team.id

    const byRival = new Map<number, Match>()
    for (const match of [...(played.data ?? []), ...(scheduled.data ?? [])]) {
      if (involves(match)) byRival.set(rivalOf(match), match)
    }

    // Everyone else in the zone is a fixture, whether or not a match exists for
    // it yet. That absence is the answer to "who do we still have to arrange
    // with", which is the question this page was built for.
    return teams.data
      .filter((other) => other.id !== team.id)
      .map((rival) => ({ rival, match: byRival.get(rival.id) ?? null }))
  }, [team, teams.data, played.data, scheduled.data])

  const done = fixtures.filter((f) => f.match?.status === 'played')
  const booked = fixtures.filter((f) => f.match?.status === 'pending')
  const unarranged = fixtures.filter((f) => f.match === null)

  const loading = teams.loading || played.loading || scheduled.loading

  return (
    <div className="container-page">
      <PageTitle
        title="Cruces"
        lead="Quién ya jugó contra quién dentro de cada zona, y qué falta arreglar."
      />

      <Step number={1} title="Elegí una zona" />
      <div className="mb-8 grid gap-3 sm:grid-cols-2">
        {(zones.data ?? []).map((option) => {
          const active = zoneId === option.id
          return (
            <button
              key={option.id}
              type="button"
              onClick={() => {
                setZoneId(option.id)
                setTeamId(null)
              }}
              aria-pressed={active}
              className="display card px-4 py-6 text-lg transition-colors"
              style={{
                backgroundColor: active ? 'var(--color-accent)' : 'transparent',
                color: active ? 'var(--color-on-accent)' : 'var(--color-fg)',
                borderColor: active ? 'var(--color-accent)' : 'var(--color-rule)',
              }}
            >
              {option.name}
            </button>
          )
        })}
      </div>

      {zoneId !== null && (
        <>
          <Step number={2} title="Elegí una pareja para ver sus cruces" />
          {loading ? (
            <Notice>Cargando…</Notice>
          ) : (
            <ul className="mb-8 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {(teams.data ?? []).map((option) => {
                const active = teamId === option.id
                return (
                  <li key={option.id} className="min-w-0">
                    <button
                      type="button"
                      onClick={() => setTeamId(option.id)}
                      aria-pressed={active}
                      className="card card-hover flex w-full items-center gap-3 px-3 py-2.5 text-left"
                      style={{
                        borderColor: active ? 'var(--color-accent)' : 'var(--color-rule)',
                      }}
                    >
                      <TeamAvatar team={option} size={30} />
                      <span className="min-w-0 flex-1 truncate text-sm">
                        {option.player_one_name} / {option.player_two_name}
                      </span>
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </>
      )}

      {team && (
        <section>
          <Step number={3} title={`${team.player_one_name} / ${team.player_two_name}`} />

          <div className="grid gap-6">
            <Group
              title="Ya jugaron"
              empty="Todavía no jugaron ningún partido."
              fixtures={done}
              team={team}
            />
            <Group
              title="Programados"
              empty="No tienen ningún partido con fecha."
              fixtures={booked}
              team={team}
            />
            <Group
              title="Falta acordar"
              empty="Ya está todo el fixture arreglado."
              fixtures={unarranged}
              team={team}
            />
          </div>
        </section>
      )}
    </div>
  )
}

function Step({ number, title }: { number: number; title: string }) {
  return (
    <div className="mb-4 flex items-baseline gap-3">
      <span className="display text-sm" style={{ color: 'var(--color-accent)' }}>
        {number}
      </span>
      <h2 className="display text-[clamp(16px,2.5vw,22px)]">{title}</h2>
    </div>
  )
}

function Group({
  title,
  empty,
  fixtures,
  team,
}: {
  title: string
  empty: string
  fixtures: Fixture[]
  team: Team
}) {
  return (
    <div>
      <h3
        className="mb-2 text-[11px] font-semibold tracking-widest uppercase"
        style={{ color: 'var(--color-fg-muted)' }}
      >
        {title} ({fixtures.length})
      </h3>

      {fixtures.length === 0 ? (
        <p className="text-sm" style={{ color: 'var(--color-fg-muted)' }}>
          {empty}
        </p>
      ) : (
        <ul className="grid gap-2">
          {fixtures.map(({ rival, match }) => (
            <li key={rival.id}>
              <FixtureRow rival={rival} match={match} team={team} />
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function FixtureRow({ rival, match, team }: { rival: Team; match: Match | null; team: Team }) {
  const setsWonBy = (teamId: number) =>
    (match?.sets ?? []).filter((set) =>
      teamId === match?.team_a_id
        ? set.team_a_games > set.team_b_games
        : set.team_b_games > set.team_a_games,
    ).length

  const won = match?.winner_team_id === team.id
  const schedule = match
    ? [formatDate(match.date), formatTime(match.time), venueLabel(match.venue)]
        .filter(Boolean)
        .join(' · ')
    : null

  return (
    <div className="card flex items-center gap-3 px-3 py-2.5">
      <TeamAvatar team={rival} size={26} />

      <span className="min-w-0 flex-1 truncate text-sm">
        {rival.player_one_name} / {rival.player_two_name}
      </span>

      {match?.status === 'played' ? (
        <span className="flex flex-none items-center gap-2">
          <span
            className="text-[10px] font-bold tracking-wider uppercase"
            style={{ color: won ? 'var(--color-accent)' : 'var(--color-fg-muted)' }}
          >
            {won ? 'Ganaron' : 'Perdieron'}
          </span>
          <span className="text-sm font-semibold tabular-nums">
            {setsWonBy(team.id)}-{setsWonBy(rival.id)}
          </span>
        </span>
      ) : (
        <span
          className="flex-none text-right text-[11px]"
          style={{ color: 'var(--color-fg-muted)' }}
        >
          {schedule ?? 'Sin fecha'}
        </span>
      )}
    </div>
  )
}
