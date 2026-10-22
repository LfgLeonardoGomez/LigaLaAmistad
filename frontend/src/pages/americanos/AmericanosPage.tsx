import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import type { AmericanoListPageProps, EventSummary, StartStage, ZoneCount } from '../../api/americano-types'
import { Alert, Button, Card, EmptyState, Field, Input, PageHeader, Select, Spinner, Table, Td, Th } from '../../components/ui'

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
    if (inFlight.current || loading || uncertain || !name.trim()) return
    const started = generation.current
    inFlight.current = true
    setSaving(true)
    setCreateError(null)
    try {
      const next = await operations.createEvent({ name: name.trim(), zone_count: zones, start_stage: stage })
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
    <PageHeader title="Americanos" description="Eventos independientes de parejas fijas. Retomá un evento o consultá su historial."
      action={<Button variant="secondary" disabled={loading || saving} onClick={() => setReload((n) => n + 1)}>Recargar lista</Button>} />
    <Card className="p-5">
      <h2 className="mb-4 text-base font-semibold text-ink-900">Nuevo evento</h2>
      <form onSubmit={create}>
        <fieldset disabled={loading || saving || uncertain} className="grid items-end gap-4 lg:grid-cols-[2fr_1fr_1fr_auto]">
          <Field label="Nombre del nuevo evento"><Input required value={name} onChange={(e) => setName(e.target.value)} /></Field>
          <Field label="Zonas"><Select value={zones} onChange={(e) => setZones(Number(e.target.value) as ZoneCount)}><option value="1">Una zona</option><option value="2">Dos zonas</option></Select></Field>
          <Field label="Inicio de eliminatorias"><Select value={stage} onChange={(e) => setStage(e.target.value as StartStage)}>{Object.entries(stages).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</Select></Field>
          <Button type="submit" disabled={!name.trim()}>{saving ? 'Creando…' : 'Crear borrador'}</Button>
        </fieldset>
      </form>
      <p className="mt-3 text-xs text-ink-500">Se crea vacío. Después registrás las parejas y revisás el reparto antes de generar.</p>
      {createError && <Alert>{createError}</Alert>}
    </Card>
    {loadError && <Alert>{loadError}</Alert>}
    <Card>
      {loading ? <Spinner label="Cargando eventos…" /> : loadError ? <EmptyState>No se pudo consultar el historial. Recargá la lista.</EmptyState> : !events.length ? <EmptyState>Todavía no hay Americanos. Creá el primer borrador.</EmptyState> :
        <Table head={<tr><Th>Evento</Th><Th>Estado</Th><Th>Parejas / zonas</Th><Th>Grupos guardados</Th><Th>Acceso</Th></tr>}>
          {events.map((event) => <tr key={event.id} className="hover:bg-ink-50">
            <Td><span className="font-medium text-ink-900">{event.name}</span><p className="text-xs text-ink-500">#{event.id} · {stages[event.start_stage]}</p></Td>
            <Td>{states[event.state]}</Td><Td className="tabular-nums">{event.registration_count} / {event.zone_count}</Td>
            <Td className="tabular-nums">{event.saved_rounds} / {event.total_rounds}</Td>
            <Td><Button variant="secondary" onClick={() => onNavigate({ kind: 'event', event_id: event.id })}>{event.state === 'draft' ? 'Retomar evento' : 'Ver historial'}</Button></Td>
          </tr>)}
        </Table>}
    </Card>
  </div>
}
