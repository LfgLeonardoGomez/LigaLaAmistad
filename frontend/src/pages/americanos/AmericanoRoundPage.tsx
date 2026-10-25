import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import type {
  AmericanoNavigation, AmericanoRoundPageProps, DirtyNavigationDraft, Registration,
  RoundResponse, SaveRoundRequest, Side, StandingsResponse,
} from '../../api/americano-types'
import { ScoreRow } from '../../components/americanos/ScoreRow'
import { StandingsDrawer } from '../../components/americanos/StandingsDrawer'
import { Alert, Button, Card, Spinner } from '../../components/ui'
import { useRoundDraft } from './useRoundDraft'

function pairName(registration: Registration) {
  return `${registration.player1_name} / ${registration.player2_name}`
}

function messageOf(error: unknown) {
  return error instanceof Error ? error.message : 'No se pudo completar la operación. Conservamos tu edición.'
}

function statusOf(error: unknown) {
  return typeof error === 'object' && error !== null && 'status' in error ? error.status : undefined
}

function matchesRequest(round: RoundResponse, request: SaveRoundRequest) {
  return round.saved && round.matches.length === request.results.length && request.results.every(result =>
    round.matches.some(match => match.id === result.match_id && match.games_a === result.games_a && match.games_b === result.games_b))
}

function isReadOnly(round: RoundResponse) {
  return round.read_only || round.locked || !['groups', 'review'].includes(round.state)
}

function sameMatchMembership(previous: RoundResponse, canonical: RoundResponse) {
  return previous.matches.length === canonical.matches.length && new Set(canonical.matches.map(match => match.id)).size === canonical.matches.length &&
    previous.matches.every(match => canonical.matches.some(current => current.id === match.id && current.zone_id === match.zone_id &&
      current.registration_a.id === match.registration_a.id && current.registration_b.id === match.registration_b.id))
}

export function AmericanoRoundPage(props: AmericanoRoundPageProps) {
  const { eventId, roundNumber, operations } = props
  const [loaded, setLoaded] = useState<RoundResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)
  const navigateRef = useRef(props.onNavigate)
  const operationsRef = useRef(operations)
  useLayoutEffect(() => {
    navigateRef.current = props.onNavigate
    operationsRef.current = operations
  }, [props.onNavigate, operations])

  useEffect(() => {
    let active = true
    const port = operationsRef.current
    setLoaded(null)
    setError(null)
    async function load() {
      try {
        if (!Number.isSafeInteger(eventId) || eventId < 1 || !Number.isSafeInteger(roundNumber) || roundNumber < 1) {
          navigateRef.current({ kind: 'event', event_id: eventId })
          return
        }
        const round = await port.loadRound(eventId, roundNumber)
        if (!active) return
        if (round.locked) {
          navigateRef.current({ kind: 'event', event_id: eventId })
          return
        }
        if (round.event_id !== eventId || round.number !== roundNumber || round.matches.length > 6 || round.matches.length === 0 ||
          round.matches.some(match => !round.zones.some(zone => zone.id === match.zone_id))) {
          throw new Error('La ronda recibida no corresponde al puesto de carga. Volvé a abrir el evento.')
        }
        setLoaded(round)
      } catch (failure) {
        if (!active) return
        if (statusOf(failure) === 409 || statusOf(failure) === 404) {
          try {
            const event = await port.loadEvent(eventId)
            if (active) navigateRef.current({ ...event.continuation, event_id: event.id })
            return
          } catch (continuationError) {
            if (active) setError(messageOf(continuationError))
            return
          }
        }
        setError(messageOf(failure))
      }
    }
    void load()
    return () => { active = false }
  }, [eventId, roundNumber, attempt])

  if (error) return <div className="space-y-4"><Alert>{error}</Alert><Button type="button" onClick={() => setAttempt(value => value + 1)}>Volver a cargar ronda</Button></div>
  if (!loaded || loaded.event_id !== eventId || loaded.number !== roundNumber) return <Spinner label="Cargando ronda…" />
  return <RoundWorkstation key={`${eventId}:${roundNumber}`} {...props} initialRound={loaded} />
}

function RoundWorkstation({ initialRound, operations, onNavigate, onDirtyChange, mode = 'editable' }: AmericanoRoundPageProps & { initialRound: RoundResponse }) {
  const [round, setRound] = useState(initialRound)
  const consultation = mode === 'consultation'
  const draft = useRoundDraft(round, !consultation)
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState('')
  const [saveError, setSaveError] = useState<string | null>(null)
  const [conflict, setConflict] = useState<RoundResponse | null>(null)
  const [needsReconcile, setNeedsReconcile] = useState(false)
  const reconciliationPending = useRef(false)
  const lastRequest = useRef<SaveRoundRequest | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [standings, setStandings] = useState<StandingsResponse | null>(null)
  const [standingsLoading, setStandingsLoading] = useState(false)
  const [standingsError, setStandingsError] = useState<string | null>(null)
  const [pendingNavigation, setPendingNavigation] = useState<AmericanoNavigation | null>(null)
  const inputs = useRef(new Map<string, HTMLInputElement>())
  const form = useRef<HTMLFormElement>(null)
  const drawerButton = useRef<HTMLButtonElement>(null)
  const drawerReturnFocus = useRef<HTMLElement | null>(null)
  const tableRequest = useRef(0)
  const busy = useRef(false)
  const alive = useRef(true)
  const editable = useRef(!consultation)
  const modeRevision = useRef(0)
  const dirtyCallback = useRef(onDirtyChange)
  const actions = useRef<Pick<DirtyNavigationDraft, 'save' | 'discard'>>({ save: async () => false, discard: () => false })
  const canKeepEdit = !consultation && conflict !== null && !isReadOnly(conflict) && sameMatchMembership(round, conflict)
  const groupsClosed = isReadOnly(consultation ? round : conflict ?? round)
  const readOnly = consultation || groupsClosed || (conflict !== null && !sameMatchMembership(round, conflict))
  const matches = [...round.matches].sort((a, b) => a.display_order - b.display_order)

  useLayoutEffect(() => {
    alive.current = true
    return () => { alive.current = false; tableRequest.current++ }
  }, [])

  useLayoutEffect(() => {
    editable.current = !consultation
    modeRevision.current++
    if (consultation) {
      setConflict(null)
      setNeedsReconcile(false)
      reconciliationPending.current = false
      lastRequest.current = null
      setPendingNavigation(null)
      setNotice('')
      setSaveError(null)
    }
  }, [consultation])

  function canAct() {
    return alive.current && editable.current
  }

  const loadStandings = useCallback(async () => {
    const requestId = ++tableRequest.current
    setStandingsLoading(true)
    setStandingsError(null)
    try {
      const result = await operations.loadStandings(initialRound.event_id)
      if (alive.current && requestId === tableRequest.current) setStandings(result)
    } catch (error) {
      if (alive.current && requestId === tableRequest.current) setStandingsError(messageOf(error))
    } finally {
      if (alive.current && requestId === tableRequest.current) setStandingsLoading(false)
    }
  }, [operations, initialRound.event_id])

  function accept(canonical: RoundResponse, savedStandings?: StandingsResponse) {
    setRound(canonical)
    draft.accept(canonical)
    // The integration guard must see clean state before its awaited save() resolves.
    publishClean()
    setConflict(null)
    setNeedsReconcile(false)
    reconciliationPending.current = false
    setSaveError(null)
    lastRequest.current = null
    // A late drawer GET must not replace the newer table returned with a successful PUT.
    tableRequest.current++
    setStandings(savedStandings ?? null)
    setStandingsLoading(false)
    setStandingsError(null)
    if (!savedStandings && drawerOpen) void loadStandings()
  }

  async function reconcile(request: SaveRoundRequest): Promise<RoundResponse | null> {
    if (!canAct()) return null
    const revision = modeRevision.current
    setConflict(null)
    try {
      const canonical = await operations.loadRound(round.event_id, round.number)
      if (!canAct() || revision !== modeRevision.current) return null
      if (canonical.event_id !== round.event_id || canonical.number !== round.number || canonical.matches.length === 0 || canonical.matches.length > 6 ||
        canonical.matches.some(match => !canonical.zones.some(zone => zone.id === match.zone_id))) throw new Error('No se pudo verificar esta ronda.')
      const editStillMatches = draft.rows.length === request.results.length && draft.rows.every(row =>
        request.results.some(result => result.match_id === row.match_id && String(result.games_a) === row.games_a && String(result.games_b) === row.games_b))
      if (sameMatchMembership(round, canonical) && matchesRequest(canonical, request) && editStillMatches) {
        accept(canonical)
        setNotice('Guardado verificado con la ronda del servidor.')
        return canonical
      }
      setConflict(canonical)
      setSaveError('La ronda del servidor difiere de tu edición. Compará los resultados antes de continuar; no se reenviaron cambios.')
    } catch (error) {
      if (canAct() && revision === modeRevision.current) setSaveError(`No pudimos verificar el guardado. Tu edición sigue acá. ${messageOf(error)}`)
    }
    return null
  }

  async function persist(): Promise<RoundResponse | null> {
    if (!canAct() || busy.current || readOnly || reconciliationPending.current) return null
    const revision = modeRevision.current
    const request = draft.validate()
    if (!request) {
      setSaveError('Completá todos los marcadores para guardar la ronda.')
      const missing = draft.rows.flatMap(row => (['a', 'b'] as const).map(side => ({ row, side })))
        .find(({ row, side }) => row[side === 'a' ? 'games_a' : 'games_b'] === '')
      if (missing) inputs.current.get(`${missing.row.match_id}:${missing.side}`)?.focus()
      return null
    }
    busy.current = true
    setSaving(true)
    setNotice('Guardando ronda…')
    setSaveError(null)
    lastRequest.current = request
    try {
      const response = await operations.saveRound(round.event_id, round.number, request)
      if (!canAct() || revision !== modeRevision.current) return null
      if (response.round.event_id !== round.event_id || response.round.number !== round.number || !matchesRequest(response.round, request)) {
        throw new Error('La respuesta no permite verificar el guardado. Conservamos tu edición.')
      }
      accept(response.round, response.standings)
      setNotice('Ronda guardada.')
      return response.round
    } catch (error) {
      if (!canAct() || revision !== modeRevision.current) return null
      setNotice('')
      setSaveError(messageOf(error))
      const status = statusOf(error)
      if (status === 0 || status === 409 || status === undefined || (typeof status === 'number' && status >= 500)) {
        reconciliationPending.current = true
        setNeedsReconcile(true)
        return await reconcile(request)
      }
      return null
    } finally {
      busy.current = false
      if (alive.current) setSaving(false)
    }
  }

  function discard(): boolean {
    if (!canAct() || busy.current || (reconciliationPending.current && !conflict)) return false
    if (conflict) accept(conflict)
    else draft.reset()
    publishClean()
    setSaveError(null)
    setNotice('Edición descartada. Se restauró la ronda guardada.')
    return true
  }

  function keepEdit() {
    if (!canAct() || busy.current || !conflict || !canKeepEdit) return
    setRound(conflict)
    draft.rebase(conflict)
    setConflict(null)
    setNeedsReconcile(false)
    reconciliationPending.current = false
    lastRequest.current = null
    setSaveError(null)
    setNotice('Se conservó tu edición sobre la revisión del servidor. Revisá los marcadores y pulsá Guardar ronda completa para reintentar.')
  }

  useLayoutEffect(() => {
    dirtyCallback.current = onDirtyChange
    actions.current = { save: async () => (await persist()) !== null, discard }
  })
  const saveDescriptor = useCallback(() => actions.current.save(), [])
  const discardDescriptor = useCallback(() => actions.current.discard(), [])
  function publishClean() {
    dirtyCallback.current(canAct() ? { dirty: false, get pending() { return canAct() && (busy.current || reconciliationPending.current) }, save: saveDescriptor, discard: discardDescriptor } : null)
  }
  const descriptor = useMemo<DirtyNavigationDraft>(() => ({
    dirty: draft.dirty, get pending() { return canAct() && (busy.current || reconciliationPending.current) }, save: saveDescriptor, discard: discardDescriptor,
  }), [draft.dirty, saving, needsReconcile, saveDescriptor, discardDescriptor])
  useLayoutEffect(() => {
    onDirtyChange(consultation ? null : descriptor)
    return () => onDirtyChange(null)
  }, [descriptor, consultation, onDirtyChange])
  useLayoutEffect(() => {
    if (consultation) return
    function beforeUnload(event: BeforeUnloadEvent) {
      if (!canAct()) return
      if (!draft.dirty && !busy.current && !reconciliationPending.current) return
      event.preventDefault()
      event.returnValue = ''
    }
    window.addEventListener('beforeunload', beforeUnload)
    return () => window.removeEventListener('beforeunload', beforeUnload)
  }, [draft.dirty, consultation])

  const registerInput = useCallback((matchId: number, side: Side, element: HTMLInputElement | null) => {
    const key = `${matchId}:${side}`
    if (element) inputs.current.set(key, element)
    else inputs.current.delete(key)
  }, [])

  function advance(matchId: number, side: Side) {
    if (!canAct() || readOnly || busy.current) return
    const index = matches.findIndex(match => match.id === matchId)
    const next = side === 'a' ? `${matchId}:b` : matches[index + 1] ? `${matches[index + 1]!.id}:a` : null
    if (next) inputs.current.get(next)?.focus()
    else form.current?.querySelector<HTMLButtonElement>('button[type="submit"]')?.focus()
  }

  function requestNavigation(target: AmericanoNavigation) {
    if (!alive.current) return
    if (target.kind === 'round' && (!Number.isSafeInteger(target.round_number) || target.round_number < 1 ||
      target.round_number > Math.min(round.total_rounds, round.max_unlocked_round))) return
    if (!editable.current) { onNavigate(target); return }
    if (busy.current) return
    if (draft.dirty || reconciliationPending.current) setPendingNavigation(target)
    else onNavigate(target)
  }

  async function saveFromForm() {
    if (!canAct()) return
    const revision = modeRevision.current
    const saved = await persist()
    if (!canAct() || revision !== modeRevision.current || !saved) return
    if (saved.state === 'review' && saved.number === saved.total_rounds) onNavigate({ kind: 'qualification', event_id: saved.event_id })
    else if (saved.number < saved.total_rounds && saved.max_unlocked_round > saved.number)
      onNavigate({ kind: 'round', event_id: saved.event_id, round_number: saved.number + 1 })
  }

  function captureDrawerFocus() {
    drawerReturnFocus.current = document.activeElement instanceof HTMLElement ? document.activeElement : drawerButton.current
  }

  const restLabels = { bye: 'Descanso por ronda impar', capacity: 'Espera por capacidad', zone_finished: 'Zona finalizada' }
  const roundStatus = groupsClosed ? 'Solo lectura · grupos cerrados'
    : consultation ? 'Consulta · carga de resultados todavía no disponible'
      : readOnly ? 'Solo lectura · composición de partidos modificada'
        : draft.dirty || !round.saved ? 'Sin guardar' : 'Guardada'
  const resultsNotice = consultation
    ? groupsClosed ? 'Los resultados de grupos ya no se pueden modificar.' : 'Consulta de resultados guardados. La carga de resultados todavía no está disponible.'
    : notice || (readOnly ? 'Los resultados de grupos ya no se pueden modificar.' : 'Completá los games y guardá toda la ronda.')
  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-5 border-b border-ink-200 pb-5">
        <div>
          <p className="text-sm font-medium text-ink-500">{round.event_name}</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-ink-900">Ronda <span className="tabular-nums">{round.number}/{round.total_rounds}</span></h1>
          <p className="mt-2 text-sm text-ink-600">{roundStatus}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button type="button" variant="secondary" disabled={(!consultation && saving) || round.number <= 1}
            onClick={() => requestNavigation({ kind: 'round', event_id: round.event_id, round_number: round.number - 1 })}>Anterior</Button>
          <Button type="button" variant="secondary" disabled={(!consultation && saving) || round.number >= round.total_rounds || round.number >= round.max_unlocked_round}
            onClick={() => requestNavigation({ kind: 'round', event_id: round.event_id, round_number: round.number + 1 })}>Siguiente</Button>
          {round.state === 'playoffs' || round.state === 'completed' ? <Button type="button" variant="secondary" disabled={!consultation && saving}
            onClick={() => requestNavigation({ kind: 'playoffs', event_id: round.event_id })}>Volver a playoffs</Button> : null}
          <button ref={drawerButton} type="button" onPointerDown={captureDrawerFocus}
            onClick={() => {
              if (!drawerReturnFocus.current?.isConnected) captureDrawerFocus()
              setDrawerOpen(true)
              void loadStandings()
            }}
            className="rounded-md px-3.5 py-2 text-sm font-medium text-ink-700 ring-1 ring-ink-300 hover:bg-ink-50 focus-visible:outline-2 focus-visible:outline-ink-800">Ver tablas</button>
        </div>
      </header>

      <form ref={form} onSubmit={event => { event.preventDefault(); void saveFromForm() }} className="space-y-5" aria-label="Resultados de la ronda">
        <Card className="overflow-hidden">
          <div className="divide-y divide-ink-200">
            {matches.map(match => {
              const row = draft.rows.find(value => value.match_id === match.id)
              const zone = round.zones.find(value => value.id === match.zone_id)
              return row && zone ? (
                <fieldset key={match.id} className="min-w-0" aria-label={`Zona ${zone.label}, partido ${match.display_order}`}>
                  <legend className="sr-only">Zona {zone.label}, partido {match.display_order}</legend>
                  <p className="px-5 pt-3 text-xs font-semibold text-ink-500">Zona {zone.label} <span className="ml-2 font-normal">· Partido {match.display_order}</span></p>
                  <ScoreRow match={match} zoneLabel={zone.label} value={row} readOnly={readOnly || saving} errors={draft.errors[match.id] ?? {}}
                    onChange={(matchId, side, value) => { if (!canAct() || readOnly || busy.current) return; draft.setScore(matchId, side, value); setNotice('') }}
                    onAdvance={advance} onInvalidInput={() => { setSaveError(null); setNotice('Ingresá un solo dígito (0–9).') }} registerInput={registerInput} />
                </fieldset>
              ) : null
            })}
          </div>
        </Card>
        {round.resting.length ? (
          <section aria-label="Parejas que no juegan esta ronda" className="rounded-lg border border-ink-200 px-5 py-4">
            <h2 className="text-sm font-semibold text-ink-700">No juegan esta ronda</h2>
            <ul className="mt-2 grid gap-2 text-sm text-ink-600 sm:grid-cols-2">
              {round.resting.map(rest => <li key={rest.registration.id}><span className="font-medium">{pairName(rest.registration)}</span><span className="ml-2 text-xs">· {restLabels[rest.reason]}</span></li>)}
            </ul>
          </section>
        ) : null}
        {!consultation && saveError ? <Alert>{saveError}</Alert> : null}
        {!consultation && needsReconcile ? (
          <section className="space-y-3 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-ink-800" aria-label="Comparación de ronda">
            {conflict ? <><h2 className="font-semibold">Resultados actuales del servidor · revisión {conflict.revision}</h2>
              <ul className="space-y-1">{[...conflict.matches].sort((a, b) => a.display_order - b.display_order).map(match => <li key={match.id}>{pairName(match.registration_a)} · {match.games_a ?? '—'} – {match.games_b ?? '—'} · {pairName(match.registration_b)}</li>)}</ul>
              <p>Tu edición sigue en los campos de arriba. Usar la ronda del servidor la descarta; conservarla adopta esta revisión sin enviar resultados.</p>
              <div className="flex flex-wrap gap-2">
                <Button type="button" variant="secondary" disabled={saving} onClick={() => { if (!canAct()) return; accept(conflict); setNotice('Se cargó la ronda guardada del servidor.') }}>Usar ronda guardada</Button>
                <Button type="button" variant="secondary" disabled={saving || !canKeepEdit} onClick={keepEdit}>Conservar mi edición</Button>
              </div>
              {!canKeepEdit ? <p>No se puede reintentar: cambió la composición de los partidos o el servidor ya no permite editar esta ronda. Podés consultar tu edición y usar la ronda del servidor.</p> : null}</> : null}
            <Button type="button" variant="secondary" disabled={saving} onClick={async () => {
              if (!canAct() || !lastRequest.current || busy.current) return
              busy.current = true; setSaving(true)
              try { await reconcile(lastRequest.current) } finally { busy.current = false; if (alive.current) setSaving(false) }
            }}>Volver a comprobar guardado</Button>
          </section>
        ) : null}
        <footer className="flex flex-wrap items-center justify-between gap-4">
          <p role="status" aria-live="polite" className="text-sm text-ink-600">{resultsNotice}</p>
          {!readOnly ? <Button type="submit" disabled={saving || needsReconcile}>{saving ? 'Guardando…' : 'Guardar ronda completa'}</Button> : null}
        </footer>
      </form>
      {round.state === 'review' ? <Button type="button" variant="secondary" disabled={!consultation && saving} onClick={() => requestNavigation({ kind: 'qualification', event_id: round.event_id })}>Revisar clasificados</Button> : null}
      <StandingsDrawer open={drawerOpen} standings={standings} loading={standingsLoading} error={standingsError}
        onClose={() => { setDrawerOpen(false); drawerReturnFocus.current = null }} returnFocusTo={drawerReturnFocus.current} />
      {!consultation && pendingNavigation ? <RoundNavigationDialog canSave={!saving && !needsReconcile && !readOnly} canDiscard={!saving && (!needsReconcile || conflict !== null)} onResolve={action => {
        const target = pendingNavigation
        const revision = modeRevision.current
        setPendingNavigation(null)
        // Wait until the native dialog has released focus/inertness before validating.
        requestAnimationFrame(async () => {
          if (!canAct() || revision !== modeRevision.current) return
          const resolved = action === 'discard' ? discard() : action === 'save' ? await persist() : false
          if (resolved && canAct() && revision === modeRevision.current) onNavigate(target)
        })
      }} /> : null}
    </div>
  )
}

function RoundNavigationDialog({ onResolve, canSave, canDiscard }: { onResolve: (action: 'save' | 'discard' | 'cancel') => void; canSave: boolean; canDiscard: boolean }) {
  const ref = useRef<HTMLDialogElement>(null)
  useLayoutEffect(() => {
    const dialog = ref.current
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null
    dialog?.showModal()
    return () => { dialog?.close(); if (previous?.isConnected) previous.focus() }
  }, [])
  return (
    <dialog ref={ref} aria-labelledby="round-navigation-title" aria-modal="true"
      onCancel={event => { event.preventDefault(); onResolve('cancel') }}
      className="m-auto w-full max-w-md rounded-lg border border-ink-200 bg-surface p-6 text-ink-800 shadow-xl backdrop:bg-black/40">
      <h2 id="round-navigation-title" className="text-lg font-semibold text-ink-900">Hay cambios sin guardar</h2>
      <p className="mt-2 text-sm text-ink-600">Guardá la ronda completa, descartá la edición o permanecé en esta ronda. Si hay un guardado sin verificar, primero compará con el servidor.</p>
      <div className="mt-5 flex flex-wrap gap-2">
        <Button type="button" disabled={!canSave} onClick={() => onResolve('save')}>Guardar y continuar</Button>
        <Button type="button" variant="secondary" disabled={!canDiscard} onClick={() => onResolve('discard')}>Descartar y continuar</Button>
        <Button type="button" variant="ghost" onClick={() => onResolve('cancel')}>Permanecer</Button>
      </div>
    </dialog>
  )
}
