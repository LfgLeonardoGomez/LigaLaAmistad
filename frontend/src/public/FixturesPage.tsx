import { useEffect, useMemo, useRef, useState } from 'react'

import type { Match, Team, Zone } from '../api/types'
import { formatTime, venueLabel } from '../api/types'
import { useResource } from '../api/useResource'
import { Notice, PageTitle, TeamAvatar, formatDate } from './parts'

/** What is known about one pairing inside a zone. */
interface Fixture {
  rival: Team
  match: Match | null
}

type Step = 'zone' | 'team' | 'detail'

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

  const zone = zones.data?.find((z) => z.id === zoneId) ?? null
  const team = teams.data?.find((t) => t.id === teamId) ?? null

  // One step at a time, each replacing the one before. Stacked, the answer
  // landed below the fold and a reader who did not scroll thought the tap had
  // done nothing.
  const step: Step = zoneId === null ? 'zone' : team === null ? 'team' : 'detail'

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

  const heading =
    step === 'zone'
      ? 'Elegí una zona'
      : step === 'team'
        ? `Elegí una pareja de ${zone?.name ?? ''}`.trimEnd()
        : `${team?.player_one_name} / ${team?.player_two_name}`

  // Focus follows the step so the change is announced to a screen reader and
  // the keyboard caret lands on the new content. Skipped on first paint: a
  // page that steals focus on load is worse than one that never moves it.
  const headingRef = useRef<HTMLHeadingElement>(null)
  const mounted = useRef(false)
  useEffect(() => {
    if (!mounted.current) {
      mounted.current = true
      return
    }
    headingRef.current?.focus()
  }, [step])

  const loading = teams.loading || played.loading || scheduled.loading

  return (
    <div className="container-page">
      <PageTitle
        title="Cruces"
        lead="Quién ya jugó contra quién dentro de cada zona, y qué falta arreglar."
      />

      {step !== 'zone' && (
        <BackButton
          label={step === 'team' ? 'Volver a las zonas' : `Volver a ${zone?.name ?? 'la zona'}`}
          onClick={() => {
            // Going back to the zones clears the pair too. Keeping it meant
            // re-picking the same zone jumped straight past the pair list.
            if (step === 'team') setZoneId(null)
            setTeamId(null)
          }}
        />
      )}

      <div className="mb-4 flex items-baseline gap-3">
        <span className="display text-sm" style={{ color: 'var(--color-accent)' }}>
          {step === 'zone' ? 1 : step === 'team' ? 2 : 3}
        </span>
        <h2
          ref={headingRef}
          tabIndex={-1}
          className="display text-[clamp(16px,2.5vw,22px)] outline-none"
        >
          {heading}
        </h2>
      </div>

      {step === 'zone' && (
        <div className="grid gap-3 sm:grid-cols-2">
          {(zones.data ?? []).map((option) => (
            <button
              key={option.id}
              type="button"
              onClick={() => setZoneId(option.id)}
              className="display card card-hover px-4 py-6 text-lg"
              style={{ color: 'var(--color-fg)' }}
            >
              {option.name}
            </button>
          ))}
        </div>
      )}

      {step === 'team' &&
        (loading ? (
          <Notice>Cargando…</Notice>
        ) : (
          <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {(teams.data ?? []).map((option) => (
              <li key={option.id} className="min-w-0">
                <button
                  type="button"
                  onClick={() => setTeamId(option.id)}
                  className="card card-hover flex w-full items-center gap-3 px-3 py-2.5 text-left"
                >
                  <TeamAvatar team={option} size={30} />
                  <span className="min-w-0 flex-1 truncate text-sm">
                    {option.player_one_name} / {option.player_two_name}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        ))}

      {step === 'detail' && team && (
        <div className="grid gap-6">
          <Group
            title="Ya jugaron"
            empty="Todavía no jugaron ningún partido."
            fixtures={fixtures.filter((f) => f.match?.status === 'played')}
            team={team}
          />
          <Group
            title="Programados"
            empty="No tienen ningún partido con fecha."
            fixtures={fixtures.filter((f) => f.match?.status === 'pending')}
            team={team}
          />
          <Group
            title="Falta acordar"
            empty="Ya está todo el fixture arreglado."
            fixtures={fixtures.filter((f) => f.match === null)}
            team={team}
          />
        </div>
      )}
    </div>
  )
}

function BackButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="mb-4 inline-flex items-center gap-1.5 text-sm transition-opacity hover:opacity-70"
      style={{ color: 'var(--color-fg-muted)' }}
    >
      <span aria-hidden="true">←</span>
      {label}
    </button>
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
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {fixtures.map(({ rival, match }) => (
            <li key={rival.id} className="min-w-0">
              <FixtureCard rival={rival} match={match} team={team} />
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function FixtureCard({ rival, match, team }: { rival: Team; match: Match | null; team: Team }) {
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
    <div className="card flex h-full flex-col gap-3 p-3">
      <div className="flex items-center gap-2.5">
        <TeamAvatar team={rival} size={38} />
        {/* Un nombre por renglon: en una tarjeta angosta "Fulano / Mengano"
            se truncaba justo donde importa. */}
        <span className="min-w-0 flex-1 text-sm leading-tight">
          <span className="block truncate">{rival.player_one_name}</span>
          <span className="block truncate">{rival.player_two_name}</span>
        </span>
      </div>

      {/* `mt-auto` empuja el pie al fondo, asi el marcador queda alineado
          entre tarjetas de distinta altura dentro de la misma fila. */}
      {match?.status === 'played' ? (
        <div
          className="mt-auto flex items-center justify-between gap-2 border-t pt-2"
          style={{ borderColor: 'var(--color-rule)' }}
        >
          <span
            className="text-[10px] font-bold tracking-wider uppercase"
            style={{ color: won ? 'var(--color-accent)' : 'var(--color-fg-muted)' }}
          >
            {won ? 'Ganaron' : 'Perdieron'}
          </span>
          <span className="text-base font-semibold tabular-nums">
            {setsWonBy(team.id)}-{setsWonBy(rival.id)}
          </span>
        </div>
      ) : (
        // Sin partido no se dice nada: el titulo del grupo ya explica que ese
        // cruce esta sin acordar, y repetirlo por tarjeta solo agrega ruido.
        schedule && (
          <div
            className="mt-auto border-t pt-2 text-[11px]"
            style={{ borderColor: 'var(--color-rule)', color: 'var(--color-fg-muted)' }}
          >
            {schedule}
          </div>
        )
      )}
    </div>
  )
}
