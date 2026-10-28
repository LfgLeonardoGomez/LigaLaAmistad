import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import type {
  AmericanoNavigation, AmericanoPlayoffsPageProps, EventDetail, KnockoutNode,
  DirtyNavigationDraft, PlayoffsResponse, QualifierSnapshot, SaveKnockoutRequest, Side, StartStage,
} from '../../api/americano-types'
import { Alert, Button, Card, Select, Spinner } from '../../components/ui'

const stages: StartStage[] = ['quarterfinal', 'semifinal', 'final']
const stageNames: Record<StartStage, string> = { quarterfinal: 'Cuartos', semifinal: 'Semifinal', final: 'Final' }
const stageHeadings: Record<StartStage, string> = { quarterfinal: 'Cuartos de final', semifinal: 'Semifinales', final: 'Final' }
const counts: Record<StartStage, { seeds: number; nodes: number }> = {
  quarterfinal: { seeds: 8, nodes: 7 }, semifinal: { seeds: 4, nodes: 3 }, final: { seeds: 2, nodes: 1 },
}

function positive(value: number) { return Number.isSafeInteger(value) && value > 0 }
function pairName(pair: Pick<QualifierSnapshot, 'player1_name' | 'player2_name'>) {
  return `${pair.player1_name} / ${pair.player2_name}`
}
function nodeName(node: Pick<KnockoutNode, 'stage' | 'slot'>) {
  return `${stageNames[node.stage]}${node.stage === 'final' ? '' : ` ${node.slot}`}`
}
function statusOf(cause: unknown) {
  return typeof cause === 'object' && cause !== null && 'status' in cause ? cause.status : undefined
}
function continuation(event: EventDetail): AmericanoNavigation | null {
  if (event.state === 'draft') return { kind: 'setup', event_id: event.id }
  if (event.state === 'review') return { kind: 'qualification', event_id: event.id }
  if (event.state === 'groups') {
    const next = event.continuation
    if (next.kind === 'round' && positive(next.round_number) && next.round_number <= event.total_rounds && next.round_number <= event.max_unlocked_round) {
      return { kind: 'round', event_id: event.id, round_number: next.round_number }
    }
    throw new Error('El evento no indica una ronda habilitada. Volvé a consultar su estado.')
  }
  if (event.state !== 'playoffs' && event.state !== 'completed') throw new Error('El estado del evento no permite una continuación segura.')
  return null
}

// Validate transport identity/references, never calculate seeds, winners or sets.
function checkPlayoffs(data: PlayoffsResponse, event: EventDetail) {
  const expected = counts[data.start_stage]
  if (data.event_id !== event.id || !['playoffs', 'completed'].includes(data.state) || data.start_stage !== event.start_stage || !expected ||
    data.snapshots.length !== expected.seeds || data.nodes.length !== expected.nodes) throw new Error('El cuadro recibido no corresponde al evento o está incompleto.')
  const ids = new Set(data.nodes.map(node => node.id))
  const seeds = new Set(data.snapshots.map(seed => seed.registration_id))
  const zones = new Set(data.zones.map(zone => zone.id))
  const registrations = new Set(event.registrations.map(registration => registration.id))
  const destinations = new Set<string>()
  const slots = new Set<string>()
  if (ids.size !== data.nodes.length || seeds.size !== data.snapshots.length || data.zones.length !== event.zones.length ||
    data.zones.some(zone => !event.zones.some(canonical => canonical.id === zone.id && canonical.label === zone.label)) ||
    data.snapshots.some(seed => !positive(seed.registration_id) || !registrations.has(seed.registration_id) || !zones.has(seed.zone_id) || seed.source_groups_revision !== data.groups_revision)) {
    throw new Error('El cuadro contiene referencias de participantes o partidos inválidas.')
  }
  for (const node of data.nodes) {
    const slot = `${node.stage}:${node.slot}`
    if (!positive(node.id) || !positive(node.slot) || !stages.includes(node.stage) || stages.indexOf(node.stage) < stages.indexOf(data.start_stage) || slots.has(slot) ||
      (node.registration_a && !seeds.has(node.registration_a.id)) || (node.registration_b && !seeds.has(node.registration_b.id)) ||
      (node.winner_registration_id !== null && node.winner_registration_id !== node.registration_a?.id && node.winner_registration_id !== node.registration_b?.id)) {
      throw new Error('El cuadro contiene un partido que no pertenece a sus clasificados.')
    }
    slots.add(slot)
    if (node.next_match_id === null) {
      if (node.next_side !== null || node.stage !== 'final') throw new Error('El destino de un partido no está disponible.')
    } else {
      const next = data.nodes.find(candidate => candidate.id === node.next_match_id)
      const destination = `${node.next_match_id}:${node.next_side}`
      if (!next || !['a', 'b'].includes(node.next_side ?? '') || stages.indexOf(next.stage) !== stages.indexOf(node.stage) + 1 || destinations.has(destination)) {
        throw new Error('El cuadro contiene un destino de avance inválido.')
      }
      destinations.add(destination)
    }
  }
  if ((data.champion && (!seeds.has(data.champion.id) || data.state !== 'completed')) || (data.state === 'completed' && !data.champion)) throw new Error('No se pudo verificar el campeón del evento.')
}

export function AmericanoPlayoffsPage({ eventId, operations, onNavigate, onDirtyChange }: AmericanoPlayoffsPageProps) {
  const [loaded, setLoaded] = useState<{ event: EventDetail; playoffs: PlayoffsResponse } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)
  const ports = useRef({ operations, onNavigate })
  useLayoutEffect(() => { ports.current = { operations, onNavigate } }, [operations, onNavigate])
  useEffect(() => {
    let active = true
    const port = ports.current
    setLoaded(null)
    setError(null)
    async function canonical() {
      const event = await port.operations.loadEvent(eventId)
      if (event.id !== eventId) throw new Error('El evento recibido no corresponde a esta URL.')
      return event
    }
    async function load() {
      try {
        if (!positive(eventId)) throw new Error('El identificador del evento no es válido.')
        const event = await canonical()
        if (!active) return
        const target = continuation(event)
        if (target) { port.onNavigate(target); return }
        let data: PlayoffsResponse
        try { data = await port.operations.loadPlayoffs(eventId) }
        catch (cause) {
          if (!active) return
          if (statusOf(cause) === 404 || statusOf(cause) === 409) {
            const latest = await canonical()
            if (!active) return
            const destination = continuation(latest)
            if (destination) { port.onNavigate(destination); return }
          }
          throw cause
        }
        if (!active) return
        checkPlayoffs(data, event)
        setLoaded({ event, playoffs: data })
      } catch (cause) {
        if (active) setError(cause instanceof Error ? cause.message : 'No se pudo consultar el cuadro. Volvé a intentarlo.')
      }
    }
    void load()
    return () => { active = false }
  }, [eventId, attempt])

  const current = loaded?.event.id === eventId ? loaded : null
  if (error) return <section className="space-y-4" aria-label="Error al consultar eliminatorias">
    <Alert>{error}</Alert>
    <div className="flex flex-wrap gap-2">
      <Button type="button" onClick={() => setAttempt(value => value + 1)}>Volver a consultar cuadro</Button>
      <Button type="button" variant="secondary" onClick={() => onNavigate({ kind: 'list' })}>Volver a Americanos</Button>
    </div>
  </section>
  if (!current) return <Spinner label="Consultando cuadro…" />
  return <PlayoffsWorkstation key={eventId} initial={current} operations={operations} onNavigate={onNavigate} onDirtyChange={onDirtyChange} />
}

type LoadedPlayoffs = { event: EventDetail; playoffs: PlayoffsResponse }
type SetDraft = { nodeId: number; games_a: string; games_b: string }
type SetAttempt = { node: KnockoutNode; request: SaveKnockoutRequest }

function sameParticipants(first: KnockoutNode, second: KnockoutNode) {
  return first.id === second.id && first.registration_a?.id === second.registration_a?.id && first.registration_b?.id === second.registration_b?.id
}
function matchesAttempt(data: PlayoffsResponse, attempt: SetAttempt) {
  const node = data.nodes.find(candidate => candidate.id === attempt.node.id)
  return Boolean(node && sameParticipants(attempt.node, node) && node.set_complete &&
    node.games_a === attempt.request.games_a && node.games_b === attempt.request.games_b)
}
function draftOf(node: KnockoutNode): SetDraft {
  return { nodeId: node.id, games_a: node.games_a === null ? '' : String(node.games_a), games_b: node.games_b === null ? '' : String(node.games_b) }
}
function sameSavedResult(node: KnockoutNode, draft: SetDraft) {
  return node.set_complete && /^\d+$/.test(draft.games_a) && /^\d+$/.test(draft.games_b) &&
    Number(draft.games_a) === node.games_a && Number(draft.games_b) === node.games_b
}
function validTerminal(first: string, second: string) {
  if (!/^[0-7]$/.test(first) || !/^[0-7]$/.test(second)) return false
  const a = Number(first), b = Number(second)
  if (!Number.isSafeInteger(a) || !Number.isSafeInteger(b)) return false
  return (a === 6 && b <= 4) || (b === 6 && a <= 4) || (a === 7 && (b === 5 || b === 6)) || (b === 7 && (a === 5 || a === 6))
}

function PlayoffsWorkstation({ initial, operations, onNavigate, onDirtyChange }: {
  initial: LoadedPlayoffs
} & Omit<AmericanoPlayoffsPageProps, 'eventId'>) {
  const [current, setCurrent] = useState(initial)
  const currentRef = useRef(initial)
  const [editor, setEditor] = useState<SetDraft | null>(null)
  const editorRef = useRef<SetDraft | null>(null)
  const [busyState, setBusy] = useState(false)
  const busy = useRef(false)
  const unresolved = useRef(false)
  const [comparison, setComparison] = useState<LoadedPlayoffs | null>(null)
  const comparisonRef = useRef<LoadedPlayoffs | null>(null)
  const [needsReconcile, setNeedsReconcile] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [notice, setNotice] = useState('')
  const [courtAttempt, setCourtAttempt] = useState<{ nodeId: number; courtNumber: number } | null>(null)
  const lastAttempt = useRef<SetAttempt | null>(null)
  const active = useRef(true)
  const generation = useRef(0)
  const scoreInputs = useRef(new Map<string, HTMLInputElement>())
  const saveButtons = useRef(new Map<number, HTMLButtonElement>())
  const focusAfterSave = useRef<string | null>(null)
  useLayoutEffect(() => {
    if (busyState || !focusAfterSave.current) return
    scoreInputs.current.get(focusAfterSave.current)?.focus()
    focusAfterSave.current = null
  }, [current, busyState])
  const ports = useRef({ operations, onDirtyChange })
  useLayoutEffect(() => { ports.current = { operations, onDirtyChange } }, [operations, onDirtyChange])
  useLayoutEffect(() => {
    active.current = true
    return () => { active.current = false; generation.current += 1 }
  }, [])
  function dirtyNow() {
    const draft = editorRef.current
    if (!draft) return false
    const node = currentRef.current.playoffs.nodes.find(candidate => candidate.id === draft.nodeId)
    if (!node) return true
    const baseline = draftOf(node)
    return draft.games_a !== baseline.games_a || draft.games_b !== baseline.games_b
  }
  const actions = useRef<Pick<DirtyNavigationDraft, 'save' | 'discard'>>({ save: async () => false, discard: () => false })
  const saveDescriptor = useCallback(() => actions.current.save(), [])
  const discardDescriptor = useCallback(() => actions.current.discard(), [])
  const descriptor = useMemo<DirtyNavigationDraft>(() => ({
    get dirty() { return active.current && dirtyNow() },
    get pending() { return active.current && (busy.current || unresolved.current) },
    save: saveDescriptor, discard: discardDescriptor,
  // Keep action identities stable, but republish a descriptor after state
  // changes so the provider's already-open dialog updates its disabled state.
  }), [saveDescriptor, discardDescriptor, editor, busyState, needsReconcile, current])
  useLayoutEffect(() => {
    onDirtyChange(descriptor)
    return () => onDirtyChange(null)
  }, [descriptor, onDirtyChange])

  function updateEditor(next: SetDraft | null) {
    // A later explicit GET must never acknowledge an older rejected request
    // and discard values typed since that request.
    lastAttempt.current = null
    editorRef.current = next
    setEditor(next)
    setSaveError(null)
    setNotice('')
  }
  function changeScore(node: KnockoutNode, side: Side, value: string) {
    if (!active.current || busy.current || unresolved.current) return
    const selectedEditor = editorRef.current
    if (selectedEditor && selectedEditor.nodeId !== node.id && dirtyNow()) return
    if (!/^[0-7]?$/.test(value)) { setSaveError('Usá un único dígito del 0 al 7 para los games.'); return }
    const base = selectedEditor?.nodeId === node.id ? selectedEditor : draftOf(node)
    const previous = side === 'a' ? base.games_a : base.games_b
    updateEditor({ ...base, [side === 'a' ? 'games_a' : 'games_b']: value })
    if (previous === '' && value !== '') {
      if (side === 'a') scoreInputs.current.get(`${node.id}:b`)?.focus()
      else requestAnimationFrame(() => saveButtons.current.get(node.id)?.focus())
    }
  }
  function adopt(next: LoadedPlayoffs, keep: boolean) {
    currentRef.current = next
    setCurrent(next)
    setCourtAttempt(null)
    if (!keep) { editorRef.current = null; setEditor(null) }
    comparisonRef.current = null
    setComparison(null)
    unresolved.current = false
    setNeedsReconcile(false)
    lastAttempt.current = null
    setSaveError(null)
  }
  async function loadCanonical(): Promise<LoadedPlayoffs> {
    const eventId = initial.event.id
    const port = ports.current.operations
    const event = await port.loadEvent(eventId)
    if (event.id !== eventId || continuation(event)) throw new Error('El estado del evento cambió. Conservamos tu edición; consultá su estado antes de salir.')
    const playoffs = await port.loadPlayoffs(eventId)
    checkPlayoffs(playoffs, event)
    if (playoffs.revision < currentRef.current.playoffs.revision || playoffs.groups_revision !== currentRef.current.playoffs.groups_revision) throw new Error('La respuesta no conserva la revisión del cuadro y sus grupos cerrados.')
    return { event, playoffs }
  }
  async function compareWithServer(attempt: SetAttempt | null, started: number) {
    const uncertainWrite = unresolved.current || attempt !== null
    comparisonRef.current = null
    setComparison(null)
    try {
      const canonical = await loadCanonical()
      if (!active.current || generation.current !== started) return false
      if (attempt && matchesAttempt(canonical.playoffs, attempt)) {
        adopt(canonical, false)
        setNotice('Guardado verificado en el servidor.')
        return true
      }
      if (!editorRef.current && !unresolved.current) {
        adopt(canonical, false)
        setNotice('Cuadro actualizado.')
        return true
      }
      comparisonRef.current = canonical
      setComparison(canonical)
      unresolved.current = true
      setNeedsReconcile(true)
      setSaveError('Compará el cuadro del servidor con tu edición. No se reenviaron resultados.')
    } catch (cause) {
      if (active.current && generation.current === started) {
        unresolved.current = uncertainWrite
        setNeedsReconcile(uncertainWrite)
        setSaveError(`${uncertainWrite ? 'No pudimos verificar el guardado.' : 'No pudimos actualizar el cuadro.'} Conservamos los datos y tu edición. ${cause instanceof Error ? cause.message : ''}`)
      }
    }
    return false
  }
  async function persist(nodeId?: number): Promise<boolean> {
    if (!active.current || busy.current || unresolved.current) return false
    const base = currentRef.current
    const targetId = nodeId ?? editorRef.current?.nodeId
    if (!targetId) return false
    const node = base.playoffs.nodes.find(candidate => candidate.id === targetId)
    if (!node) return false
    const existing = editorRef.current
    if (existing && existing.nodeId !== targetId && dirtyNow()) return false
    const draft = existing?.nodeId === targetId ? existing : draftOf(node)
    if (sameSavedResult(node, draft)) return false
    if (existing?.nodeId !== targetId) updateEditor(draft)
    if (!node?.can_edit || !node.registration_a || !node.registration_b) return false
    if (!validTerminal(draft.games_a, draft.games_b)) {
      setSaveError('Resultado inválido. Usá 6-0 a 6-4, 7-5 o 7-6, o sus inversos.')
      if (!/^\d+$/.test(draft.games_a)) scoreInputs.current.get(`${node.id}:a`)?.focus()
      else if (!/^\d+$/.test(draft.games_b)) scoreInputs.current.get(`${node.id}:b`)?.focus()
      else scoreInputs.current.get(`${node.id}:a`)?.focus()
      return false
    }
    const attempt: SetAttempt = { node, request: { expected_revision: base.playoffs.revision, games_a: Number(draft.games_a), games_b: Number(draft.games_b), set_complete: true } }
    const started = generation.current
    lastAttempt.current = attempt
    busy.current = true
    setBusy(true)
    setSaveError(null)
    setNotice('Guardando resultado…')
    try {
      const data = await ports.current.operations.saveKnockout(base.event.id, node.id, attempt.request)
      if (!active.current || generation.current !== started) return false
      checkPlayoffs(data, base.event)
      if (data.revision !== base.playoffs.revision + 1 || data.groups_revision !== base.playoffs.groups_revision || !matchesAttempt(data, attempt)) throw new Error('La respuesta no permite verificar este resultado.')
      const next = [...data.nodes].sort((a, b) => stages.indexOf(a.stage) - stages.indexOf(b.stage) || a.slot - b.slot)
        .find(candidate => candidate.id !== node.id && candidate.can_edit && !candidate.set_complete)
      focusAfterSave.current = next ? `${next.id}:a` : null
      adopt({ event: base.event, playoffs: data }, false)
      setNotice('Resultado guardado.')
      return true
    } catch (cause) {
      if (!active.current || generation.current !== started) return false
      setNotice('')
      setSaveError(cause instanceof Error ? cause.message : 'No se pudo guardar. Tu edición sigue acá.')
      const status = statusOf(cause)
      if (status === 409 || status === 0 || status === undefined || (typeof status === 'number' && status >= 500)) {
        unresolved.current = true
        setNeedsReconcile(true)
        return await compareWithServer(attempt, started)
      }
      lastAttempt.current = null
      return false
    } finally {
      busy.current = false
      if (active.current && generation.current === started) setBusy(false)
    }
  }
  async function assignCourt(node: KnockoutNode, courtNumber: number) {
    const assign = ports.current.operations.assignKnockoutCourt
    if (!assign || !active.current || busy.current || unresolved.current || dirtyNow() || node.set_complete) return
    const base = currentRef.current
    const started = generation.current
    busy.current = true
    setBusy(true)
    setSaveError(null)
    setNotice('Guardando cancha…')
    setCourtAttempt({ nodeId: node.id, courtNumber })
    try {
      const data = await assign(base.event.id, node.id, { expected_revision: base.playoffs.revision, court_number: courtNumber })
      if (!active.current || generation.current !== started) return
      checkPlayoffs(data, base.event)
      if (data.revision !== base.playoffs.revision + 1 || data.groups_revision !== base.playoffs.groups_revision || data.nodes.find(candidate => candidate.id === node.id)?.court_number !== courtNumber) throw new Error('No se pudo verificar la cancha guardada.')
      adopt({ event: { ...base.event, revision: data.revision }, playoffs: data }, false)
      setNotice('Cancha actualizada.')
    } catch (cause) {
      if (!active.current || generation.current !== started) return
      setSaveError(cause instanceof Error ? cause.message : 'No se pudo guardar la cancha.')
      if (statusOf(cause) !== 422) {
        unresolved.current = true
        setNeedsReconcile(true)
        await compareWithServer(null, started)
      } else setCourtAttempt(null)
    } finally {
      if (active.current && generation.current === started) { busy.current = false; setBusy(false) }
    }
  }

  function discard() {
    if (!active.current || busy.current || (unresolved.current && !comparisonRef.current)) return false
    if (comparisonRef.current) adopt(comparisonRef.current, false)
    else { editorRef.current = null; setEditor(null); lastAttempt.current = null; setSaveError(null) }
    setNotice('Edición descartada. Se restauró el cuadro guardado.')
    return true
  }
  useLayoutEffect(() => { actions.current = { save: persist, discard } })
  async function refresh() {
    if (!active.current || busy.current) return
    busy.current = true
    setBusy(true)
    const started = generation.current
    try { await compareWithServer(lastAttempt.current, started) }
    finally { busy.current = false; if (active.current && generation.current === started) setBusy(false) }
  }
  const selected = editor ? current.playoffs.nodes.find(node => node.id === editor.nodeId) : null
  const canonicalNode = editor && comparison ? comparison.playoffs.nodes.find(node => node.id === editor.nodeId) : null
  const canKeep = Boolean(selected && canonicalNode && sameParticipants(selected, canonicalNode) && canonicalNode.can_edit)
  const { event, playoffs } = current
  const orderedStages = stages.filter(stage => playoffs.nodes.some(node => node.stage === stage))
  const bracketRows = playoffs.start_stage === 'quarterfinal' ? 8 : playoffs.start_stage === 'semifinal' ? 4 : 2
  const gridColumns = orderedStages.flatMap((_, index) => index < orderedStages.length - 1
    ? ['minmax(260px,1fr)', '48px'] : ['minmax(260px,1fr)']).join(' ')
  const champion = playoffs.champion
  const lastRound = positive(event.total_rounds) && event.saved_rounds === event.total_rounds && event.max_unlocked_round === event.total_rounds ? event.total_rounds : null

  function connectorPaths(stageIndex: number) {
    const fromStage = orderedStages[stageIndex]!
    const toStage = orderedStages[stageIndex + 1]!
    const sources = playoffs.nodes.filter(node => node.stage === fromStage)
    const destinations = playoffs.nodes.filter(node => node.stage === toStage)
    return destinations.flatMap(destination => {
      const incoming = sources.filter(source => source.next_match_id === destination.id).sort((a, b) => a.slot - b.slot)
      const ys = incoming.map(source => ((source.slot - 0.5) / sources.length) * 100)
      const destinationY = ((destination.slot - 0.5) / destinations.length) * 100
      if (ys.length >= 2) return [
        ...ys.map(y => `M 0 ${y} H 50`),
        `M 50 ${Math.min(...ys)} V ${Math.max(...ys)}`,
        `M 50 ${destinationY} H 100`,
      ]
      if (ys.length === 1) return [`M 0 ${ys[0]} H 50 V ${destinationY} H 100`]
      return []
    })
  }

  return <div className="space-y-5">
    <header className="flex flex-wrap items-end justify-between gap-4 border-b border-ink-200 pb-5">
      <div>
        <p className="text-sm font-medium text-ink-500">{playoffs.event_name}</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-ink-900">Playoffs</h1>
      </div>
      <Button type="button" variant="secondary" disabled={busyState} onClick={() => void refresh()}>Actualizar</Button>
    </header>

    {champion ? <section aria-label="Campeón" className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3">
      <span className="mr-2 text-xs font-semibold uppercase tracking-wide text-emerald-800">Campeón</span>
      <span className="font-semibold text-emerald-950">{pairName(champion)}</span>
    </section> : null}

    {saveError ? <p role="alert" className="text-sm text-red-700">{saveError}</p> : null}
    {notice ? <p role="status" aria-live="polite" className="text-sm text-ink-600">{notice}</p> : null}
    {needsReconcile ? <section aria-label="Comparación del cuadro" className="space-y-3 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-ink-800">
      <h2 className="font-semibold">No se pudo verificar el guardado</h2>
      {comparison ? <>
        <p>El cuadro guardado está en revisión {comparison.playoffs.revision}. {courtAttempt ? 'Revisá la cancha guardada antes de volver a cambiarla.' : 'Tu edición sigue en el formulario.'}</p>
        {courtAttempt ? <p>Cancha solicitada: {courtAttempt.courtNumber} · Cancha guardada: {comparison.playoffs.nodes.find(node => node.id === courtAttempt.nodeId)?.court_number ?? 'Sin asignar'}. No se reenvió el cambio.</p> : null}
        {canonicalNode ? <p>{nodeName(canonicalNode)}: {canonicalNode.registration_a ? pairName(canonicalNode.registration_a) : 'Participante pendiente'} · {canonicalNode.games_a ?? '—'} – {canonicalNode.games_b ?? '—'} · {canonicalNode.registration_b ? pairName(canonicalNode.registration_b) : 'Participante pendiente'}</p> : null}
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="secondary" disabled={busyState} onClick={() => { if (!busy.current && comparisonRef.current) { adopt(comparisonRef.current, false); setNotice('Se adoptó el cuadro guardado.') } }}>Usar cuadro guardado</Button>
          {!courtAttempt ? <Button type="button" variant="secondary" disabled={busyState || !canKeep} onClick={() => {
            if (busy.current || !canKeep || !comparisonRef.current) return
            adopt(comparisonRef.current, true)
            setNotice('Edición conservada. Revisá el resultado y guardalo para reintentar.')
          }}>Conservar mi edición</Button> : null}
        </div>
        {!canKeep && !courtAttempt ? <p>Este resultado ya no admite correcciones.</p> : null}
      </> : <p>Consultá el servidor antes de volver a guardar.</p>}
      <Button type="button" variant="secondary" disabled={busyState} onClick={() => void refresh()}>Volver a comprobar</Button>
    </section> : null}

    <section aria-label="Llave de eliminatorias" className="overflow-x-auto pb-2">
      <div className="min-w-max">
        <div className="grid gap-x-0" style={{ gridTemplateColumns: gridColumns }}>
          {orderedStages.map((stage, stageIndex) => <h2 key={stage} className="border-b border-ink-200 pb-2 text-sm font-semibold text-ink-800"
            style={{ gridColumn: `${stageIndex * 2 + 1}` }}>{stageHeadings[stage]}</h2>)}
        </div>
        <div className="relative grid pt-3" style={{
          gridTemplateColumns: gridColumns,
          gridTemplateRows: `repeat(${bracketRows}, minmax(96px, 1fr))`,
          minHeight: `${bracketRows * 96}px`,
        }}>
          {orderedStages.map((stage, stageIndex) => {
            const stageNodes = playoffs.nodes.filter(node => node.stage === stage).sort((a, b) => a.slot - b.slot)
            const rowsPerMatch = bracketRows / stageNodes.length
            return stageNodes.map(node => {
              const rowStart = 1 + (node.slot - 1) * rowsPerMatch
              const activeEditor = editor?.nodeId === node.id
              const otherDraftBlocks = Boolean(editor && !activeEditor && dirtyNow())
              const canEnterScore = node.can_edit && Boolean(node.registration_a && node.registration_b)
              const draft = activeEditor ? editor : draftOf(node)
              const unchangedSavedResult = sameSavedResult(node, draft)
              const invalidScore = Boolean(draft.games_a && draft.games_b && !validTerminal(draft.games_a, draft.games_b))
              return <article key={node.id} id={`americano-match-${node.id}`} aria-label={nodeName(node)} className="relative z-10 self-center px-1"
                style={{ gridColumn: `${stageIndex * 2 + 1}`, gridRow: `${rowStart} / span ${rowsPerMatch}` }}>
                <Card className="overflow-hidden p-0 shadow-sm">
                  <h3 className="border-b border-ink-200 bg-ink-50 px-3 py-2 text-xs font-semibold text-ink-700">{nodeName(node)}</h3>
                  <div className="border-b border-ink-200 px-3 py-2">
                    {operations.assignKnockoutCourt && !node.set_complete && playoffs.state === 'playoffs' ? <label className="flex items-center gap-2 text-xs text-ink-600">
                      Cancha sugerida
                      <Select aria-label={`Cancha de ${nodeName(node)}`} value={node.court_number ?? ''}
                        disabled={busyState || needsReconcile || dirtyNow()}
                        onChange={e => void assignCourt(node, Number(e.target.value))}>
                        {!node.court_number ? <option value="" disabled>Sin asignar</option> : null}
                        {playoffs.courts.map(court => <option key={court} value={court}>Cancha {court}</option>)}
                      </Select>
                    </label> : <p className="text-xs font-medium text-emerald-800">{node.court_number ? `Cancha ${node.court_number}` : 'Cancha sin asignar'}</p>}
                    {!node.set_complete ? <p className="mt-1 text-[11px] text-ink-500">Según disponibilidad; pueden jugarse en distintos turnos.</p> : null}
                  </div>
                  <div className="divide-y divide-ink-200">
                    {(['a', 'b'] as Side[]).map(side => {
                      const registration = side === 'a' ? node.registration_a : node.registration_b
                      const source = playoffs.nodes.find(candidate => candidate.next_match_id === node.id && candidate.next_side === side)
                      const score = side === 'a' ? node.games_a : node.games_b
                      const scoreValue = side === 'a' ? draft.games_a : draft.games_b
                      const winner = registration && node.winner_registration_id === registration.id
                      const inputKey = `${node.id}:${side}`
                      return <div key={side} className={`grid grid-cols-[minmax(0,1fr)_3.5rem] items-center gap-2 px-3 py-2.5 ${winner ? 'bg-emerald-50/70' : 'bg-surface'}`}>
                        <div className="min-w-0">
                          <p className={`break-words text-sm ${winner ? 'font-semibold text-emerald-950' : 'text-ink-800'}`}>
                            {registration ? pairName(registration) : source ? `Ganador de ${nodeName(source)}` : 'Participante pendiente'}
                          </p>
                          {winner ? <span className="text-[11px] font-semibold uppercase tracking-wide text-emerald-700">Ganador</span> : null}
                        </div>
                        {canEnterScore ? <input
                          ref={element => { if (element) scoreInputs.current.set(inputKey, element); else scoreInputs.current.delete(inputKey) }}
                          type="text" inputMode="numeric" pattern="[0-7]" maxLength={1} autoComplete="off"
                          aria-label={`Games de ${registration ? pairName(registration) : `lado ${side.toUpperCase()}`} · ${nodeName(node)}`}
                          aria-invalid={activeEditor && (invalidScore || Boolean(saveError))} aria-describedby={`score-error-${node.id}`}
                          disabled={busyState || needsReconcile || otherDraftBlocks} value={scoreValue}
                          onFocus={event => event.currentTarget.select()}
                          onChange={event => changeScore(node, side, event.currentTarget.value)}
                          onPaste={event => { event.preventDefault(); changeScore(node, side, event.clipboardData.getData('text')) }}
                          onKeyDown={event => {
                            if (event.key === 'Backspace' || event.key === 'Delete') { event.preventDefault(); changeScore(node, side, '') }
                            if (event.key === 'Enter') {
                              event.preventDefault()
                              if (side === 'a') scoreInputs.current.get(`${node.id}:b`)?.focus()
                              else void persist(node.id)
                            }
                          }}
                          className={`h-14 w-14 rounded-md border bg-surface text-center text-2xl font-semibold tabular-nums text-ink-900 outline-none focus:ring-2 focus:ring-ink-800 focus:ring-offset-2 disabled:bg-ink-50 ${invalidScore ? 'border-red-600' : 'border-ink-300'}`} />
                          : <span aria-label={`Games lado ${side.toUpperCase()}`} className="text-center text-xl font-semibold tabular-nums text-ink-900">{score ?? '—'}</span>}
                      </div>
                    })}
                  </div>
                  {canEnterScore ? <p id={`score-error-${node.id}`} className={invalidScore ? 'px-3 py-2 text-xs text-red-700' : 'sr-only'}>
                    {invalidScore ? 'Resultado inválido. Usá 6-0 a 6-4, 7-5 o 7-6, o sus inversos.' : 'Un dígito por casillero, del 0 al 7. Al completar el resultado, guardá para continuar al siguiente partido.'}
                  </p> : null}
                  {canEnterScore ? <div className="flex items-center gap-2 border-t border-ink-200 px-3 py-2.5">
                    <Button ref={element => { if (element) saveButtons.current.set(node.id, element); else saveButtons.current.delete(node.id) }} type="button" disabled={busyState || needsReconcile || otherDraftBlocks || unchangedSavedResult || !validTerminal(draft.games_a, draft.games_b)}
                      onClick={() => void persist(node.id)}>
                      {busyState && activeEditor ? 'Guardando…' : unchangedSavedResult ? 'Guardado' : node.set_complete ? 'Guardar corrección' : 'Guardar resultado'}
                    </Button>
                    {activeEditor ? <Button type="button" variant="ghost" disabled={busyState || needsReconcile} onClick={() => discard()}>Cancelar</Button> : null}
                  </div> : node.edit_block_reason === 'participants_pending' ? <p className="border-t border-ink-200 px-3 py-2 text-xs text-ink-500">Esperando participantes</p>
                    : node.edit_block_reason === 'descendant_played' ? <p className="border-t border-ink-200 px-3 py-2 text-xs text-ink-500">Resultado bloqueado</p> : null}
                </Card>
              </article>
            })
          })}
          {orderedStages.slice(0, -1).map((_stage, stageIndex) => {
            const paths = connectorPaths(stageIndex)
            return <svg key={`connector-${stageIndex}`} aria-hidden="true" viewBox="0 0 100 100" preserveAspectRatio="none"
              className="pointer-events-none z-0 h-full w-full self-stretch overflow-visible text-ink-300"
              style={{ gridColumn: `${stageIndex * 2 + 2}`, gridRow: `1 / span ${bracketRows}` }}>
              {paths.map((path, pathIndex) => <path key={pathIndex} d={path} fill="none" stroke="currentColor" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />)}
            </svg>
          })}
        </div>
      </div>
    </section>

    <nav aria-label="Consultas del evento" className="flex flex-wrap gap-2 border-t border-ink-200 pt-4">
      {lastRound ? <Button type="button" variant="secondary" onClick={() => onNavigate({ kind: 'round', event_id: event.id, round_number: lastRound })}>Consultar rondas y tablas</Button> : null}
      <Button type="button" variant="ghost" onClick={() => onNavigate({ kind: 'list' })}>Volver a Americanos</Button>
    </nav>
  </div>
}
