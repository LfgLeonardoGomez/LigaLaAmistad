import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import type { AmericanoListPageProps, EventSummary, StartStage, ZoneCount } from '../../api/americano-types'
import { Alert, Button, Card, EmptyState, Field, Input, Select, Spinner, Table, Td, Th } from '../../components/ui'
import { ALL_COURTS, CourtSelector } from './CourtSelector'
import { SetupSteps } from './SetupSteps'

const states = { draft: 'Borrador', groups: 'Grupos', review: 'Revisión', playoffs: 'Playoffs', completed: 'Finalizado' }
const stages = { quarterfinal: 'Cuartos de final', semifinal: 'Semifinales', final: 'Final' }

export function AmericanosPage({ operations, onNavigate }: AmericanoListPageProps) {
  const [events, setEvents] = useState<EventSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [createError, setCreateError] = useState<string | null>(null)
  const [reload, setReload] = useState(0)
  const [name, setName] = useState('')
  const [zones, setZones] = useState<ZoneCount>(1)
  const [stage, setStage] = useState<StartStage>('semifinal')
  const [courts, setCourts] = useState<number[]>(ALL_COURTS)
  const [saving, setSaving] = useState(false)
  const [uncertain, setUncertain] = useState(false)
  const inFlight = useRef(false)
  const generation = useRef(0)

  useEffect(() => {
    let ignore = false
    generation.current += 1
    setLoading(true)
    setLoadError(null)
    void operations.listEvents().then((next) => {
      if (!ignore) { setEvents(next); setUncertain(false); setCreateError(null) }
    }, (cause: unknown) => {
      if (!ignore) setLoadError(cause instanceof Error ? cause.message : 'No se pudieron cargar los eventos.')
    }).finally(() => { if (!ignore) setLoading(false) })
    return () => { ignore = true; generation.current += 1 }
  }, [operations, reload])

  async function create(e: FormEvent) {
    e.preventDefault()
    if (inFlight.current || loading || uncertain || !name.trim() || !courts.length) return
    const started = generation.current
    inFlight.current = true
    setSaving(true)
    setCreateError(null)
    try {
      const next = await operations.createEvent({ name: name.trim(), zone_count: zones, start_stage: stage, courts })
      if (generation.current === started) {
        setEvents((current) => [next, ...current.filter((item) => item.id !== next.id)])
        setName('')
        onNavigate({ kind: 'setup', event_id: next.id })
      }
    } catch (cause) {
      if (generation.current === started) {
        const status = typeof cause === 'object' && cause !== null && 'status' in cause ? cause.status : undefined
        const mustReload = status !== 422
        const recovery = mustReload ? ' Recargá la lista antes de volver a crear: la respuesta podría haberse perdido.' : ''
        setCreateError(`${status === 409 ? 'Conflicto 409. ' : ''}${cause instanceof Error ? cause.message : 'No se pudo crear el evento.'}${recovery}`)
        setUncertain(mustReload)
      }
    } finally { inFlight.current = false; setSaving(false) }
  }

  return <div className="space-y-6">
    <Card className="space-y-5 p-5 sm:p-6">
      <SetupSteps current={1} />
      <h2 className="text-base font-semibold text-ink-900">Nuevo evento</h2>
      <form onSubmit={create} className="space-y-5">
        <div className="grid items-start gap-6 md:grid-cols-2 md:gap-10">
        <fieldset disabled={loading || saving || uncertain} className="space-y-4">
          <Field label="Nombre del nuevo evento"><Input required value={name} onChange={(e) => setName(e.target.value)} /></Field>
          <Field label="Zonas"><Select value={zones} onChange={(e) => setZones(Number(e.target.value) as ZoneCount)}><option value="1">Una zona</option><option value="2">Dos zonas</option></Select></Field>
          <Field label="Inicio de eliminatorias"><Select value={stage} onChange={(e) => setStage(e.target.value as StartStage)}>{Object.entries(stages).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</Select></Field>
        </fieldset>
        <div className="w-full md:max-w-sm md:justify-self-end"><CourtSelector value={courts} onChange={setCourts} disabled={loading || saving || uncertain} /></div>
        </div>
        <div className="flex flex-wrap items-center gap-x-5 gap-y-3 border-t border-ink-200 pt-5">
          <Button type="submit" disabled={loading || saving || uncertain || !name.trim() || !courts.length}>{saving ? 'Creando…' : 'Crear borrador y agregar parejas'}</Button>
          <p className="max-w-sm text-xs leading-relaxed text-ink-500">Después cargás las parejas y revisás las zonas antes de generar el fixture.</p>
        </div>
      </form>
      {createError && <Alert>{createError}</Alert>}
    </Card>
    {loadError || uncertain ? <div className="space-y-2">
      <Alert>{loadError ?? 'La creación pudo haberse guardado. Consultá el historial antes de intentar crear de nuevo.'}</Alert>
      <Button variant="secondary" disabled={loading || saving} onClick={() => setReload(n => n + 1)}>Volver a consultar eventos</Button>
    </div> : null}
    <Card>
      {loading ? <Spinner label="Cargando eventos…" /> : loadError ? <EmptyState>No se pudo consultar el historial. Recargá la lista.</EmptyState> : !events.length ? <EmptyState>Todavía no hay Americanos. Creá el primer borrador.</EmptyState> :
        <Table head={<tr><Th>Evento</Th><Th>Estado</Th><Th>Parejas / zonas</Th><Th>Campeones</Th><Th>Acceso</Th></tr>}>
          {events.map((event) => <tr key={event.id} className="hover:bg-ink-50">
            <Td><span className="font-medium text-ink-900">{event.name}</span><p className="text-xs text-ink-500">#{event.id} · {stages[event.start_stage]}</p></Td>
            <Td>{states[event.state]}</Td><Td className="tabular-nums">{event.registration_count} / {event.zone_count}</Td>
            <Td>{event.champion ? <span className="font-medium text-ink-900">{event.champion.player1_name} / {event.champion.player2_name}</span> : <span className="text-ink-500">—</span>}</Td>
            <Td><Button variant="secondary" onClick={() => onNavigate({ kind: 'event', event_id: event.id })}>{event.state === 'draft' ? 'Retomar evento' : 'Ver historial'}</Button></Td>
          </tr>)}
        </Table>}
    </Card>
  </div>
}
