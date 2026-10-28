import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import type { AmericanoSetupPageProps, EventDetail, Registration, StartStage, ZoneCount } from '../../api/americano-types'
import { Alert, Button, Card, EmptyState, Field, Input, PageHeader, Select, Spinner } from '../../components/ui'
import { CourtSelector } from './CourtSelector'
import { SetupSteps } from './SetupSteps'
import { GenerateFixtureDialog } from './GenerateFixtureDialog'

const stages = { quarterfinal: 'Cuartos de final', semifinal: 'Semifinales', final: 'Final' }
const states = { draft: 'Borrador', groups: 'Grupos', review: 'Revisión', playoffs: 'Playoffs', completed: 'Finalizado' }
type Mutate = (job: () => Promise<EventDetail>, kind?: 'registration-add' | 'generated') => Promise<boolean>
interface Recovery {
  canonical: EventDetail | null
  additionUncertain: boolean
  useServer: () => void
  keep: () => boolean
}
interface PairDraft { key: number; player1: string; player2: string }

export function AmericanoSetupPage(props: AmericanoSetupPageProps) {
  return <SetupLoader key={props.eventId} {...props} />
}

function SetupLoader({ eventId, operations, onNavigate }: AmericanoSetupPageProps) {
  const [event, setEvent] = useState<EventDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [blocked, setBlocked] = useState(false)
  const [notice, setNotice] = useState('')
  const [reload, setReload] = useState(0)
  const [canonical, setCanonical] = useState<EventDetail | null>(null)
  const [additionUncertain, setAdditionUncertain] = useState(false)
  const [editorVersion, setEditorVersion] = useState(0)
  const [step, setStep] = useState(2)
  const inFlight = useRef(false)
  const generation = useRef(0)
  const initialized = useRef(false)
  const needsReview = useRef(false)
  const generationUncertain = useRef(false)

  function adoptGenerated(next: EventDetail) {
    setEvent(next)
    setEditorVersion((version) => version + 1)
    setCanonical(null)
    generationUncertain.current = false
    needsReview.current = false
    setBlocked(false)
    setError(null)
    setNotice('Fixture generado. Configuración bloqueada.')
    if (next.state === 'groups' && next.total_rounds > 0) {
      onNavigate({ kind: 'round', event_id: next.id, round_number: 1 })
    } else if (next.state === 'review') {
      onNavigate({ kind: 'qualification', event_id: next.id })
    } else onNavigate({ kind: 'event', event_id: next.id })
  }

  useEffect(() => {
    let ignore = false
    generation.current += 1
    setLoading(true)
    setBlocked(true)
    setCanonical(null)
    setError(null)
    setNotice('')
    void operations.loadEvent(eventId).then((next) => {
      if (ignore) return
      if (generationUncertain.current && next.state !== 'draft') {
        adoptGenerated(next)
      } else if (initialized.current) {
        setCanonical(next)
      } else {
        initialized.current = true
        needsReview.current = false
        setEvent(next)
        setBlocked(false)
      }
    }, (cause: unknown) => {
      if (!ignore) setError(cause instanceof Error ? cause.message : 'No se pudo cargar el evento.')
    }).finally(() => { if (!ignore) setLoading(false) })
    return () => { ignore = true; generation.current += 1 }
  }, [eventId, operations, reload])

  const mutate: Mutate = async (job, kind) => {
    if (inFlight.current || loading || blocked || needsReview.current) return false
    const started = generation.current
    inFlight.current = true
    setPending(true)
    setError(null)
    setNotice('')
    try {
      const next = await job()
      if (generation.current !== started) return false
      if (kind === 'generated') { adoptGenerated(next); return true }
      setEvent(next)
      setEditorVersion((version) => version + 1)
      setAdditionUncertain(false)
      generationUncertain.current = false
      setNotice('Cambios guardados.')
      return true
    } catch (cause) {
      if (generation.current === started) {
        const status = typeof cause === 'object' && cause !== null && 'status' in cause ? cause.status : undefined
        const mustReload = status !== 422
        needsReview.current = mustReload
        setBlocked(mustReload)
        if (kind === 'registration-add' && (status === 0 || typeof status !== 'number' || status >= 500)) setAdditionUncertain(true)
        const detail = cause instanceof Error ? cause.message : 'No se pudo guardar.'
        const recovery = mustReload ? ' Conservamos la edición. Recargá el evento para verificar el estado guardado antes de reintentar.' : ''
        setError(`${status === 409 ? 'Conflicto 409. ' : ''}${detail}${recovery}`)
        if (kind === 'generated' && (status === 0 || typeof status !== 'number' || status >= 500)) {
          generationUncertain.current = true
          setCanonical(null)
          try {
            const next = await operations.loadEvent(eventId)
            if (generation.current !== started) return false
            if (next.state !== 'draft') adoptGenerated(next)
            else setCanonical(next)
          } catch (reloadCause) {
            if (generation.current === started) setError(reloadCause instanceof Error ? reloadCause.message : 'No se pudo verificar el evento. Recargá para comprobar si el fixture fue generado.')
          }
        }
      }
      return false
    } finally {
      if (generation.current === started) {
        inFlight.current = false
        setPending(false)
      }
    }
  }

  function reloadEvent() {
    if (inFlight.current || loading) return
    needsReview.current = true
    setBlocked(true)
    setCanonical(null)
    setReload((n) => n + 1)
  }

  function acceptCanonical(keepProposal: boolean): boolean {
    if (!canonical || loading || inFlight.current || (keepProposal && canonical.state !== 'draft')) return false
    setEvent(canonical)
    setCanonical(null)
    needsReview.current = false
    generationUncertain.current = false
    setBlocked(false)
    setError(null)
    setNotice(keepProposal ? 'Edición conservada con la revisión guardada. Guardá explícitamente para enviarla.' : 'Datos guardados adoptados; edición local descartada.')
    if (!keepProposal) {
      setEditorVersion((version) => version + 1)
      setAdditionUncertain(false)
    }
    return true
  }

  return <div className="space-y-5">
    <PageHeader title={event?.name ?? 'Configuración de Americano'} description="Prepará parejas, zonas y cupos antes de generar el fixture."
      action={<div className="flex gap-2">
        <Button variant="ghost" onClick={() => onNavigate({ kind: 'list' })}>Americanos</Button>
        <Button variant="secondary" disabled={loading || pending} onClick={reloadEvent}>Recargar evento</Button>
      </div>} />
    {error && <Alert>{error}</Alert>}
    <p role="status" aria-live="polite" className="text-sm text-ink-600">{pending ? 'Guardando…' : notice}</p>
    {loading && <Spinner label="Cargando evento…" />}
    {event ?
      <SetupEditor key={editorVersion} event={event} operations={operations}
        step={step} setStep={setStep}
        onNavigate={onNavigate} eventId={eventId} mutate={mutate} disabled={loading || pending || blocked}
        recovery={{ canonical, additionUncertain, useServer: () => { acceptCanonical(false) }, keep: () => acceptCanonical(true) }} /> :
      !loading && <EmptyState>No se pudo abrir el evento. Usá Recargar evento.</EmptyState>}
  </div>
}

function SetupEditor({ event, operations, onNavigate, mutate, disabled, recovery, step, setStep }: AmericanoSetupPageProps & { event: EventDetail; mutate: Mutate; disabled: boolean; recovery: Recovery; step: number; setStep: (step: number) => void }) {
  const [name, setName] = useState(event.name)
  const [zoneCount, setZoneCount] = useState(event.zone_count)
  const [stage, setStage] = useState(event.start_stage)
  const [generationDialog, setGenerationDialog] = useState(false)
  const [courts, setCourts] = useState(event.courts)
  const [editing, setEditing] = useState<Registration | null>(null)
  const pairSequence = useRef(1)
  const [pairRows, setPairRows] = useState<PairDraft[]>([{ key: 0, player1: '', player2: '' }])
  const zoneA = event.zones.find((zone) => zone.label === 'A')
  const [selected, setSelected] = useState(() => new Set(event.registrations.filter((r) => r.zone_id === zoneA?.id).map((r) => r.id)))
  const frozen = event.state !== 'draft'
  const locked = disabled || frozen
  const configDirty = name !== event.name || zoneCount !== event.zone_count || stage !== event.start_stage || courts.join(',') !== event.courts.join(',')
  const pairDirty = editing !== null || pairRows.length > 1 || pairRows.some((row) => row.player1 !== '' || row.player2 !== '')
  const zonesDirty = event.registrations.some((r) => selected.has(r.id) !== (r.zone_id === zoneA?.id))
  const revision = { expected_revision: event.revision }
  const zoneB = event.zones.find((zone) => zone.label === 'B')
  const previewZone = (registration: Registration) => {
    if (event.zone_count !== 2 || !zonesDirty) return registration.zone_id
    if (selected.has(registration.id)) return zoneA?.id ?? null
    return registration.zone_id === zoneB?.id ? zoneB.id : null
  }
  const a = event.registrations.filter((r) => event.zone_count === 1 || previewZone(r) === zoneA?.id)
  const b = event.zone_count === 2 ? event.registrations.filter((r) => previewZone(r) === zoneB?.id) : []
  const savedUnassigned = event.registrations.some((r) => r.zone_id === null)
  const unassigned = event.zone_count === 2 ? event.registrations.some((r) => previewZone(r) === null) : savedUnassigned
  const hasSavedDistribution = event.zone_count === 2 && event.registrations.some((r) => r.zone_id !== null)
  const total = { quarterfinal: 8, semifinal: 4, final: 2 }[event.start_stage]
  const required = total / event.zone_count
  const dirty = configDirty || pairDirty || zonesDirty
  const { canonical } = recovery
  const canonicalPair = canonical?.registrations.find((r) => r.id === editing?.id)
  const keepBlock = canonical?.state !== 'draft' ? 'El evento ya no es un borrador; no se puede reenviar esta edición.' :
    editing && !canonicalPair ? 'La pareja editada ya no existe. No se puede recrear ni reutilizar su ID.' :
      zonesDirty ? 'El reparto local debe revisarse de nuevo con los datos guardados; no se trasladan asignaciones antiguas.' : null

  function keepProposal() {
    if (!canonical || keepBlock) return
    const dirtyName = name !== event.name
    const dirtyZoneCount = zoneCount !== event.zone_count
    const dirtyStage = stage !== event.start_stage
    if (!recovery.keep()) return
    // Rebase untouched fields only. Never promote stale configuration/zone IDs
    // into a different proposal while preserving a pair's strings and identity.
    if (!dirtyName) setName(canonical.name)
    if (!dirtyZoneCount) setZoneCount(canonical.zone_count)
    if (!dirtyStage) setStage(canonical.start_stage)
    if (courts.join(',') === event.courts.join(',')) setCourts(canonical.courts)
    if (editing && canonicalPair) setEditing(canonicalPair)
    const canonicalZoneA = canonical.zones.find((zone) => zone.label === 'A')
    setSelected(new Set(canonical.registrations.filter((r) => r.zone_id === canonicalZoneA?.id).map((r) => r.id)))
  }

  function resetPair() {
    setEditing(null)
    setPairRows([{ key: pairSequence.current++, player1: '', player2: '' }])
  }
  function saveConfiguration(e: FormEvent) {
    e.preventDefault()
    if (locked || !configDirty || !name.trim() || !courts.length || pairDirty || zonesDirty) return
    void mutate(() => operations.updateEvent(event.id, {
      ...revision, name: name.trim(), zone_count: zoneCount, start_stage: stage, courts,
    }))
  }
  function toggleZoneA(id: number) {
    if (locked || configDirty || pairDirty || !operations.setZones || !event.registrations.some((r) => r.id === id)) return
    setSelected((current) => {
      const next = new Set(current)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }
  function saveZones() {
    const save = operations.setZones
    if (!save || locked || configDirty || pairDirty) return
    const ids = event.zone_count === 1 ? event.registrations.map((r) => r.id) : [...selected]
    if (ids.some((id) => !event.registrations.some((r) => r.id === id))) return
    void mutate(() => save(event.id, { ...revision, zone_count: event.zone_count, zone_a_registration_ids: ids }))
  }
  async function savePair(e: FormEvent) {
    e.preventDefault()
    const registrations = pairRows.map((row) => ({ player1_name: row.player1.trim(), player2_name: row.player2.trim() }))
    if (registrations.some((pair) => !pair.player1_name || !pair.player2_name) || locked || configDirty || zonesDirty) return
    const first = registrations[0]
    if (!first) return
    if (editing) {
      await mutate(() => operations.updateRegistration(event.id, editing.id, { ...revision, ...first }))
    } else if (registrations.length === 1) {
      await mutate(() => operations.addRegistration(event.id, { ...revision, ...first }), 'registration-add')
    } else if (operations.addRegistrations) {
      await mutate(() => operations.addRegistrations!(event.id, { ...revision, registrations }), 'registration-add')
    }
  }
  function discardZoneEdits() {
    setSelected(new Set(event.registrations.filter((r) => r.zone_id === zoneA?.id).map((r) => r.id)))
  }
  function discardSavedZones() {
    if (!operations.clearZones || locked || configDirty || pairDirty) return
    void mutate(() => operations.clearZones!(event.id, revision))
  }
  function generateFixture() {
    if (!operations.generateFixture || locked || dirty || !event.can_generate) return
    setGenerationDialog(true)
  }
  function confirmGeneration() {
    const generate = operations.generateFixture
    if (!generationDialog || !generate || locked || dirty || !event.can_generate) return
    setGenerationDialog(false)
    void mutate(async () => (await generate(event.id, revision)).event, 'generated')
  }

  return <>
    {generationDialog ? <GenerateFixtureDialog name={event.name} pairCount={event.registrations.length} courts={event.courts} hasRounds={event.zones.some(zone => event.registrations.filter(pair => pair.zone_id === zone.id).length >= 2)} onClose={() => setGenerationDialog(false)} onConfirm={confirmGeneration} /> : null}
    <SetupSteps current={step} onChange={setStep} canVisit={(target) => !disabled && !dirty && (target < 3 || event.registrations.length > 0)} />
    {dirty && <p role="status" className="text-sm text-amber-700">Guardá o descartá los cambios de este paso antes de cambiar de paso.</p>}
    {recovery.additionUncertain && <Alert tone="info">La incorporación pudo haberse guardado. Revisá las parejas guardadas antes de volver a agregar: conservar la edición no reenvía nada. Los nombres repetidos son válidos; un nuevo envío explícito puede crear otra pareja.</Alert>}
    {canonical && <section aria-label="Datos guardados del evento" className="space-y-3 rounded-md border border-ink-200 bg-ink-50 p-4">
      <h2 className="font-semibold text-ink-900">Datos guardados del evento</h2>
      <p className="text-sm text-ink-700">{canonical.name} · {states[canonical.state]} · {canonical.zone_count === 1 ? 'Una zona' : 'Dos zonas'} · {stages[canonical.start_stage]} · Revisión {canonical.revision}</p>
      <ul className="space-y-1 text-sm text-ink-700">{canonical.registrations.map((r) => {
        const zone = canonical.zones.find((z) => z.id === r.zone_id)
        return <li key={r.id}>#{r.registration_order} · {r.player1_name} / {r.player2_name} · {zone ? `Zona ${zone.label}` : 'Sin asignar'}</li>
      })}</ul>
      {!canonical.registrations.length && <p className="text-sm text-ink-600">No hay parejas guardadas.</p>}
      <p className="text-sm text-ink-600">Tu propuesta sigue en el formulario. Elegí usar el servidor para descartarla o conservarla con la revisión actual; ninguna opción la envía automáticamente.</p>
      {keepBlock && <p className="text-sm text-amber-700">{keepBlock}</p>}
      <div className="flex gap-2">
        <Button variant="secondary" onClick={recovery.useServer}>Usar datos guardados</Button>
        <Button disabled={keepBlock !== null} onClick={keepProposal}>Conservar mi edición</Button>
      </div>
    </section>}
    {frozen && <Alert tone="info">
      El fixture ya fue generado. Parejas, nombres, zonas y etapa quedan bloqueados según el alcance aprobado; no hay regeneración. Este historial muestra la configuración guardada.
    </Alert>}
    {frozen && <section aria-label="Resumen del fixture" className="space-y-3 rounded-md border border-ink-200 bg-ink-50 p-5">
      <h2 className="font-semibold text-ink-900">Resumen del fixture</h2>
      <p className="text-sm text-ink-700">Estado: {states[event.state]} · Rondas totales: <span className="tabular-nums">{event.total_rounds}</span></p>
      <p className="text-sm text-ink-600">{event.total_rounds > 0 ? 'Podés cargar y corregir resultados de rondas hasta confirmar clasificados.' : 'Este fixture no tiene rondas.'} Al confirmar clasificados se cierran los grupos y se crea el cuadro. Los resultados eliminatorios se cargan allí; una corrección se bloquea si ya se jugó un partido siguiente de esa rama.</p>
      <div className="flex flex-wrap gap-2">
        {event.total_rounds > 0 ? <Button variant="secondary" disabled={disabled}
          onClick={() => onNavigate({ kind: 'round', event_id: event.id, round_number: 1 })}>Abrir rondas</Button> : null}
        <Button variant="secondary" disabled={disabled} onClick={() => onNavigate({ kind: 'event', event_id: event.id })}>Continuar evento</Button>
      </div>
    </section>}
    <section hidden={step !== 1} aria-label="Paso 1: Configuración">
    <Card className="p-5">
      <h2 className="mb-4 font-semibold text-ink-900">01 · Configuración</h2>
      {!frozen ? <form onSubmit={saveConfiguration}>
        <fieldset disabled={locked || pairDirty || zonesDirty} className="grid items-end gap-4 lg:grid-cols-[2fr_1fr_1fr]">
          <Field label="Nombre del evento"><Input required value={name} onChange={(e) => setName(e.target.value)} /></Field>
          <Field label="Cantidad de zonas">
            <Select value={zoneCount} onChange={(e) => setZoneCount(Number(e.target.value) as ZoneCount)}>
              <option value="1">Una zona</option><option value="2">Dos zonas</option>
            </Select>
          </Field>
          <Field label="Inicio de eliminatorias">
            <Select value={stage} onChange={(e) => setStage(e.target.value as StartStage)}>
              {Object.entries(stages).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </Select>
          </Field>
        </fieldset>
        <div className="mt-5"><CourtSelector value={courts} onChange={setCourts} disabled={locked || pairDirty || zonesDirty} /></div>
        <Button className="mt-5" type="submit" disabled={locked || pairDirty || zonesDirty || !configDirty || !name.trim() || !courts.length}>Guardar configuración</Button>
      </form> : <p className="text-sm text-ink-700">{event.name} · {event.zone_count === 1 ? 'Una zona' : 'Dos zonas'} · {stages[event.start_stage]} · Canchas {event.courts.join(', ')}</p>}
      {configDirty && <Button variant="ghost" disabled={disabled} onClick={() => { setName(event.name); setZoneCount(event.zone_count); setStage(event.start_stage); setCourts(event.courts) }}>Descartar configuración</Button>}
      <p className="mt-3 text-xs text-ink-500">Cuartos: 8 clasificados · Semifinales: 4 · Final: 2. En dos zonas, mitad del cupo en cada una. Las seis plantillas de cruces están aprobadas.</p>
    </Card>
    </section>
    <section hidden={step !== 2} aria-label="Paso 2: Parejas">
      <Card className="p-5">
        <h2 className="mb-4 font-semibold text-ink-900">02 · Parejas <span className="text-ink-500 tabular-nums">({event.registrations.length})</span></h2>
        {!frozen && <form onSubmit={savePair}>
          <fieldset disabled={locked || configDirty || zonesDirty} className="space-y-3">
            {pairRows.map((row, index) => <div key={row.key} className="grid items-end gap-3 sm:grid-cols-[1fr_1fr_auto]">
              <Field label={`Pareja ${index + 1} · Jugador 1`}><Input required value={row.player1}
                onChange={(e) => setPairRows((current) => current.map((item) => item.key === row.key ? { ...item, player1: e.target.value } : item))} /></Field>
              <Field label={`Pareja ${index + 1} · Jugador 2`}><Input required value={row.player2}
                onChange={(e) => setPairRows((current) => current.map((item) => item.key === row.key ? { ...item, player2: e.target.value } : item))} /></Field>
              {!editing && pairRows.length > 1 ? <Button type="button" variant="ghost" aria-label={`Quitar pareja ${index + 1}`}
                onClick={() => setPairRows((current) => current.filter((item) => item.key !== row.key))}>Quitar</Button> : null}
            </div>)}
            {!editing && <Button type="button" variant="secondary" disabled={pairRows.some((row) => !row.player1.trim() || !row.player2.trim())}
              onClick={() => setPairRows((current) => [...current, { key: pairSequence.current++, player1: '', player2: '' }])}>Agregar otra pareja</Button>}
            <div className="flex gap-2">
              <Button type="submit" disabled={pairRows.some((row) => !row.player1.trim() || !row.player2.trim()) || (!editing && pairRows.length > 1 && !operations.addRegistrations)}>
                {editing ? 'Guardar pareja' : pairRows.length === 1 ? 'Agregar pareja' : `Agregar ${pairRows.length} parejas`}</Button>
              {pairDirty && <Button type="button" variant="ghost" onClick={resetPair}>Cancelar pareja</Button>}
            </div>
          </fieldset>
        </form>}
        {!event.registrations.length ? <EmptyState>Todavía no hay parejas registradas.</EmptyState> : <ul className="mt-4 divide-y divide-ink-200">
          {event.registrations.map((r) => {
            const zone = event.zones.find((z) => z.id === r.zone_id)
            return <li key={r.id} className="flex items-center justify-between gap-3 py-3 text-sm">
              <div className="min-w-0">
                <span className="break-words font-medium text-ink-900">{r.player1_name} / {r.player2_name}</span>
                <p className="text-xs text-ink-500">#{r.registration_order} · {zone ? `Zona ${zone.label}` : 'Sin asignar'}</p>
              </div>
              {!frozen && <div className="flex shrink-0 gap-1">
                <Button variant="ghost" aria-label={`Editar pareja #${r.registration_order}`} disabled={locked || configDirty || zonesDirty || pairDirty}
                  onClick={() => { setEditing(r); setPairRows([{ key: pairSequence.current++, player1: r.player1_name, player2: r.player2_name }]) }}>Editar</Button>
                <Button variant="ghost" aria-label={`Eliminar pareja #${r.registration_order}`} disabled={locked || configDirty || zonesDirty || pairDirty}
                  onClick={() => void mutate(() => operations.deleteRegistration(event.id, r.id, revision))}>Eliminar</Button>
              </div>}
            </li>
          })}
        </ul>}
      </Card>
    </section>
    <section hidden={step !== 3} aria-label="Paso 3: Zonas">
      <Card className="p-5">
        <h2 className="mb-2 font-semibold text-ink-900">03 · Reparto y vista previa</h2>
        <p className="mb-4 text-sm text-ink-600">{event.zone_count === 1 ? 'Todas las parejas pertenecen a Zona A.' : 'Seleccioná las parejas que van a la zona A.'}</p>
        {!operations.setZones && <p className="mb-3 text-sm text-ink-600">Asignación manual no implementada en este corte.</p>}
        {!operations.randomizeZones && <p className="mb-3 text-sm text-ink-600">Reparto aleatorio no implementado en este corte.</p>}
        {!frozen && <fieldset disabled={locked || configDirty || pairDirty}>
          {event.zone_count === 2 && <>
            <div role="group" aria-label="Seleccionar parejas de Zona A" className="mb-4 grid grid-cols-2 gap-2">
              {event.registrations.map((r) => <Button key={r.id} variant={selected.has(r.id) ? 'primary' : 'secondary'}
                disabled={!operations.setZones} aria-pressed={selected.has(r.id)} aria-label={`Zona A: #${r.registration_order} ${r.player1_name} / ${r.player2_name}`}
                className="justify-start break-words text-left" onClick={() => toggleZoneA(r.id)}>
                #{r.registration_order} · {r.player1_name} / {r.player2_name}
              </Button>)}
            </div>
          </>}
          <div className="mb-4 flex flex-wrap gap-2">
            <Button disabled={!operations.setZones || (event.zone_count === 2 && !zonesDirty && !unassigned)} onClick={saveZones}>Guardar reparto</Button>
            {event.zone_count === 2 && <>
              <Button variant="secondary" disabled={!operations.randomizeZones || zonesDirty || !event.registrations.length}
                onClick={() => { const randomize = operations.randomizeZones; if (randomize && !locked && !configDirty && !pairDirty && !zonesDirty) void mutate(() => randomize(event.id, revision)) }}>Repartir aleatoriamente</Button>
              {zonesDirty && <Button variant="ghost" onClick={discardZoneEdits}>Descartar cambios</Button>}
              {hasSavedDistribution && <Button variant="ghost" disabled={!operations.clearZones || locked || configDirty || pairDirty}
                onClick={discardSavedZones}>Descartar reparto</Button>}
            </>}
          </div>
        </fieldset>}
        <p role="status" className="mb-3 text-xs text-ink-500">{zonesDirty ? 'Reparto sin guardar' : unassigned ? 'Reparto incompleto' : 'Reparto guardado'}{unassigned ? ' · Hay parejas sin asignar.' : ''}</p>
        <div className={`grid gap-3 ${event.zone_count === 2 ? 'grid-cols-2' : ''}`}>
          {[{ label: 'A', pairs: a }, ...(event.zone_count === 2 ? [{ label: 'B', pairs: b }] : [])].map(({ label, pairs }) => <section key={label} aria-label={`Vista previa Zona ${label}`} className="rounded-md border border-ink-200 bg-ink-50 p-3">
            <h3 className="font-semibold text-ink-900">Zona {label} <span className="tabular-nums">· {pairs.length}</span></h3>
            <p className={`my-2 text-xs ${pairs.length < required ? 'text-red-700' : 'text-ink-600'}`}>Cupo {pairs.length < required ? `insuficiente: ${pairs.length} de ${required}` : 'suficiente'} · Clasifican {required}</p>
            <ul className="space-y-2 text-sm text-ink-700">{pairs.map((r) => <li key={r.id} className="break-words">#{r.registration_order} · {r.player1_name} / {r.player2_name}</li>)}</ul>
          </section>)}
        </div>
      </Card>
    </section>
    <section hidden={step !== 4} aria-label="Paso 4: Fixture">
    <Card className="space-y-4 p-5">
      <h2 className="font-semibold text-ink-900">04 · Generar fixture</h2>
      <dl className="grid gap-3 rounded-md bg-ink-50 p-4 text-sm sm:grid-cols-2">
        <div><dt className="text-ink-500">Evento</dt><dd className="font-medium text-ink-900">{event.name}</dd></div>
        <div><dt className="text-ink-500">Parejas y zonas</dt><dd>{event.registrations.length} parejas · {event.zone_count} {event.zone_count === 1 ? 'zona' : 'zonas'}</dd></div>
        <div><dt className="text-ink-500">Canchas</dt><dd>{event.courts.join(', ')} · Hasta {event.courts.length} partidos por ronda</dd></div>
        <div><dt className="text-ink-500">Eliminatorias desde</dt><dd>{stages[event.start_stage]}</dd></div>
      </dl>
      <p className="text-sm text-ink-600">Todos contra todos dentro de cada zona. Los cruces se distribuyen en rondas según las canchas elegidas, con su número real y las parejas libres indicadas. En eliminatorias la cancha sugerida se puede ajustar según disponibilidad.</p>
      {event.configuration_issues.length > 0 && <Alert><ul>{event.configuration_issues.map((issue, i) => <li key={`${issue.code}:${issue.zone_id}:${i}`}>{issue.message}</li>)}</ul></Alert>}
      {dirty && <p className="text-sm text-amber-700">Guardá o descartá la edición activa antes de continuar. La vista previa usa la configuración guardada.</p>}
      {!frozen && <p className="text-sm text-ink-700">Al generar se bloquean la configuración, las canchas y las parejas. No se puede regenerar.</p>}
      {!operations.generateFixture && <p id="fixture-next-cut" className="text-sm text-ink-600">Generación no implementada en este corte; disponible en un próximo corte aunque los cupos sean suficientes.</p>}
      {!frozen && <Button aria-describedby={!operations.generateFixture ? 'fixture-next-cut' : undefined} disabled={!operations.generateFixture || locked || dirty || !event.can_generate} onClick={generateFixture}>Generar fixture</Button>}
    </Card>
    </section>
    <div className="flex items-center justify-between gap-3 border-t border-ink-200 pt-4">
      <Button variant="secondary" disabled={disabled || dirty || step === 1} onClick={() => setStep(step - 1)}>Anterior</Button>
      <span className="text-xs text-ink-500">Paso {step} de 4</span>
      {step < 4 ? <Button disabled={disabled || dirty || (step >= 2 && !event.registrations.length)} onClick={() => setStep(step + 1)}>{step === 3 ? 'Revisar fixture' : 'Siguiente'}</Button> : <span />}
    </div>
  </>
}
