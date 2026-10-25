import { useEffect, useRef, useState } from 'react'
import type {
  AmericanoQualificationPageProps, ConfirmQualifiersRequest, EventDetail, QualificationResponse, TieResolution,
} from '../../api/americano-types'
import { Alert, Button, Card, Field, PageHeader, Select, Spinner, Table, Td, Th } from '../../components/ui'

type Review = { event: EventDetail; preview: QualificationResponse }
function messageOf(cause: unknown) { return cause instanceof Error ? cause.message : 'No se pudo completar la operación.' }
function statusOf(cause: unknown) { return typeof cause === 'object' && cause !== null && 'status' in cause ? cause.status : undefined }
function savedSelections(preview: QualificationResponse): TieResolution[] {
  return preview.slots.flatMap(slot => slot.requires_resolution && slot.registration_id !== null
    ? [{ zone_id: slot.zone_id, position: slot.position, registration_id: slot.registration_id }] : [])
}
function selectionKey(values: TieResolution[]) {
  return JSON.stringify([...values].sort((a, b) => a.zone_id - b.zone_id || a.position - b.position))
}
function validSelections(preview: QualificationResponse, values: TieResolution[]) {
  const manual = preview.slots.filter(slot => slot.requires_resolution)
  if (values.length !== manual.length || manual.some(slot => values.filter(value => value.zone_id === slot.zone_id && value.position === slot.position && slot.candidate_registration_ids.includes(value.registration_id)).length !== 1)) return false
  const ids = preview.slots.map(slot => ({ zone: slot.zone_id, id: slot.requires_resolution
    ? values.find(value => value.zone_id === slot.zone_id && value.position === slot.position)?.registration_id : slot.registration_id }))
  return ids.every((value, index) => value.id !== undefined && value.id !== null && !ids.slice(0, index).some(previous => previous.zone === value.zone && previous.id === value.id))
}

export function AmericanoQualificationPage(props: AmericanoQualificationPageProps) {
  return <QualificationReview key={props.eventId} {...props} />
}

function QualificationReview({ eventId, operations, onNavigate }: AmericanoQualificationPageProps) {
  const [review, setReview] = useState<Review | null>(null)
  const [resolutions, setResolutions] = useState<TieResolution[]>([])
  const [loading, setLoading] = useState(true)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState('')
  const [recovery, setRecovery] = useState(false)
  const [canonical, setCanonical] = useState<Review | null>(null)
  const [retryRequest, setRetryRequest] = useState<ConfirmQualifiersRequest | null>(null)
  const [attempt, setAttempt] = useState(0)
  const [tieDialogOpen, setTieDialogOpen] = useState(false)
  const alive = useRef(false)
  const busy = useRef(false)
  const generation = useRef(0)
  const port = useRef(operations)
  port.current = operations

  async function readCanonical(): Promise<Review> {
    const [event, preview] = await Promise.all([port.current.loadEvent(eventId), port.current.loadQualification(eventId)])
    if (event.id !== eventId || preview.event_id !== eventId || event.revision !== preview.revision ||
      event.groups_revision !== preview.source_groups_revision || event.state !== preview.state ||
      preview.frozen !== ['playoffs', 'completed'].includes(preview.state) ||
      (preview.can_confirm && (preview.state !== 'review' || preview.blockers.length > 0 || preview.missing_slots.length > 0 || preview.seeding_template.status !== 'approved'))) {
      throw new Error('La revisión cambió durante la consulta. Volvé a cargarla antes de continuar.')
    }
    return { event, preview }
  }
  function adopt(next: Review) {
    setReview(next)
    setResolutions(savedSelections(next.preview))
    setCanonical(null)
    setRecovery(false)
    setError(null)
  }
  useEffect(() => {
    alive.current = true
    const started = ++generation.current
    if (!Number.isSafeInteger(eventId) || eventId < 1) {
      setError('El ID del evento no es válido.')
      setLoading(false)
      return () => { alive.current = false; generation.current++ }
    }
    setLoading(true)
    void readCanonical().then(next => {
      if (alive.current && started === generation.current) adopt(next)
    }, cause => {
      if (alive.current && started === generation.current) setError(messageOf(cause))
    }).finally(() => { if (alive.current && started === generation.current) setLoading(false) })
    return () => { alive.current = false; generation.current++ }
    // Operations are an injected port; replacing its object does not discard local choices.
  }, [eventId, attempt])

  const preview = review?.preview
  const dirty = Boolean(preview && selectionKey(resolutions) !== selectionKey(savedSelections(preview)))
  const readOnly = !preview || preview.frozen || preview.state !== 'review'
  const complete = Boolean(preview && validSelections(preview, resolutions))
  const disabled = pending || recovery || retryRequest !== null || readOnly
  const canConfirm = Boolean(preview?.can_confirm && preview.seeding_template.status === 'approved' &&
    preview.blockers.length === 0 && preview.missing_slots.length === 0 && !dirty && complete && !disabled)
  const needsHumanResolution = Boolean(preview?.slots.some(slot => slot.requires_resolution) && (!complete || dirty))
  const hasResolutionSlots = Boolean(preview?.slots.some(slot => slot.requires_resolution))
  const canOpenTieDialog = Boolean(preview && hasResolutionSlots && !disabled && preview.state === 'review' &&
    preview.seeding_template.status === 'approved' && preview.missing_slots.length === 0 &&
    preview.blockers.every(blocker => blocker.code === 'unresolved_ties'))

  async function compareCanonical(started: number) {
    setCanonical(null)
    try {
      const next = await readCanonical()
      if (alive.current && started === generation.current) setCanonical(next)
    } catch (cause) {
      if (alive.current && started === generation.current) setError(previous => `${previous ?? ''} No pudimos comprobar la revisión actual: ${messageOf(cause)}`)
    }
  }
  async function save() {
    if (!preview || busy.current || disabled || !dirty || !complete) return
    const started = generation.current
    busy.current = true; setPending(true); setError(null); setNotice('')
    try {
      const next = await port.current.saveTieResolutions(eventId, {
        expected_revision: preview.revision, source_groups_revision: preview.source_groups_revision, resolutions,
      })
      if (!alive.current || started !== generation.current) return
      if (next.event_id !== eventId || next.source_groups_revision !== preview.source_groups_revision ||
        next.revision !== preview.revision + 1 || next.state !== 'review' || next.frozen ||
        selectionKey(savedSelections(next)) !== selectionKey(resolutions)) throw new Error('La respuesta no permite verificar las resoluciones guardadas.')
      setReview(current => current ? { event: { ...current.event, revision: next.revision, state: next.state }, preview: next } : null)
      setResolutions(savedSelections(next)); setNotice('Resoluciones guardadas. Revisá el cuadro antes de confirmar.')
    } catch (cause) {
      if (!alive.current || started !== generation.current) return
      setTieDialogOpen(false)
      setRecovery(true)
      setError(`${statusOf(cause) === 409 ? 'Conflicto 409. ' : ''}${messageOf(cause)} Conservamos tu selección. Cargá la revisión actual antes de volver a guardar o confirmar.`)
      await compareCanonical(started)
    } finally { if (alive.current && started === generation.current) { busy.current = false; setPending(false) } }
  }
  async function confirm(request?: ConfirmQualifiersRequest) {
    if (!preview || busy.current || (!request && !canConfirm) || (request && retryRequest !== request)) return
    setTieDialogOpen(false)
    const started = generation.current
    busy.current = true; setPending(true); setError(null); setNotice('')
    let intention = request
    try {
      intention ??= { expected_revision: preview.revision, source_groups_revision: preview.source_groups_revision, confirmation_key: crypto.randomUUID() }
      const response = await port.current.confirmQualifiers(eventId, intention)
      if (!alive.current || started !== generation.current) return
      if (response.event.id !== eventId || response.playoffs.event_id !== eventId || response.confirmation_key !== intention.confirmation_key ||
        response.confirmed_source_revision !== intention.source_groups_revision ||
        response.event.groups_revision !== response.confirmed_source_revision || response.playoffs.groups_revision !== response.confirmed_source_revision ||
        response.event.revision <= intention.expected_revision || response.event.revision !== response.playoffs.revision ||
        response.event.state !== response.playoffs.state || !['playoffs', 'completed'].includes(response.event.state) ||
        !response.confirmed_at || response.event.confirmed_at !== response.confirmed_at) throw new Error('No pudimos verificar la confirmación recibida.')
      setRetryRequest(null)
      onNavigate({ kind: 'playoffs', event_id: eventId })
    } catch (cause) {
      if (!alive.current || started !== generation.current) return
      const status = statusOf(cause)
      const uncertain = status === 0 || status === undefined || (typeof status === 'number' && status >= 500)
      setRetryRequest(uncertain && intention ? intention : null)
      setRecovery(true)
      setError(`${status === 409 ? 'Conflicto 409. ' : ''}${messageOf(cause)} No reenviamos la confirmación automáticamente. Consultá el estado actual.`)
      await compareCanonical(started)
    } finally { if (alive.current && started === generation.current) { busy.current = false; setPending(false) } }
  }
  function navigate(kind: 'event' | 'playoffs' | 'list') {
    if (busy.current) return
    if ((dirty || retryRequest) && !window.confirm('Hay decisiones locales sin guardar o una confirmación sin verificar. ¿Salir y consultar el estado guardado?')) return
    if (kind === 'event' && review?.event.state === 'review') {
      const number = review.event.total_rounds
      onNavigate(number > 0 ? { kind: 'round', event_id: eventId, round_number: number } : { kind: 'setup', event_id: eventId })
    } else onNavigate(kind === 'list' ? { kind } : { kind, event_id: eventId })
  }

  function startPlayoffs() {
    if (!preview || busy.current || disabled) return
    if (needsHumanResolution) setTieDialogOpen(true)
    else void confirm()
  }

  function selectTie(zoneId: number, position: number, raw: string) {
    if (!preview || busy.current || disabled) return
    const slot = preview.slots.find(item => item.zone_id === zoneId && item.position === position && item.requires_resolution)
    if (!slot) return
    const registrationId = raw === '' ? null : Number(raw)
    if (registrationId !== null && (!slot.candidate_registration_ids.includes(registrationId) ||
      resolutions.some(value => value.zone_id === zoneId && value.position !== position && value.registration_id === registrationId))) return
    setResolutions(current => {
      const otherSlots = current.filter(value => value.zone_id !== zoneId || value.position !== position)
      return registrationId === null ? otherSlots : [...otherSlots, { zone_id: zoneId, position, registration_id: registrationId }]
    })
    setNotice('')
  }

  if (loading) return <Spinner label="Cargando revisión de clasificados…" />
  if (!review || !preview) return <div className="space-y-4"><Alert>{error ?? 'No se pudo cargar la revisión.'}</Alert>
    <Button type="button" disabled={!Number.isSafeInteger(eventId) || eventId < 1} onClick={() => setAttempt(value => value + 1)}>Volver a cargar revisión</Button>
    <Button type="button" variant="secondary" onClick={() => onNavigate({ kind: 'list' })}>Volver a Americanos</Button></div>
  const pairs = new Map(review.event.registrations.map(pair => [pair.id, `${pair.player1_name} / ${pair.player2_name} · #${pair.registration_order}`]))
  const qualifiedIds = new Set(preview.slots.flatMap(slot => slot.registration_id === null ? [] : [slot.registration_id]))
  const canonicalChanged = canonical && (canonical.preview.revision !== preview.revision || canonical.preview.source_groups_revision !== preview.source_groups_revision)
  const primaryDisabled = pending || recovery || retryRequest !== null ||
    (!preview.frozen && !canConfirm && !canOpenTieDialog)
  return <div className="space-y-6">
    <PageHeader title="Clasificados" description={review.event.name} />
    <p className="flex items-center gap-2 text-sm text-ink-600" aria-label="Leyenda de clasificación">
      <span className="inline-flex rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-800">Clasificado</span>
    </p>
    {preview.standings.map(zone => <section key={zone.zone.id} aria-label={`Clasificación zona ${zone.zone.label}`}>
      <h2 className="mb-3 text-sm font-semibold text-ink-800">Zona {zone.zone.label}</h2>
      <Card><Table head={<tr><Th>Pos.</Th><Th>Pareja</Th><Th className="text-right">Puntos</Th><Th className="text-right">Dif. games</Th></tr>}>
        {zone.blocks.flatMap(block => block.rows.map(row => {
          const qualified = qualifiedIds.has(row.registration.id)
          return <tr key={row.registration.id} className={qualified ? 'bg-emerald-50' : undefined}>
          <Td className="tabular-nums">{block.position_from === block.position_to ? block.position_from : `${block.position_from}–${block.position_to}`}</Td>
          <Td><span className={qualified ? 'font-semibold text-emerald-900' : undefined}>{pairs.get(row.registration.id)}</span>
            {qualified ? <span className="ml-2 inline-flex rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-800">Clasificado</span> : null}</Td>
          <Td className="text-right tabular-nums">{(row.points_half_units / 2).toLocaleString('es-AR')}</Td>
          <Td className="text-right tabular-nums">{row.games_diff > 0 ? '+' : ''}{row.games_diff}</Td>
        </tr>
        }))}
      </Table></Card>
    </section>)}
    {error ? <Alert>{error}</Alert> : null}
    {recovery ? <section className="space-y-3 rounded-md border border-amber-200 bg-amber-50 p-4" aria-label="Recuperación de clasificación">
      {canonical ? <><p className="text-sm text-ink-700">La revisión guardada cambió. Cargá la versión actual para continuar.</p>
        <Button type="button" variant="secondary" disabled={pending} onClick={() => {
          if (busy.current || !canonical) return
          if (dirty && !window.confirm('Cargar la revisión actual descarta tu selección local. ¿Continuar?')) return
          const preserveIntent = retryRequest && !canonicalChanged && !canonical.preview.frozen
          adopt(canonical)
          if (!preserveIntent) setRetryRequest(null)
          else setRecovery(true)
          setNotice('Se cargó la revisión guardada del servidor.')
        }}>Cargar revisión actual</Button>
        {canonical.preview.frozen ? <Button type="button" disabled={pending} onClick={() => navigate('playoffs')}>Ver playoffs</Button> : null}
      </> : <p className="text-sm text-ink-700">El estado no se pudo verificar.</p>}
      <Button type="button" variant="secondary" disabled={pending} onClick={async () => {
        if (busy.current) return
        busy.current = true; setPending(true)
        try { await compareCanonical(generation.current) } finally { if (alive.current) { busy.current = false; setPending(false) } }
      }}>Comprobar revisión</Button>
      {retryRequest && !canonical?.preview.frozen && !canonicalChanged ? <Button type="button" disabled={pending} onClick={() => void confirm(retryRequest)}>Reintentar inicio</Button> : null}
    </section> : null}
    <footer className="flex flex-wrap gap-3 border-t border-ink-200 pt-5">
      <Button type="button" disabled={primaryDisabled} onClick={preview.frozen ? () => navigate('playoffs') : startPlayoffs}>
        {preview.frozen ? 'Ver playoffs' : 'Iniciar playoffs'}
      </Button>
      <Button type="button" variant="secondary" disabled={pending} onClick={() => navigate('event')}>Volver al evento</Button>
    </footer>
    {tieDialogOpen && preview ? <TieResolutionDialog
      preview={preview}
      resolutions={resolutions}
      registrations={review.event.registrations}
      pending={pending}
      dirty={dirty}
      complete={complete}
      canConfirm={canConfirm}
      notice={notice}
      onSelect={selectTie}
      onSave={() => void save()}
      onConfirm={() => void confirm()}
      onClose={() => setTieDialogOpen(false)}
    /> : null}
  </div>
}

function TieResolutionDialog({
  preview, resolutions, registrations, pending, dirty, complete, canConfirm, notice, onSelect, onSave, onConfirm, onClose,
}: {
  preview: QualificationResponse
  resolutions: TieResolution[]
  registrations: EventDetail['registrations']
  pending: boolean
  dirty: boolean
  complete: boolean
  canConfirm: boolean
  notice: string
  onSelect: (zoneId: number, position: number, value: string) => void
  onSave: () => void
  onConfirm: () => void
  onClose: () => void
}) {
  const dialog = useRef<HTMLDialogElement>(null)
  const names = new Map(registrations.map(pair => [pair.id, `${pair.player1_name} / ${pair.player2_name} · #${pair.registration_order}`]))
  const tiedSlots = preview.slots.filter(slot => slot.requires_resolution)
  useEffect(() => {
    const element = dialog.current
    element?.showModal()
    return () => { element?.close() }
  }, [])

  return <dialog ref={dialog} aria-labelledby="tie-resolution-title" aria-modal="true"
    onCancel={event => { event.preventDefault(); onClose() }}
    className="m-auto w-full max-w-lg rounded-lg border border-ink-200 bg-surface p-6 text-ink-800 shadow-xl backdrop:bg-black/40">
    <h2 id="tie-resolution-title" className="text-lg font-semibold text-ink-900">Resolver empates</h2>
    <p className="mt-1 text-sm text-ink-600">Elegí quién clasifica en cada empate.</p>
    <div className="mt-4 space-y-3">
      {tiedSlots.map(slot => {
        const zone = preview.standings.find(value => value.zone.id === slot.zone_id)?.zone
        const selected = resolutions.find(value => value.zone_id === slot.zone_id && value.position === slot.position)?.registration_id
        const duplicate = selected !== undefined && resolutions.some(value => value.zone_id === slot.zone_id && value.position !== slot.position && value.registration_id === selected)
        const missing = selected === undefined || !slot.candidate_registration_ids.includes(selected) || duplicate
        const label = `Zona ${zone?.label ?? '?'} · plaza ${slot.position}`
        return <Field key={`${slot.zone_id}:${slot.position}`} label={label}>
          <Select aria-label={label} aria-invalid={missing} value={selected ?? ''} disabled={pending}
            onChange={event => onSelect(slot.zone_id, slot.position, event.currentTarget.value)}>
            <option value="">Elegir pareja</option>
            {slot.candidate_registration_ids.map(id => <option key={id} value={id}
              disabled={resolutions.some(value => value.zone_id === slot.zone_id && value.position !== slot.position && value.registration_id === id)}>
              {names.get(id) ?? `Pareja #${id}`}
            </option>)}
          </Select>
        </Field>
      })}
    </div>
    {dirty && !complete ? <p className="mt-3 text-sm text-amber-700">Elegí una pareja en cada empate.</p> : null}
    {notice ? <p role="status" aria-live="polite" className="mt-3 text-sm text-ink-600">{notice}</p> : null}
    <div className="mt-5 flex flex-wrap gap-2">
      <Button type="button" disabled={pending || !dirty || !complete} onClick={onSave}>Guardar sorteo</Button>
      <Button type="button" disabled={pending || !canConfirm} onClick={onConfirm}>Iniciar playoffs</Button>
      <Button type="button" variant="secondary" disabled={pending} onClick={onClose}>Volver</Button>
    </div>
  </dialog>
}
