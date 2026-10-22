import { Navigate, useNavigate, useParams } from 'react-router-dom'
import { americanoDraftOperations, americanoSetupOperations } from '../../api/americanos'
import type { AmericanoNavigation } from '../../api/americano-types'
import { Alert, Button } from '../../components/ui'
import { AmericanosPage } from './AmericanosPage'
import { AmericanoSetupPage } from './AmericanoSetupPage'

function positiveId(value: string | undefined): number | null {
  if (!value || !/^[1-9]\d*$/.test(value)) return null
  const id = Number(value)
  return Number.isSafeInteger(id) ? id : null
}

function useDraftNavigation() {
  const navigate = useNavigate()
  return (target: AmericanoNavigation) => {
    if (target.kind === 'list') { void navigate('/admin/americanos'); return }
    if (!Number.isSafeInteger(target.event_id) || target.event_id <= 0) return
    // Only the saved configuration/history is available in this draft slice.
    if (target.kind === 'event' || target.kind === 'setup') {
      void navigate(`/admin/americanos/${target.event_id}/configuracion`)
    }
  }
}

export function AmericanosListRoute() {
  const onNavigate = useDraftNavigation()
  return <AmericanosPage operations={americanoDraftOperations} onNavigate={onNavigate} />
}

export function AmericanoSetupRoute({ resolve = false }: { resolve?: boolean }) {
  const { eventId } = useParams<'eventId'>()
  const id = positiveId(eventId)
  const onNavigate = useDraftNavigation()
  if (id === null) return <AmericanoUnavailableRoute />
  if (resolve) return <Navigate to={`/admin/americanos/${id}/configuracion`} replace />
  return <AmericanoSetupPage eventId={id} operations={americanoSetupOperations} onNavigate={onNavigate} />
}

export function AmericanoUnavailableRoute() {
  const navigate = useNavigate()
  return <div className="space-y-4">
    <Alert>La URL de Americano no es válida o corresponde a una función no implementada en este corte.</Alert>
    <Button variant="secondary" onClick={() => void navigate('/admin/americanos')}>Volver a Americanos</Button>
  </div>
}
