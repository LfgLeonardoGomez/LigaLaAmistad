import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import type { Match, Sponsor, Team, Zone } from '../api/types'
import { useResource } from '../api/useResource'
import { MatchDetail } from './MatchDetail'
import { Notice, PublicModal, TeamAvatar, formatDate } from './parts'
import { imageUrl } from '../api/images'

const POINT_RULES = [
  { label: 'Ganar 2-0', value: '3 pts' },
  { label: 'Ganar 2-1', value: '2 pts' },
  { label: 'Perder 1-2', value: '1 pt' },
  { label: 'Perder 0-2', value: '0 pts' },
]

/**
 * Every pair plays every other pair inside its own zone, so a zone of n pairs
 * produces n·(n-1)/2 matches. Two zones of ten give ninety.
 *
 * Computed and not hard coded: the day a zone ends up with nine or eleven
 * pairs, a fixed number would turn the headline into a lie.
 */
function seasonMatches(teams: Team[]): number {
  const perZone = new Map<number, number>()
  for (const team of teams) {
    perZone.set(team.zone_id, (perZone.get(team.zone_id) ?? 0) + 1)
  }

  let total = 0
  for (const count of perZone.values()) {
    total += (count * (count - 1)) / 2
  }
  return total
}

export function HomePage() {
  const zones = useResource<Zone[]>('/public/zones')
  const teams = useResource<Team[]>('/public/teams')
  const matches = useResource<Match[]>('/public/matches')
  const sponsors = useResource<Sponsor[]>('/public/sponsors')

  const teamsById = useMemo(
    () => new Map((teams.data ?? []).map((team) => [team.id, team])),
    [teams.data],
  )

  const [openMatch, setOpenMatch] = useState<Match | null>(null)

  // The API returns played matches oldest first; the home wants the newest.
  const recent = useMemo(() => [...(matches.data ?? [])].reverse().slice(0, 3), [matches.data])

  return (
    <>
      <Hero
        teams={teams.data?.length}
        zones={zones.data?.length}
        seasonTotal={teams.data ? seasonMatches(teams.data) : undefined}
      />

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
                onOpen={() => setOpenMatch(match)}
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

      {openMatch && (
        <PublicModal title="El partido" onClose={() => setOpenMatch(null)}>
          <MatchDetail
            match={openMatch}
            teamsById={teamsById}
            zones={zones.data ?? []}
          />
        </PublicModal>
      )}

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
  seasonTotal,
}: {
  teams: number | undefined
  zones: number | undefined
  seasonTotal: number | undefined
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

        {/* A slogan, not a description: the numbers below already explain the
            format, so this line only has to say what the league feels like. */}
        <p
          className="hero-measure mt-6 max-w-[28ch] text-[clamp(19px,3vw,30px)] leading-snug text-balance"
          style={{ color: 'var(--color-fg)' }}
        >
          Los amigos de siempre,{' '}
          <span style={{ color: 'var(--color-accent)' }}>enfrentados como nunca.</span>
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

        <p
          className="hero-row mt-12 flex flex-wrap items-baseline gap-x-3 gap-y-2 text-[clamp(15px,2vw,19px)]"
          style={{ color: 'var(--color-fg-muted)' }}
        >
          <Beat value={teams} word="parejas" />
          <Dot />
          <Beat value={zones} word="zonas" />
          <Dot />
          <Beat value={seasonTotal} word="partidos" />
          <Dot />
          <Beat value={1} word="campeón" trophy />
        </p>
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

/** One beat of the headline: a number and the word that follows it. */
function Beat({
  value,
  word,
  trophy = false,
}: {
  value: number | undefined
  word: string
  trophy?: boolean
}) {
  return (
    <span className="inline-flex items-baseline gap-1.5 whitespace-nowrap">
      <span
        className="display text-[clamp(24px,4vw,38px)]"
        style={{ color: 'var(--color-accent)' }}
      >
        {value ?? '—'}
      </span>
      {trophy && <Trophy />}
      <span>{word}</span>
    </span>
  )
}

function Dot() {
  return (
    <span aria-hidden="true" style={{ color: 'var(--color-rule)' }}>
      ·
    </span>
  )
}

/** Drawn rather than an emoji: an emoji renders differently on every platform
    and would be the only thing on the page not wearing the theme's colour. */
function Trophy() {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      className="h-[0.95em] w-[0.95em] self-center"
      fill="currentColor"
      style={{ color: 'var(--color-accent)' }}
    >
      <path d="M6 3h12v2h3v3a4 4 0 0 1-3.4 3.95A6 6 0 0 1 13 15.9V18h3a1 1 0 0 1 0 2H8a1 1 0 0 1 0-2h3v-2.1a6 6 0 0 1-4.6-3.95A4 4 0 0 1 3 8V5h3V3Zm0 4H5v1a2 2 0 0 0 1 1.73V7Zm12 2.73A2 2 0 0 0 19 8V7h-1v2.73Z" />
    </svg>
  )
}

function MatchCard({
  match,
  teamsById,
  zones,
  onOpen,
}: {
  match: Match
  teamsById: Map<number, Team>
  zones: Zone[]
  onOpen: () => void
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

  const hasExtras = Boolean(match.photo_url || match.comment)

  return (
    <button
      type="button"
      onClick={onOpen}
      aria-haspopup="dialog"
      className="card card-hover block w-full p-4 text-left"
    >
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

      <span
        className="mt-3 flex items-center gap-1.5 text-[11px] font-semibold tracking-widest uppercase"
        style={{ color: 'var(--color-accent)' }}
      >
        {hasExtras ? 'Ver foto y comentario' : 'Ver el partido'}
        <span aria-hidden="true">→</span>
      </span>
    </button>
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
      src={imageUrl(sponsor.logo_url, { width: 240 })}
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
