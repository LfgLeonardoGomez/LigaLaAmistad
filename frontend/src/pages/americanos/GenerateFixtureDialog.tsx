import { useId, useLayoutEffect, useRef } from 'react'
import { Button } from '../../components/ui'

export function GenerateFixtureDialog({ name, pairCount, courts, hasRounds, onConfirm, onClose }: {
  name: string
  pairCount: number
  courts: number[]
  hasRounds: boolean
  onConfirm: () => void
  onClose: () => void
}) {
  const dialog = useRef<HTMLDialogElement>(null)
  const cancel = useRef<HTMLButtonElement>(null)
  const id = useId()
  useLayoutEffect(() => {
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const element = dialog.current
    element?.showModal()
    cancel.current?.focus()
    return () => {
      element?.close()
      if (previous?.isConnected) previous.focus({ preventScroll: true })
    }
  }, [])

  return <dialog ref={dialog} aria-labelledby={`${id}-title`} aria-describedby={`${id}-description`}
    aria-modal="true" onCancel={event => { event.preventDefault(); onClose() }}
    className="m-auto w-[calc(100%-2rem)] max-w-lg rounded-lg border border-ink-200 bg-surface p-0 text-ink-800 shadow-xl backdrop:bg-black/50">
    <div className="space-y-4 p-6">
      <div className="flex items-start gap-3">
        <span aria-hidden="true" className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-amber-50 text-xl font-semibold text-amber-700">!</span>
        <div>
          <h2 id={`${id}-title`} className="text-lg font-semibold text-ink-900">Generar fixture</h2>
          <p className="mt-1 break-words text-sm text-ink-600">{name}</p>
        </div>
      </div>
      <p id={`${id}-description`} className="text-sm leading-relaxed">Los cruces quedarán definidos y no se podrán regenerar. Revisá las parejas, zonas y canchas antes de continuar.</p>
      <dl className="grid grid-cols-2 gap-3 rounded-md bg-ink-50 p-4 text-sm">
        <div><dt className="text-ink-500">Parejas</dt><dd className="font-semibold text-ink-900">{pairCount}</dd></div>
        <div><dt className="text-ink-500">Canchas</dt><dd className="font-semibold text-ink-900">{courts.join(', ')}</dd></div>
      </dl>
      <p className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-700">Se bloqueará la configuración del evento. {hasRounds ? 'Al confirmar, abriremos la primera ronda para cargar los resultados.' : 'Como no hay cruces de grupos, abriremos la revisión de clasificados.'}</p>
    </div>
    <div className="flex flex-wrap justify-end gap-2 border-t border-ink-200 px-6 py-4">
      <button ref={cancel} type="button" onClick={onClose} className="rounded-md px-4 py-2 text-sm font-medium text-ink-700 ring-1 ring-ink-300 hover:bg-ink-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink-800">Volver a revisar</button>
      <Button type="button" onClick={onConfirm}>{hasRounds ? 'Confirmar y abrir ronda' : 'Confirmar y revisar clasificados'}</Button>
    </div>
  </dialog>
}
