import type { Match, Team, Zone } from '../api/types'
import { formatTime, venueLabel } from '../api/types'
import type { VoteTally } from '../api/votes'
import { imageUrl } from '../api/images'
import { MatchVoting } from './MatchVoting'
import { TeamAvatar, formatDate } from './parts'

/**
 * The whole story of a match: who played, the games of every set, and the
 * photo and the jab if somebody left them.
 *
 * Shared between the results list and the dialog that opens from the home, so
 * a match looks the same wherever it is read.
 */
export function MatchDetail({
  match,
  teamsById,
  zones,
  interactive = false,
  tally,
}: {
  match: Match
  teamsById: Map<number, Team>
  zones: Zone[]
  /** Adds the hover lift. Off inside a dialog, where nothing is clickable. */
  interactive?: boolean
  /** How the public voted before it was played. Absent means nobody did. */
  tally?: VoteTally
}) {
  const teamA = teamsById.get(match.team_a_id)
  const teamB = teamsById.get(match.team_b_id)
  // A match stores no zone. It is the zone of its teams, which always match.
  const zoneName = zones.find((zone) => zone.id === teamA?.zone_id)?.name
  const startTime = formatTime(match.time)
  const venue = venueLabel(match.venue)

  return (
    <article className={`card h-full ${interactive ? 'card-hover' : ''}`}>
      <header
        className="flex items-center justify-between gap-3 px-3 py-2 text-[10px] font-semibold tracking-widest uppercase"
        style={{ borderBottom: '1px solid var(--color-rule)', color: 'var(--color-fg-muted)' }}
      >
        <span>{zoneName ?? '—'}</span>
        <time dateTime={match.time ? `${match.date}T${match.time}` : match.date}>
          {formatDate(match.date)}
          {startTime && ` · ${startTime}`}
        </time>
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

      {/* The venue, the photo and the jab are all optional and most matches
          have none of them, so each one renders nothing at all rather than an
          empty slot: a card without them has to look exactly like it did
          before the feature existed. */}
      {venue && (
        <p
          className="px-3 py-1.5 text-[10px] font-semibold tracking-widest uppercase"
          style={{ borderTop: '1px solid var(--color-rule)', color: 'var(--color-fg-muted)' }}
        >
          {venue}
        </p>
      )}

      {match.photo_url && (
        <img
          src={imageUrl(match.photo_url, { width: 600 })}
          alt=""
          // Lazy down a list of twenty cards; eager inside the dialog, where
          // the photo is the reason the dialog was opened.
          loading={interactive ? 'lazy' : 'eager'}
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

      {/* What the public predicted, next to what actually happened. Renders
          nothing when nobody voted, so a match from before the feature looks
          exactly as it did. */}
      {tally && tally.total > 0 && (
        <div className="px-3 pb-3">
          <MatchVoting
            tally={tally}
            teamA={teamA}
            teamB={teamB}
            winnerTeamId={match.winner_team_id}
          />
        </div>
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
              backgroundColor: won
                ? 'color-mix(in srgb, var(--color-accent) 12%, transparent)'
                : 'transparent',
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
