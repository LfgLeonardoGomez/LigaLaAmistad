import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import type { AmericanoSetupPageProps, EventDetail, Registration, StartStage, ZoneCount } from '../../api/americano-types'
import { Alert, Button, Card, EmptyState, Field, Input, PageHeader, Select, Spinner } from '../../components/ui'

const stages = { quarterfinal: 'Cuartos de final', semifinal: 'Semifinales', final: 'Final' }
const states = { draft: 'Borrador', groups: 'Grupos', review: 'Revisión', playoffs: 'Playoffs', completed: 'Finalizado' }
type Mutate = (job: () => Promise<EventDetail>, kind?: 'registration-add' | 'generated') => Promise<boolean>
interface Recovery {
  canonical: EventDetail | null
  additionUncertain: boolean
  useServer: () => void
  keep: () => boolean
}

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
  const inFlight = useRef(false)
  const generation = useRef(0)
  const initialized = useRef(false)
  const needsReview = useRef(false)

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
      if (initialized.current) {
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
      setEvent(next)
      setEditorVersion((version) => version + 1)
      setAdditionUncertain(false)
      setNotice(kind === 'generated' ? 'Fixture generado. Configuración bloqueada.' : 'Cambios guardados.')
      if (kind === 'generated') onNavigate({ ...next.continuation, event_id: next.id })
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
      }
      return false
    } finally { inFlight.current = false; setPending(false) }
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
        onNavigate={onNavigate} eventId={eventId} mutate={mutate} disabled={loading || pending || blocked}
        recovery={{ canonical, additionUncertain, useServer: () => { acceptCanonical(false) }, keep: () => acceptCanonical(true) }} /> :
      !loading && <EmptyState>No se pudo abrir el evento. Usá Recargar evento.</EmptyState>}
  </div>
}

function SetupEditor({ event, operations, mutate, disabled, recovery }: AmericanoSetupPageProps & { event: EventDetail; mutate: Mutate; disabled: boolean; recovery: Recovery }) {
  const [name, setName] = useState(event.name)
  const [zoneCount, setZoneCount] = useState(event.zone_count)
  const [stage, setStage] = useState(event.start_stage)
  const [editing, setEditing] = useState<Registration | null>(null)
  const [player1, setPlayer1] = useState('')
  const [player2, setPlayer2] = useState('')
  const zoneA = event.zones.find((zone) => zone.label === 'A')
  const [selected, setSelected] = useState(() => new Set(event.registrations.filter((r) => r.zone_id === zoneA?.id).map((r) => r.id)))
  const [selectionEdited, setSelectionEdited] = useState(false)
  const frozen = event.state !== 'draft'
  const locked = disabled || frozen
  const configDirty = name !== event.name || zoneCount !== event.zone_count || stage !== event.start_stage
  const pairDirty = editing !== null || player1 !== '' || player2 !== ''
  const unassigned = event.registrations.some((r) => r.zone_id === null)
  const zonesDirty = (selectionEdited && unassigned) || event.registrations.some((r) => selected.has(r.id) !== (r.zone_id === zoneA?.id))
  const revision = { expected_revision: event.revision }
  const a = event.registrations.filter((r) => event.zone_count === 1 || selected.has(r.id))
  const zoneB = event.zones.find((zone) => zone.label === 'B')
  const b = event.zone_count === 2 ? event.registrations.filter((r) => zonesDirty ? !selected.has(r.id) : r.zone_id === zoneB?.id) : []
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
    if (editing && canonicalPair) setEditing(canonicalPair)
    const canonicalZoneA = canonical.zones.find((zone) => zone.label === 'A')
    setSelected(new Set(canonical.registrations.filter((r) => r.zone_id === canonicalZoneA?.id).map((r) => r.id)))
    setSelectionEdited(false)
  }

  function resetPair() { setEditing(null); setPlayer1(''); setPlayer2('') }
  function saveConfiguration(e: FormEvent) {
    e.preventDefault()
    if (locked || !configDirty || !name.trim() || pairDirty || zonesDirty) return
    void mutate(() => operations.updateEvent(event.id, {
      ...revision, name: name.trim(), zone_count: zoneCount, start_stage: stage,
    }))
  }
  function toggleZoneA(id: number) {
    if (locked || configDirty || pairDirty || !operations.setZones || !event.registrations.some((r) => r.id === id)) return
    setSelectionEdited(true)
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
    if (!player1.trim() || !player2.trim() || locked || configDirty || zonesDirty) return
    const request = { ...revision, player1_name: player1.trim(), player2_name: player2.trim() }
    await mutate(() => editing ? operations.updateRegistration(event.id, editing.id, request) : operations.addRegistration(event.id, request), editing ? undefined : 'registration-add')
  }

  return <>
    {recovery.additionUncertain && <Alert tone="info">La incorporación pudo haberse guardado. Revisá las parejas guardadas antes de volver a agregar: conservar la edición no reenvía nada. Los nombres repetidos son válidos; un nuevo envío explícito puede crear otra pareja.</Alert>}
    {canonical && <section aria-label="Datos guardados del evento" className="space-y-3 rounded-md border border-ink-200 bg-ink-50 p-4">
      <h2 className="font-semibold text-ink-900">Datos guardados del evento</h2>
      <p className="text-sm text-ink-700">{canonical.name} · {states[canonical.state]} · {canonical.zone_count === 1 ? 'Una zona' : 'Dos zonas'} · {stages[canonical.start_stage]} · Revisión {canonical.revision}</p>
      <ul className="space-y-1 text-sm text-ink-700">{canonical.registrations.map((r) => {
        const zone = canonical.zones.find((z) => z.id === r.zone_id)
        return <li key={r.id}>#{r.id} · {r.player1_name} / {r.player2_name} · {zone ? `Zona ${zone.label}` : 'Sin asignar'}</li>
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
    <Card className="p-5">
      <h2 className="mb-4 font-semibold text-ink-900">01 · Configuración</h2>
      {!frozen ? <form onSubmit={saveConfiguration}>
        <fieldset disabled={locked || pairDirty || zonesDirty} className="grid items-end gap-4 lg:grid-cols-[2fr_1fr_1fr_auto]">
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
          <Button type="submit" disabled={!configDirty || !name.trim()}>Guardar configuración</Button>
        </fieldset>
      </form> : <p className="text-sm text-ink-700">{event.name} · {event.zone_count === 1 ? 'Una zona' : 'Dos zonas'} · {stages[event.start_stage]}</p>}
      {configDirty && <Button variant="ghost" disabled={disabled} onClick={() => { setName(event.name); setZoneCount(event.zone_count); setStage(event.start_stage) }}>Descartar configuración</Button>}
      <p className="mt-3 text-xs text-ink-500">Cuartos: 8 clasificados · Semifinales: 4 · Final: 2. En dos zonas, mitad del cupo en cada una. Las seis plantillas de cruces están aprobadas.</p>
    </Card>
    <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
      <Card className="p-5">
        <h2 className="mb-4 font-semibold text-ink-900">02 · Parejas <span className="text-ink-500 tabular-nums">({event.registrations.length})</span></h2>
        {!frozen && <form onSubmit={savePair}>
          <fieldset disabled={locked || configDirty || zonesDirty} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <Field label="Jugador 1"><Input required value={player1} onChange={(e) => setPlayer1(e.target.value)} /></Field>
              <Field label="Jugador 2"><Input required value={player2} onChange={(e) => setPlayer2(e.target.value)} /></Field>
            </div>
            <div className="flex gap-2">
              <Button type="submit" disabled={!player1.trim() || !player2.trim()}>{editing ? 'Guardar pareja' : 'Agregar pareja'}</Button>
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
                <p className="text-xs text-ink-500">#{r.id} · {zone ? `Zona ${zone.label}` : 'Sin asignar'}</p>
              </div>
              {!frozen && <div className="flex shrink-0 gap-1">
                <Button variant="ghost" aria-label={`Editar pareja #${r.id}`} disabled={locked || configDirty || zonesDirty || pairDirty}
                  onClick={() => { setEditing(r); setPlayer1(r.player1_name); setPlayer2(r.player2_name) }}>Editar</Button>
                <Button variant="ghost" aria-label={`Eliminar pareja #${r.id}`} disabled={locked || configDirty || zonesDirty || pairDirty}
                  onClick={() => void mutate(() => operations.deleteRegistration(event.id, r.id, revision))}>Eliminar</Button>
              </div>}
            </li>
          })}
        </ul>}
      </Card>
      <Card className="p-5">
        <h2 className="mb-2 font-semibold text-ink-900">03 · Reparto y vista previa</h2>
        <p className="mb-4 text-sm text-ink-600">{event.zone_count === 1 ? 'Todas las parejas pertenecen a Zona A.' : 'Seleccioná las parejas de A; al guardar, las restantes se asignan a B. El reparto manual puede ser desigual. Los cupos insuficientes no impiden guardar el borrador, pero sí generar.'}</p>
        {!operations.setZones && <p className="mb-3 text-sm text-ink-600">Asignación manual no implementada en este corte.</p>}
        {!operations.randomizeZones && <p className="mb-3 text-sm text-ink-600">Reparto aleatorio no implementado en este corte.</p>}
        {unassigned && <p className="mb-3 text-sm text-ink-600">Las parejas sin asignar no pertenecen a B hasta guardar el reparto. La selección manual muestra una propuesta, no una asignación persistida.</p>}
        {!frozen && <fieldset disabled={locked || configDirty || pairDirty}>
          {event.zone_count === 2 && <>
            <div role="group" aria-label="Seleccionar parejas de Zona A" className="mb-4 grid grid-cols-2 gap-2">
              {event.registrations.map((r) => <Button key={r.id} variant={selected.has(r.id) ? 'primary' : 'secondary'}
                disabled={!operations.setZones} aria-pressed={selected.has(r.id)} aria-label={`Zona A: #${r.id} ${r.player1_name} / ${r.player2_name}`}
                className="justify-start break-words text-left" onClick={() => toggleZoneA(r.id)}>
                #{r.id} · {r.player1_name} / {r.player2_name}
              </Button>)}
            </div>
          </>}
          <div className="mb-4 flex flex-wrap gap-2">
            <Button disabled={!operations.setZones || (event.zone_count === 2 && !zonesDirty && !unassigned)} onClick={saveZones}>Guardar reparto</Button>
            {event.zone_count === 2 && <>
              <Button variant="secondary" disabled={!operations.randomizeZones || zonesDirty || !event.registrations.length}
                onClick={() => { const randomize = operations.randomizeZones; if (randomize && !locked && !configDirty && !pairDirty && !zonesDirty) void mutate(() => randomize(event.id, revision)) }}>Repartir aleatoriamente</Button>
              {zonesDirty && <Button variant="ghost" onClick={() => { setSelected(new Set(event.registrations.filter((r) => r.zone_id === zoneA?.id).map((r) => r.id))); setSelectionEdited(false) }}>Descartar reparto</Button>}
            </>}
          </div>
        </fieldset>}
        <p role="status" className="mb-3 text-xs text-ink-500">{zonesDirty ? 'Reparto sin guardar' : unassigned ? 'Reparto incompleto' : 'Reparto guardado'}{unassigned ? ' · Hay parejas sin asignar.' : ''}</p>
        <div className={`grid gap-3 ${event.zone_count === 2 ? 'grid-cols-2' : ''}`}>
          {[{ label: 'A', pairs: a }, ...(event.zone_count === 2 ? [{ label: 'B', pairs: b }] : [])].map(({ label, pairs }) => <section key={label} aria-label={`Vista previa Zona ${label}`} className="rounded-md border border-ink-200 bg-ink-50 p-3">
            <h3 className="font-semibold text-ink-900">Zona {label} <span className="tabular-nums">· {pairs.length}</span></h3>
            <p className={`my-2 text-xs ${pairs.length < required ? 'text-red-700' : 'text-ink-600'}`}>Cupo {pairs.length < required ? `insuficiente: ${pairs.length} de ${required}` : 'suficiente'} · Clasifican {required}</p>
            <ul className="space-y-2 text-sm text-ink-700">{pairs.map((r) => <li key={r.id} className="break-words">#{r.id} · {r.player1_name} / {r.player2_name}</li>)}</ul>
          </section>)}
        </div>
        <p className="mt-3 text-xs text-ink-500">El reparto aleatorio aprobado es equilibrado y se persiste antes de generar. Generar conserva el reparto guardado y no vuelve a sortear.</p>
      </Card>
    </div>
    <Card className="space-y-4 p-5">
      <h2 className="font-semibold text-ink-900">04 · Generar fixture</h2>
      <p className="text-sm text-ink-600">Todos contra todos dentro de cada zona, hasta seis partidos por ronda global y descansos explícitos. Sin partidos, la continuación abre revisión de clasificados.</p>
      {event.configuration_issues.length > 0 && <Alert><ul>{event.configuration_issues.map((issue, i) => <li key={`${issue.code}:${issue.zone_id}:${i}`}>{issue.message}</li>)}</ul></Alert>}
      {dirty && <p className="text-sm text-amber-700">Guardá o descartá la edición activa antes de continuar. La vista previa usa la configuración guardada.</p>}
      {!frozen && <p className="text-sm text-ink-700">Alcance aprobado: generar bloquea nombres, parejas, zonas y etapa. No permite regenerar.</p>}
      {!operations.generateFixture && <p id="fixture-next-cut" className="text-sm text-ink-600">Generación no implementada en este corte; disponible en un próximo corte aunque los cupos sean suficientes.</p>}
      {!frozen && <Button aria-describedby={!operations.generateFixture ? 'fixture-next-cut' : undefined} disabled={!operations.generateFixture || locked || dirty || !event.can_generate} onClick={() => { const generate = operations.generateFixture; if (generate && !locked && !dirty && event.can_generate) void mutate(async () => (await generate(event.id, revision)).event, 'generated') }}>Generar fixture</Button>}
      <p className="text-sm text-ink-600">Rondas, clasificación y playoffs no implementados en este corte; disponibles en próximos cortes.</p>
      <p className="text-xs text-ink-500 tabular-nums">Evento #{event.id} · Revisión {event.revision} · Grupos {event.groups_revision}</p>
    </Card>
  </>
}
