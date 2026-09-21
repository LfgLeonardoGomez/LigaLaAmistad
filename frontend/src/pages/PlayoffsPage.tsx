import { useState } from 'react'

import { imageUrl } from '../api/images'
import { ApiError, api } from '../api/client'
import type {
  Bracket,
  GroupStagePendingError,
  PlayoffNode,
  PlayoffResultsLoadedError,
  PlayoffRound,
  PlayoffTeam,
  PlayoffTieMatch,
} from '../api/playoffs'
import {
  ROUND_LABELS,
  WAITING_FOR_LABEL,
  asGroupStagePendingError,
  asPlayoffResultsLoadedError,
  groupFeeders,
  isDirectQualifier,
  pairName,
  setsWonBy,
} from '../api/playoffs'
import { formatTime, venueLabel } from '../api/types'
import { useResource } from '../api/useResource'
import { Modal } from '../components/Modal'
import { Alert, Button, PageHeader, Spinner } from '../components/ui'

// --- Bracket geometry ---------------------------------------------------------
//
// Every node's position is derived from the shape of the two arrays around
// it (`groupFeeders`), never from a hardcoded slot map. That is what keeps
// this in sync with `PlayoffRoundRead.nodes` — already in draw order, see
// `app.playoffs.service.DRAW_ORDER` — without a second copy of the wiring.

const CARD_WIDTH = 208
const CARD_HEIGHT = 60
const ROW_HEIGHT = 84
const COLUMN_GAP = 56

type Column = { round: PlayoffRound; nodes: PlayoffNode[] }

function layoutYCenters(columns: PlayoffNode[][]): number[][] {
  const centers: number[][] = []
  columns.forEach((column, index) => {
    if (index === 0) {
      centers.push(column.map((_, i) => i * ROW_HEIGHT + ROW_HEIGHT / 2))
      return
    }
    const groups = groupFeeders(centers[index - 1] ?? [], column)
    centers.push(groups.map((group) => group.reduce((sum, y) => sum + y, 0) / group.length))
  })
  return centers
}

interface ConnectorLine {
  x1: number
  y1: number
  x2: number
  y2: number
}

function buildConnectors(columns: PlayoffNode[][], centers: number[][]): ConnectorLine[] {
  const lines: ConnectorLine[] = []
  for (let col = 0; col < columns.length - 1; col++) {
    const groups = groupFeeders(centers[col] ?? [], columns[col + 1] ?? [])
    const xRight = col * (CARD_WIDTH + COLUMN_GAP) + CARD_WIDTH
    const xLeft = (col + 1) * (CARD_WIDTH + COLUMN_GAP)
    const xMid = (xRight + xLeft) / 2

    groups.forEach((groupYs, nextIndex) => {
      const yNext = centers[col + 1]?.[nextIndex] ?? 0
      const first = groupYs[0] ?? 0

      // Round 2 feeds the quarterfinal one-to-one: a straight stub, no join.
      if (groupYs.length === 1) {
        lines.push({ x1: xRight, y1: first, x2: xLeft, y2: yNext })
        return
      }

      for (const y of groupYs) {
        lines.push({ x1: xRight, y1: y, x2: xMid, y2: y })
      }
      lines.push({ x1: xMid, y1: first, x2: xMid, y2: groupYs[groupYs.length - 1] ?? 0 })
      lines.push({ x1: xMid, y1: yNext, x2: xLeft, y2: yNext })
    })
  }
  return lines
}

function BracketColumns({
  columns,
  onOpenNode,
}: {
  columns: Column[]
  onOpenNode: (node: PlayoffNode, round: PlayoffRound) => void
}) {
  const nodeColumns = columns.map((column) => column.nodes)
  const centers = layoutYCenters(nodeColumns)
  const lines = buildConnectors(nodeColumns, centers)
  const width = columns.length * CARD_WIDTH + (columns.length - 1) * COLUMN_GAP
  const height = (nodeColumns[0]?.length ?? 0) * ROW_HEIGHT

  return (
    <div>
      <div className="mb-3 flex" style={{ width }}>
        {columns.map((column, index) => (
          <div
            key={column.round}
            style={{ width: CARD_WIDTH, marginRight: index < columns.length - 1 ? COLUMN_GAP : 0 }}
            className="text-center text-xs font-semibold uppercase tracking-widest text-ink-400"
          >
            {ROUND_LABELS[column.round]}
          </div>
        ))}
      </div>

      <div style={{ position: 'relative', width, height }}>
        <svg width={width} height={height} className="pointer-events-none absolute inset-0">
          {lines.map((line, index) => (
            <line
              key={index}
              x1={line.x1}
              y1={line.y1}
              x2={line.x2}
              y2={line.y2}
              className="stroke-ink-200"
              strokeWidth={1}
            />
          ))}
        </svg>

        {columns.map((column, colIndex) =>
          column.nodes.map((node, i) => (
            <div
              key={node.id ?? `${column.round}-${node.slot}`}
              style={{
                position: 'absolute',
                left: colIndex * (CARD_WIDTH + COLUMN_GAP),
                top: (centers[colIndex]?.[i] ?? 0) - CARD_HEIGHT / 2,
              }}
            >
              <NodeCard node={node} round={column.round} onOpen={() => onOpenNode(node, column.round)} />
            </div>
          )),
        )}
      </div>
    </div>
  )
}

// --- Node card -----------------------------------------------------------------

function SeedChip({ label, filled }: { label: string; filled?: boolean }) {
  return (
    <span
      className={`shrink-0 rounded px-1 py-0.5 font-mono text-[10px] leading-none ${
        filled ? 'bg-ink-900 text-white' : 'bg-ink-100 text-ink-500'
      }`}
    >
      {label}
    </span>
  )
}

function WaitingRow({
  team,
  round,
  waitingLabel,
}: {
  team: PlayoffTeam | null
  round: PlayoffRound
  waitingLabel: string
}) {
  if (team) {
    return (
      <div className="flex min-w-0 items-center gap-1.5 px-0.5">
        <SeedChip label={team.seed} filled={isDirectQualifier(round, team)} />
        <span className="truncate text-sm text-ink-800">{pairName(team)}</span>
      </div>
    )
  }
  return (
    <div className="px-0.5">
      <span className="truncate text-xs italic text-ink-400">{waitingLabel}</span>
    </div>
  )
}

type Emphasis = 'normal' | 'winner' | 'loser' | 'champion'

function ResultRow({
  round,
  team,
  scoreText,
  emphasis,
}: {
  round: PlayoffRound
  team: PlayoffTeam
  scoreText: string
  emphasis: Emphasis
}) {
  if (emphasis === 'champion') {
    return (
      <div className="flex items-center justify-between gap-2 rounded bg-ink-900 px-1.5 py-1 text-white">
        <span className="flex min-w-0 items-center gap-1.5">
          <SeedChip label={team.seed} filled />
          <span className="truncate text-sm font-semibold">{pairName(team)}</span>
        </span>
        <span className="shrink-0 font-mono text-xs">{scoreText}</span>
      </div>
    )
  }

  const nameClass =
    emphasis === 'winner' ? 'font-semibold text-ink-900' : emphasis === 'loser' ? 'text-ink-400' : 'text-ink-800'
  const scoreClass = emphasis === 'winner' ? 'text-ink-900' : 'text-ink-400'

  return (
    <div className="flex items-center justify-between gap-2 px-0.5">
      <span className="flex min-w-0 items-center gap-1.5">
        <SeedChip label={team.seed} filled={isDirectQualifier(round, team)} />
        <span className={`truncate text-sm ${nameClass}`}>{pairName(team)}</span>
      </span>
      <span className={`shrink-0 font-mono text-xs ${scoreClass}`}>{scoreText}</span>
    </div>
  )
}

function NodeCard({
  node,
  round,
  onOpen,
}: {
  node: PlayoffNode
  round: PlayoffRound
  onOpen: () => void
}) {
  const baseClass =
    'flex h-[60px] w-52 flex-col justify-center rounded-lg px-2 text-left transition-shadow hover:shadow-sm'

  if (node.status === 'bye') {
    const team = node.team_a ?? node.team_b
    if (!team) {
      return (
        <button
          type="button"
          onClick={onOpen}
          className={`${baseClass} items-center justify-center border border-dashed border-ink-300 bg-ink-50`}
        >
          <span className="text-xs italic text-ink-400">Sin cruce</span>
        </button>
      )
    }
    // The seed travels with the team, whichever side it survived on — no
    // need to guess which side of the node it came from.
    return (
      <button
        type="button"
        onClick={onOpen}
        className={`${baseClass} flex-row items-center justify-between gap-2 border border-ink-200 bg-surface`}
      >
        <span className="flex min-w-0 items-center gap-1.5">
          <SeedChip label={team.seed} filled={isDirectQualifier(round, team)} />
          <span className="truncate text-sm font-medium text-ink-900">{pairName(team)}</span>
        </span>
        <span className="shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-ink-500 ring-1 ring-inset ring-ink-300">
          Pasa
        </span>
      </button>
    )
  }

  if (!node.match) {
    const waitingLabel = WAITING_FOR_LABEL[round] ?? 'Por definir'
    return (
      <button
        type="button"
        onClick={onOpen}
        className={`${baseClass} gap-1 border border-dashed border-ink-300 bg-ink-50`}
      >
        <WaitingRow team={node.team_a} round={round} waitingLabel={waitingLabel} />
        <div className="h-px bg-ink-200" />
        <WaitingRow team={node.team_b} round={round} waitingLabel={waitingLabel} />
      </button>
    )
  }

  const match = node.match
  const played = match.status === 'played'
  const champion = round === 'final' && played
  const teamA = node.team_a
  const teamB = node.team_b
  const winnerIsA = played && match.winner_team_id === teamA?.id

  const scoreA = played && teamA ? String(setsWonBy(match, teamA.id)) : '—'
  const scoreB = played && teamB ? String(setsWonBy(match, teamB.id)) : '—'
  const emphasisA: Emphasis = champion && winnerIsA ? 'champion' : !played ? 'normal' : winnerIsA ? 'winner' : 'loser'
  const emphasisB: Emphasis =
    champion && !winnerIsA ? 'champion' : !played ? 'normal' : !winnerIsA ? 'winner' : 'loser'
  const borderClass = played ? 'border border-ink-200' : 'border border-ink-900 ring-1 ring-ink-900/10'

  return (
    <button type="button" onClick={onOpen} className={`${baseClass} gap-0.5 bg-surface ${borderClass}`}>
      {teamA && <ResultRow round={round} team={teamA} scoreText={scoreA} emphasis={emphasisA} />}
      <div className="h-px bg-ink-200" />
      {teamB && <ResultRow round={round} team={teamB} scoreText={scoreB} emphasis={emphasisB} />}
    </button>
  )
}

// --- Node detail modal -----------------------------------------------------------

function TeamPhoto({ team }: { team: PlayoffTeam }) {
  if (team.photo_url) {
    return (
      <img
        src={imageUrl(team.photo_url, { width: 72, height: 72 })}
        alt=""
        className="h-10 w-10 shrink-0 rounded-full object-cover ring-1 ring-ink-200"
      />
    )
  }
  return (
    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-ink-100 text-sm font-medium text-ink-400">
      {team.player_one_name.charAt(0).toUpperCase()}
    </span>
  )
}

function TieTeamRow({ team, highlight }: { team: PlayoffTeam | null; highlight?: boolean }) {
  if (!team) {
    return (
      <div className="flex items-center gap-3 rounded-md px-2 py-1.5">
        <span className="text-sm italic text-ink-400">Sin definir</span>
      </div>
    )
  }
  return (
    <div className={`flex items-center gap-3 rounded-md px-2 py-1.5 ${highlight ? 'bg-ink-50' : ''}`}>
      <TeamPhoto team={team} />
      <span className="flex min-w-0 items-center gap-1.5">
        <SeedChip label={team.seed} />
        <span className={`truncate text-sm ${highlight ? 'font-semibold text-ink-900' : 'text-ink-800'}`}>
          {pairName(team)}
        </span>
      </span>
    </div>
  )
}

function MatchDetail({ match }: { match: PlayoffTieMatch }) {
  return (
    <>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
        <div>
          <dt className="text-ink-500">Fecha</dt>
          <dd className="text-ink-800">{match.date}</dd>
        </div>
        {match.time && (
          <div>
            <dt className="text-ink-500">Hora</dt>
            <dd className="text-ink-800">{formatTime(match.time)}</dd>
          </div>
        )}
        {match.venue && (
          <div>
            <dt className="text-ink-500">Lugar</dt>
            <dd className="text-ink-800">{venueLabel(match.venue)}</dd>
          </div>
        )}
      </dl>

      {match.status === 'played' && match.sets.length > 0 && (
        <div>
          <p className="mb-1 text-xs font-medium uppercase tracking-wide text-ink-500">Sets</p>
          <p className="font-mono text-sm text-ink-800">
            {match.sets.map((set) => `${set.team_a_games}-${set.team_b_games}`).join('  ')}
          </p>
        </div>
      )}

      {match.comment && (
        <div>
          <p className="mb-1 text-xs font-medium uppercase tracking-wide text-ink-500">Comentario</p>
          <p className="text-sm text-ink-700">{match.comment}</p>
        </div>
      )}

      {match.photo_url && (
        <img src={imageUrl(match.photo_url, { width: 480 })} alt="" className="w-full rounded-md ring-1 ring-ink-200" />
      )}
    </>
  )
}

function NodeDetailModal({
  node,
  round,
  onClose,
}: {
  node: PlayoffNode
  round: PlayoffRound
  onClose: () => void
}) {
  const title = `${ROUND_LABELS[round]} · Cruce ${node.slot}`

  if (node.status === 'bye') {
    const team = node.team_a ?? node.team_b
    return (
      <Modal title={title} onClose={onClose}>
        {team ? (
          <div className="space-y-3">
            <p className="text-sm text-ink-600">Pasa de ronda sin jugar.</p>
            <TieTeamRow team={team} />
          </div>
        ) : (
          <p className="text-sm text-ink-500">Este cruce quedó sin equipo: ninguna pareja lo ocupa.</p>
        )}
      </Modal>
    )
  }

  if (!node.match) {
    const waitingLabel = WAITING_FOR_LABEL[round] ?? 'un resultado anterior'
    return (
      <Modal title={title} onClose={onClose}>
        <div className="space-y-3">
          {(node.team_a || node.team_b) && (
            <div className="space-y-1">
              {node.team_a && <TieTeamRow team={node.team_a} />}
              {node.team_b && <TieTeamRow team={node.team_b} />}
            </div>
          )}
          <p className="text-sm text-ink-500">
            Todavía no está definido. Este cruce espera a:{' '}
            <span className="font-medium text-ink-700">{waitingLabel}</span>.
          </p>
        </div>
      </Modal>
    )
  }

  const match = node.match
  return (
    <Modal title={title} onClose={onClose}>
      <div className="space-y-4">
        <div className="space-y-1">
          <TieTeamRow
            team={node.team_a}
            highlight={match.status === 'played' && match.winner_team_id === node.team_a?.id}
          />
          <TieTeamRow
            team={node.team_b}
            highlight={match.status === 'played' && match.winner_team_id === node.team_b?.id}
          />
        </div>
        <MatchDetail match={match} />
      </div>
    </Modal>
  )
}

// --- Mode header -----------------------------------------------------------------

function ModeHeader({
  data,
  playedCount,
  onGenerate,
  onDelete,
}: {
  data: Bracket
  playedCount: number
  onGenerate: () => void
  onDelete: () => void
}) {
  const isProjection = data.mode === 'projection'

  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-4 rounded-lg border border-ink-200 bg-surface p-4">
      <div>
        <span
          className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-wide ${
            isProjection ? 'bg-amber-50 text-amber-700' : 'bg-emerald-50 text-emerald-700'
          }`}
        >
          {isProjection ? 'Proyección' : 'Oficial'}
        </span>
        <p className="mt-2 max-w-2xl text-sm text-ink-600">
          {isProjection
            ? 'Este cuadro es una proyección en vivo a partir de la tabla de posiciones de hoy: se va a mover con cada resultado que se cargue en la fase de grupos.'
            : 'La siembra quedó congelada al generar el cuadro. Avanza a medida que se cargan los resultados de cada cruce.'}
        </p>
        <p className="mt-1 text-sm text-ink-500">
          {isProjection
            ? `${data.pending_group_matches ?? 0} ${
                data.pending_group_matches === 1 ? 'partido pendiente' : 'partidos pendientes'
              } en la fase de grupos.`
            : `${playedCount} ${playedCount === 1 ? 'cruce jugado' : 'cruces jugados'}.`}
        </p>
      </div>

      {isProjection ? (
        <Button onClick={onGenerate}>Generar playoffs</Button>
      ) : (
        <Button variant="secondary" onClick={onDelete}>
          Deshacer cuadro
        </Button>
      )}
    </div>
  )
}

// --- Page --------------------------------------------------------------------

export function PlayoffsPage() {
  const bracket = useResource<Bracket>('/playoffs/bracket')

  const [openNode, setOpenNode] = useState<{ node: PlayoffNode; round: PlayoffRound } | null>(null)

  const [generateStep, setGenerateStep] = useState<'confirm' | 'conflict' | null>(null)
  const [pendingConflict, setPendingConflict] = useState<GroupStagePendingError | null>(null)
  const [generating, setGenerating] = useState(false)
  const [generateError, setGenerateError] = useState<string | null>(null)

  const [deleteStep, setDeleteStep] = useState<'confirm' | 'conflict' | null>(null)
  const [playedConflict, setPlayedConflict] = useState<PlayoffResultsLoadedError | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  async function runGenerate(force: boolean) {
    setGenerating(true)
    setGenerateError(null)
    try {
      await api.post('/playoffs/generate', force ? { force: true } : {})
      setGenerateStep(null)
      setPendingConflict(null)
      bracket.reload()
    } catch (cause) {
      if (!force && cause instanceof ApiError && cause.status === 409) {
        const structured = asGroupStagePendingError(cause.body)
        if (structured) {
          setPendingConflict(structured)
          setGenerateStep('conflict')
          setGenerating(false)
          return
        }
      }
      setGenerateError(cause instanceof Error ? cause.message : 'No se pudo generar el cuadro')
    } finally {
      setGenerating(false)
    }
  }

  async function runDelete(force: boolean) {
    setDeleting(true)
    setDeleteError(null)
    try {
      await api.delete(force ? '/playoffs?force=true' : '/playoffs')
      setDeleteStep(null)
      setPlayedConflict(null)
      bracket.reload()
    } catch (cause) {
      if (!force && cause instanceof ApiError && cause.status === 409) {
        const structured = asPlayoffResultsLoadedError(cause.body)
        if (structured) {
          setPlayedConflict(structured)
          setDeleteStep('conflict')
          setDeleting(false)
          return
        }
      }
      setDeleteError(cause instanceof Error ? cause.message : 'No se pudo deshacer el cuadro')
    } finally {
      setDeleting(false)
    }
  }

  if (bracket.loading) return <Spinner />
  if (bracket.error) return <Alert>{bracket.error}</Alert>
  if (!bracket.data) return null

  const data = bracket.data
  const playedCount = data.rounds
    .flatMap((round) => round.nodes)
    .filter((node) => node.match?.status === 'played').length

  const byRound = new Map(data.rounds.map((round) => [round.round, round.nodes]))
  const r1 = byRound.get('round_1') ?? []
  const r2 = byRound.get('round_2') ?? []
  const qf = byRound.get('quarterfinal') ?? []
  const sf = byRound.get('semifinal') ?? []
  const final = byRound.get('final') ?? []

  const desktopColumns: Column[] = data.rounds.map((round) => ({ round: round.round, nodes: round.nodes }))

  // The two halves are genuinely independent until the final, so the split
  // is derived the same way the desktop connectors are: from the shape of
  // the arrays, not a hardcoded "first four / last four".
  const qfHalves = groupFeeders(qf, sf)
  const r2Halves = groupFeeders(r2, qfHalves)
  const r1Halves = groupFeeders(r1, qfHalves)

  const half1: Column[] = [
    { round: 'round_1', nodes: r1Halves[0] ?? [] },
    { round: 'round_2', nodes: r2Halves[0] ?? [] },
    { round: 'quarterfinal', nodes: qfHalves[0] ?? [] },
  ]
  const half2: Column[] = [
    { round: 'round_1', nodes: r1Halves[1] ?? [] },
    { round: 'round_2', nodes: r2Halves[1] ?? [] },
    { round: 'quarterfinal', nodes: qfHalves[1] ?? [] },
  ]
  const finalSection: Column[] = [
    { round: 'semifinal', nodes: sf },
    { round: 'final', nodes: final },
  ]

  const openModal = (node: PlayoffNode, round: PlayoffRound) => setOpenNode({ node, round })

  return (
    <>
      <PageHeader title="Playoffs" description="El cuadro de eliminación directa de la temporada." />

      <ModeHeader
        data={data}
        playedCount={playedCount}
        onGenerate={() => setGenerateStep('confirm')}
        onDelete={() => setDeleteStep('confirm')}
      />

      {generateError && (
        <div className="mb-4">
          <Alert>{generateError}</Alert>
        </div>
      )}
      {deleteError && (
        <div className="mb-4">
          <Alert>{deleteError}</Alert>
        </div>
      )}

      {/* Full-bleed: a bracket is wide content, unlike the rest of the panel,
          which stays inside Layout's max-w-6xl. */}
      <div style={{ width: '100vw', marginLeft: 'calc(50% - 50vw)', marginRight: 'calc(50% - 50vw)' }} className="px-4 sm:px-6">
        <div className="hidden overflow-x-auto pb-4 lg:block">
          <BracketColumns columns={desktopColumns} onOpenNode={openModal} />
        </div>

        <div className="space-y-10 lg:hidden">
          <div className="overflow-x-auto pb-4">
            <BracketColumns columns={half1} onOpenNode={openModal} />
          </div>
          <div className="overflow-x-auto pb-4">
            <BracketColumns columns={half2} onOpenNode={openModal} />
          </div>
          <div className="overflow-x-auto pb-4">
            <BracketColumns columns={finalSection} onOpenNode={openModal} />
          </div>
        </div>
      </div>

      {openNode && <NodeDetailModal node={openNode.node} round={openNode.round} onClose={() => setOpenNode(null)} />}

      {generateStep === 'confirm' && (
        <Modal title="Generar playoffs" onClose={() => setGenerateStep(null)}>
          <div className="space-y-4">
            <p className="text-sm text-ink-600">
              Esto congela la tabla de posiciones actual y arma el cuadro a partir de ella. Una vez generado, el
              cuadro no se vuelve a calcular, aunque después se cargue o se corrija un resultado de la fase de
              grupos.
            </p>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setGenerateStep(null)}>
                Cancelar
              </Button>
              <Button onClick={() => void runGenerate(false)} disabled={generating}>
                {generating ? 'Generando…' : 'Continuar'}
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {generateStep === 'conflict' && pendingConflict && (
        <Modal title="Partidos de grupos pendientes" onClose={() => setGenerateStep(null)}>
          <div className="space-y-4">
            <p className="text-sm text-ink-600">
              Todavía hay{' '}
              {pendingConflict.pending_count === 1
                ? 'un partido pendiente'
                : `${pendingConflict.pending_count} partidos pendientes`}{' '}
              en la fase de grupos. Generar el cuadro igual deja esos partidos afuera y siembra esos cruces con la
              tabla de posiciones tal como está hoy — la opción correcta cuando un partido ya no se va a jugar, por
              ejemplo porque una pareja abandonó.
            </p>
            <ul className="space-y-1 rounded-md bg-ink-50 px-3 py-2 text-sm text-ink-700">
              {pendingConflict.pending_matches.map((match) => (
                <li key={match.id}>
                  {pairName(match.team_a)} vs {pairName(match.team_b)}
                </li>
              ))}
            </ul>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setGenerateStep('confirm')}>
                Volver
              </Button>
              <Button onClick={() => void runGenerate(true)} disabled={generating}>
                {generating ? 'Generando…' : 'Generar igual'}
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {deleteStep === 'confirm' && (
        <Modal title="Deshacer el cuadro de playoffs" onClose={() => setDeleteStep(null)}>
          <div className="space-y-4">
            <p className="text-sm text-ink-600">
              Esto elimina el cuadro completo, la siembra congelada y todos los partidos que generó, junto con
              cualquier resultado ya cargado. La acción no se puede deshacer. Después se puede generar un cuadro
              nuevo desde cero.
            </p>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setDeleteStep(null)}>
                Cancelar
              </Button>
              <Button variant="danger" onClick={() => void runDelete(false)} disabled={deleting}>
                {deleting ? 'Eliminando…' : 'Eliminar el cuadro'}
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {deleteStep === 'conflict' && playedConflict && (
        <Modal title="El cuadro ya tiene resultados cargados" onClose={() => setDeleteStep(null)}>
          <div className="space-y-4">
            <p className="text-sm text-ink-600">
              {playedConflict.played_count === 1
                ? 'Ya hay un cruce jugado.'
                : `Ya hay ${playedConflict.played_count} cruces jugados.`}{' '}
              Eliminar el cuadro ahora borra esos resultados junto con todo lo demás, sin posibilidad de
              recuperarlos.
            </p>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setDeleteStep('confirm')}>
                Volver
              </Button>
              <Button variant="danger" onClick={() => void runDelete(true)} disabled={deleting}>
                {deleting ? 'Eliminando…' : 'Eliminar de todos modos'}
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </>
  )
}
