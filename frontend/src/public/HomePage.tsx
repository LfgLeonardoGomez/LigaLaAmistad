import { useMemo } from 'react'
import { Link } from 'react-router-dom'

import type { Match, Sponsor, Team, Zone } from '../api/types'
import { useResource } from '../api/useResource'
import { Notice, TeamAvatar, formatDate } from './parts'

const POINT_RULES = [
  { label: 'Ganar 2-0', value: '3 pts' },
  { label: 'Ganar 2-1', value: '2 pts' },
  { label: 'Perder 1-2', value: '1 pt' },
  { label: 'Perder 0-2', value: '0 pts' },
]

export function HomePage() {
  const zones = useResource<Zone[]>('/public/zones')
  const teams = useResource<Team[]>('/public/teams')
  const matches = useResource<Match[]>('/public/matches')
  const sponsors = useResource<Sponsor[]>('/public/sponsors')

  const teamsById = useMemo(
    () => new Map((teams.data ?? []).map((team) => [team.id, team])),
    [teams.data],
  )

  // The API returns played matches oldest first; the home wants the newest.
  const recent = useMemo(() => [...(matches.data ?? [])].reverse().slice(0, 3), [matches.data])

  return (
    <>
      <Hero teams={teams.data?.length} zones={zones.data?.length} played={matches.data?.length} />

      <section className="container-page py-[clamp(36px,6vw,64px)]">
        <div className="mb-6 flex items-baseline justify-between gap-4">
          <h2 className="display text-[clamp(24px,4.5vw,40px)]">Recién jugados</h2>
          <Link
            to="/resultados"
            className="text-xs font-semibold tracking-widest uppercase"
            style={{ color: 'var(--color-accent)' }}
          >
            Ver todos →
          </Link>
        </div>

        {matches.loading ? (
          <Notice>Cargando resultados…</Notice>
        ) : matches.error ? (
          <Notice tone="hot">{matches.error}</Notice>
        ) : recent.length === 0 ? (
          <Notice>
            Todavía no se jugó ningún partido. Cuando se cargue el primer resultado, aparece acá.
          </Notice>
        ) : (
          <div className="grid gap-4 md:grid-cols-3">
            {recent.map((match) => (
              <MatchCard
                key={match.id}
                match={match}
                teamsById={teamsById}
                zones={zones.data ?? []}
              />
            ))}
          </div>
        )}
      </section>

      <PhotoBand />

      <section className="container-page py-[clamp(36px,6vw,64px)]">
        <h2 className="display mb-6 text-[clamp(24px,4.5vw,40px)]">Cómo funciona</h2>

        <div className="grid gap-4 md:grid-cols-3">
          <RuleCard number="01" title="Dos zonas" accent="accent">
            <p style={{ color: 'var(--color-fg-muted)' }}>
              Las parejas se reparten en Zona A y Zona B. Se juega todos contra todos dentro
              de la zona.
            </p>
          </RuleCard>

          <RuleCard number="02" title="Lo arreglan ustedes" accent="hot">
            <p style={{ color: 'var(--color-fg-muted)' }}>
              Cada pareja coordina su partido y la organización carga el resultado.
            </p>
          </RuleCard>

          <RuleCard number="03" title="Puntos" accent="accent">
            <dl className="text-sm">
              {POINT_RULES.map((rule) => (
                <div
                  key={rule.label}
                  className="flex items-center justify-between py-1.5"
                  style={{ borderBottom: '1px solid var(--color-rule)' }}
                >
                  <dt>{rule.label}</dt>
                  <dd className="font-semibold" style={{ color: 'var(--color-accent)' }}>
                    {rule.value}
                  </dd>
                </div>
              ))}
            </dl>
          </RuleCard>
        </div>
      </section>

      {sponsors.data && sponsors.data.length > 0 && (
        <section className="container-page py-[clamp(28px,5vw,52px)]">
          <h2
            className="mb-5 text-xs font-semibold tracking-widest uppercase"
            style={{ color: 'var(--color-fg-muted)' }}
          >
            Nos acompañan
          </h2>
          <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            {sponsors.data.map((sponsor) => (
              <li key={sponsor.id}>
                <SponsorTile sponsor={sponsor} />
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  )
}

function Hero({
  teams,
  zones,
  played,
}: {
  teams: number | undefined
  zones: number | undefined
  played: number | undefined
}) {
  return (
    <section className="photo">
      <div className="photo__media" />
      <div className="photo__veil" />

      <div className="container-page hero-align py-[clamp(64px,14vw,140px)]">
        <span
          className="badge-live inline-flex items-center gap-2 rounded-full px-3 py-1 text-[11px] font-semibold tracking-widest uppercase backdrop-blur-sm"
          style={{ border: '1px solid var(--color-rule)', color: 'var(--color-accent)' }}
        >
          <span aria-hidden="true" className="badge-live__dot h-1.5 w-1.5 rounded-full" />
          Temporada en curso
        </span>

        <h1 className="display mt-5 text-[clamp(46px,13vw,124px)]">
          Liga
          <br />
          La <span style={{ color: 'var(--color-accent)' }}>Amistad</span>
        </h1>

        <p
          className="hero-measure mt-6 max-w-[52ch] text-[clamp(16px,2.2vw,20px)] leading-relaxed text-pretty"
          style={{ color: 'var(--color-fg-muted)' }}
        >
          Pádel de barrio, en serio. Parejas repartidas en dos zonas, todos contra todos,
          partidos al mejor de tres sets. Cada resultado que se carga mueve la tabla.
        </p>

        <div className="hero-row mt-8 flex flex-wrap gap-3">
          <Link
            to="/tabla"
            className="display rounded px-5 py-3 text-sm"
            style={{ backgroundColor: 'var(--color-accent)', color: 'var(--color-on-accent)' }}
          >
            Ver la tabla
          </Link>
          <Link
            to="/resultados"
            className="display rounded px-5 py-3 text-sm backdrop-blur-sm"
            style={{ border: '1px solid var(--color-rule)', color: 'var(--color-fg)' }}
          >
            Últimos resultados
          </Link>
        </div>

        <dl className="hero-row mt-12 flex flex-wrap gap-x-10 gap-y-4">
          <Stat value={teams} label="Parejas" />
          <Stat value={zones} label="Zonas" />
          <Stat value={3} label="Sets, al mejor de" />
          <Stat value={played} label="Partidos jugados" />
        </dl>
      </div>
    </section>
  )
}

/** The photo stays still while this section scrolls over it, like a window. */
function PhotoBand() {
  return (
    <section className="photo-band">
      <div className="photo-band__media" />
      <div className="photo__veil" />

      <div className="container-page hero-align py-[clamp(72px,14vw,150px)]">
        <h2 className="display text-[clamp(28px,6vw,64px)]">
          Todos contra todos.
          <br />
          Cada resultado <span style={{ color: 'var(--color-accent)' }}>mueve la tabla</span>.
        </h2>
        <p
          className="hero-measure mt-5 max-w-[46ch] text-[clamp(15px,2vw,18px)] leading-relaxed"
          style={{ color: 'var(--color-fg-muted)' }}
        >
          No hay fechas fijas. Cada pareja arregla su partido, la organización carga los sets
          y las posiciones se recalculan solas.
        </p>
        <div className="hero-row mt-7 flex">
          <Link
            to="/tabla"
            className="display rounded px-5 py-3 text-sm"
            style={{ backgroundColor: 'var(--color-accent)', color: 'var(--color-on-accent)' }}
          >
            Ver las posiciones
          </Link>
        </div>
      </div>
    </section>
  )
}

function Stat({ value, label }: { value: number | undefined; label: string }) {
  return (
    <div>
      <dt className="sr-only">{label}</dt>
      <dd>
        <span
          className="display block text-[clamp(28px,5vw,44px)]"
          style={{ color: 'var(--color-accent)' }}
        >
          {value ?? '—'}
        </span>
        <span
          className="mt-1 block text-[11px] font-semibold tracking-widest uppercase"
          style={{ color: 'var(--color-fg-muted)' }}
        >
          {label}
        </span>
      </dd>
    </div>
  )
}

function MatchCard({
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
  // A match stores no zone: it is the zone of its teams, which always match.
  const zoneName = zones.find((zone) => zone.id === teamA?.zone_id)?.name

  const setsWonBy = (teamId: number) =>
    match.sets.filter((set) =>
      teamId === match.team_a_id
        ? set.team_a_games > set.team_b_games
        : set.team_b_games > set.team_a_games,
    ).length

  return (
    <article className="card card-hover p-4">
      <div
        className="mb-3 flex items-center justify-between text-[11px] font-semibold tracking-widest uppercase"
        style={{ color: 'var(--color-fg-muted)' }}
      >
        <span>{zoneName ?? '—'}</span>
        <time dateTime={match.date}>{formatDate(match.date)}</time>
      </div>

      {[teamA, teamB].map((team, index) => {
        const id = index === 0 ? match.team_a_id : match.team_b_id
        const won = match.winner_team_id === id
        return (
          <div key={id} className="flex items-center gap-2.5 py-1">
            <TeamAvatar team={team} size={24} />
            <span
              className="min-w-0 flex-1 truncate text-sm"
              style={{
                color: won ? 'var(--color-fg)' : 'var(--color-fg-muted)',
                fontWeight: won ? 600 : 400,
              }}
            >
              {team ? `${team.player_one_name} / ${team.player_two_name}` : '—'}
            </span>
            <span className="flex flex-none items-center gap-2">
              {won && (
                <span
                  className="rounded px-1.5 py-0.5 text-[10px] font-bold tracking-wider uppercase"
                  style={{
                    backgroundColor: 'var(--color-accent)',
                    color: 'var(--color-on-accent)',
                  }}
                >
                  Ganó
                </span>
              )}
              <span className="font-semibold tabular-nums">{setsWonBy(id)}</span>
            </span>
          </div>
        )
      })}
    </article>
  )
}

function RuleCard({
  number,
  title,
  accent,
  children,
}: {
  number: string
  title: string
  accent: 'accent' | 'hot'
  children: React.ReactNode
}) {
  const color = accent === 'hot' ? 'var(--color-hot)' : 'var(--color-accent)'
  return (
    <article className="card p-5" style={{ borderTop: `2px solid ${color}` }}>
      <div className="text-xs font-bold tracking-widest" style={{ color }}>
        {number}
      </div>
      <h3 className="display mt-2 mb-3 text-lg">{title}</h3>
      {children}
    </article>
  )
}

function SponsorTile({ sponsor }: { sponsor: Sponsor }) {
  const image = (
    <img
      src={sponsor.logo_url}
      alt={sponsor.name}
      loading="lazy"
      className="h-14 w-full object-contain p-2"
    />
  )

  if (!sponsor.url) {
    return <div className="card">{image}</div>
  }

  return (
    <a
      href={sponsor.url}
      target="_blank"
      rel="noopener noreferrer"
      className="card card-hover block"
    >
      {image}
    </a>
  )
}
