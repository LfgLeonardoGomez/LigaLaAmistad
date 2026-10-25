import { useCallback, useEffect, useState } from 'react'
import { Navigate, useNavigate, useParams } from 'react-router-dom'
import {
  americanoDraftOperations, americanoPlayoffsOperations, americanoQualificationOperations,
  americanoRoundOperations, americanoSetupOperations,
} from '../../api/americanos'
import type { AmericanoNavigation, AmericanoRoundPageProps, EventDetail } from '../../api/americano-types'
import { Alert, Button, Spinner } from '../../components/ui'
import { AmericanosPage } from './AmericanosPage'
import { AmericanoRoundPage } from './AmericanoRoundPage'
import { AmericanoSetupPage } from './AmericanoSetupPage'
import { AmericanoQualificationPage } from './AmericanoQualificationPage'
import { AmericanoPlayoffsPage } from './AmericanoPlayoffsPage'
import { useDirtyNavigation } from './useDirtyNavigation'

function positiveId(value: string | undefined): number | null {
  if (!value || !/^[1-9]\d*$/.test(value)) return null
  const id = Number(value)
  return Number.isSafeInteger(id) ? id : null
}

function useAmericanoNavigation() {
  const navigate = useNavigate()
  return useCallback((target: AmericanoNavigation) => {
    const path = navigationPath(target)
    if (path) void navigate(path)
  }, [navigate])
}

export function AmericanosListRoute() {
  const onNavigate = useAmericanoNavigation()
  return <AmericanosPage operations={americanoDraftOperations} onNavigate={onNavigate} />
}

export function AmericanoSetupRoute({ resolve = false }: { resolve?: boolean }) {
  const { eventId } = useParams<'eventId'>()
  const id = positiveId(eventId)
  const onNavigate = useAmericanoNavigation()
  if (id === null) return <AmericanoUnavailableRoute />
  if (resolve) return <Navigate to={`/admin/americanos/${id}/configuracion`} replace />
  return <AmericanoSetupPage eventId={id} operations={americanoSetupOperations} onNavigate={onNavigate} />
}

function isPositiveInteger(value: number) {
  return Number.isSafeInteger(value) && value > 0
}

function navigationPath(target: AmericanoNavigation): string | null {
  if (target.kind === 'list') return '/admin/americanos'
  if (!isPositiveInteger(target.event_id)) return null
  const eventPath = `/admin/americanos/${target.event_id}`
  switch (target.kind) {
    case 'event': return eventPath
    case 'setup': return `${eventPath}/configuracion`
    case 'round': return isPositiveInteger(target.round_number) ? `${eventPath}/rondas/${target.round_number}` : null
    case 'qualification': return `${eventPath}/clasificados`
    case 'playoffs': return `${eventPath}/playoffs`
  }
}

function continuationPath(event: EventDetail): string {
  const eventPath = `/admin/americanos/${event.id}`
  switch (event.state) {
    case 'draft': return `${eventPath}/configuracion`
    case 'review': return `${eventPath}/clasificados`
    case 'playoffs':
    case 'completed': return `${eventPath}/playoffs`
    case 'groups': {
      const continuation = event.continuation
      if (continuation.kind === 'round' && isPositiveInteger(continuation.round_number) &&
        continuation.round_number <= event.total_rounds && continuation.round_number <= event.max_unlocked_round) {
        return `${eventPath}/rondas/${continuation.round_number}`
      }
      throw new Error('El evento no indica una ronda habilitada. Volvé a consultar su estado.')
    }
  }
}

export function AmericanoEventRoute() {
  const { eventId } = useParams<'eventId'>()
  const id = positiveId(eventId)
  if (id === null) return <AmericanoUnavailableRoute />
  return <EventContinuation key={id} eventId={id} />
}

export function AmericanoStageRoute({ stage }: { stage: 'qualification' | 'playoffs' }) {
  const { eventId } = useParams<'eventId'>()
  const id = positiveId(eventId)
  const onNavigate = useAmericanoNavigation()
  const onDirtyChange = useDirtyNavigation()
  if (id === null) return <AmericanoUnavailableRoute />
  return stage === 'qualification'
    ? <AmericanoQualificationPage key={`${id}:qualification`} eventId={id} operations={americanoQualificationOperations} onNavigate={onNavigate} />
    : <AmericanoPlayoffsPage key={`${id}:playoffs`} eventId={id} operations={americanoPlayoffsOperations} onNavigate={onNavigate} onDirtyChange={onDirtyChange} />
}

function EventContinuation({ eventId, blockedRoundNumber }: {
  eventId: number
  blockedRoundNumber?: number
}) {
  const [event, setEvent] = useState<EventDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let active = true
    setEvent(null)
    setError(null)
    async function load() {
      try {
        const canonical = await americanoRoundOperations.loadEvent(eventId)
        if (!active) return
        if (canonical.id !== eventId) throw new Error('El evento recibido no corresponde a esta URL.')
        continuationPath(canonical)
        setEvent(canonical)
      } catch (failure) {
        if (active) setError(failure instanceof Error ? failure.message : 'No se pudo consultar el evento.')
      }
    }
    void load()
    return () => { active = false }
  }, [eventId, attempt])

  const path = event ? continuationPath(event) : null
  // A failed GET may name its own round as continuation; do not remount it in a loop.
  const repeatsUnavailableRound = blockedRoundNumber !== undefined && path === `/admin/americanos/${eventId}/rondas/${blockedRoundNumber}`
  if (error || repeatsUnavailableRound) return <div className="space-y-4">
    <Alert>{error ?? 'No se pudo abrir la ronda indicada por el evento. Volvé a consultar su estado.'}</Alert>
    <Button type="button" onClick={() => setAttempt(value => value + 1)}>Volver a consultar evento</Button>
    <EventRouteActions eventId={eventId} />
  </div>
  if (!event || !path) return <Spinner label="Consultando evento…" />
  return <Navigate to={path} replace />
}

function EventRouteActions({ eventId }: { eventId: number }) {
  const navigate = useNavigate()
  return <div className="flex flex-wrap gap-2">
    <Button type="button" variant="secondary" onClick={() => void navigate(`/admin/americanos/${eventId}/configuracion`)}>Ver configuración</Button>
    <Button type="button" variant="secondary" onClick={() => void navigate('/admin/americanos')}>Volver a Americanos</Button>
  </div>
}

export function AmericanoRoundRoute() {
  const { eventId, roundNumber } = useParams<'eventId' | 'roundNumber'>()
  const id = positiveId(eventId)
  const number = positiveId(roundNumber)
  if (id === null) return <AmericanoUnavailableRoute />
  if (number === null) return <EventContinuation key={id} eventId={id} />
  return <RoundRouteView key={`${id}:${number}`} eventId={id} roundNumber={number} />
}

function RoundRouteView({ eventId, roundNumber }: { eventId: number; roundNumber: number }) {
  const navigate = useNavigate()
  const onDirtyChange: AmericanoRoundPageProps['onDirtyChange'] = useDirtyNavigation()
  const [resolving, setResolving] = useState(false)
  const onNavigate = useCallback((target: AmericanoNavigation) => {
    const path = navigationPath(target)
    if (!path || path === `/admin/americanos/${eventId}/rondas/${roundNumber}` ||
      (target.kind === 'event' && target.event_id === eventId)) {
      setResolving(true)
      return
    }
    void navigate(path)
  }, [eventId, roundNumber, navigate])
  if (resolving) return <EventContinuation eventId={eventId} blockedRoundNumber={roundNumber} />
  return <AmericanoRoundPage eventId={eventId} roundNumber={roundNumber} operations={americanoRoundOperations}
    mode="editable" onNavigate={onNavigate} onDirtyChange={onDirtyChange} />
}

export function AmericanoUnavailableRoute() {
  const navigate = useNavigate()
  return <div className="space-y-4">
    <Alert>La URL de Americano no es válida o corresponde a una función no implementada en este corte.</Alert>
    <Button variant="secondary" onClick={() => void navigate('/admin/americanos')}>Volver a Americanos</Button>
  </div>
}
