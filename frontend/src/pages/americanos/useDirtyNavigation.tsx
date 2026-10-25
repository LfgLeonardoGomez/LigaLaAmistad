import { createContext, useCallback, useContext, useEffect, useLayoutEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { useBlocker } from 'react-router-dom'

import type { DirtyNavigationDraft } from '../../api/americano-types'
import { Button } from '../../components/ui'

type RegisterDraft = (draft: DirtyNavigationDraft | null) => void
type DirtyNavigationContextValue = {
  register: RegisterDraft
  requestLogout: (logout: () => Promise<void>) => void
}

const DirtyNavigationContext = createContext<DirtyNavigationContextValue | null>(null)

function hasUnsavedWork(draft: DirtyNavigationDraft | null) {
  return Boolean(draft && (draft.dirty || draft.pending))
}

export function DirtyNavigationProvider({ children }: { children: ReactNode }) {
  const current = useRef<DirtyNavigationDraft | null>(null)
  const [draft, setDraft] = useState<DirtyNavigationDraft | null>(null)
  const [logoutAction, setLogoutAction] = useState<(() => Promise<void>) | null>(null)
  const [resolving, setResolving] = useState(false)
  const resolvingRef = useRef(false)
  const mounted = useRef(true)
  const navigationVersion = useRef(0)
  const producerVersion = useRef(0)
  const producer = useRef<Pick<DirtyNavigationDraft, 'save' | 'discard'> | null>(null)
  const logoutRef = useRef<(() => Promise<void>) | null>(null)
  const [error, setError] = useState<string | null>(null)
  const blocker = useBlocker(useCallback(() => {
    const prevent = resolvingRef.current || hasUnsavedWork(current.current)
    if (prevent) navigationVersion.current += 1
    return prevent
  }, []))
  const blockerRef = useRef(blocker)
  useLayoutEffect(() => { blockerRef.current = blocker })
  useLayoutEffect(() => {
    mounted.current = true
    return () => { mounted.current = false }
  }, [])

  const register = useCallback<RegisterDraft>(next => {
    // Layout-effect cleanup briefly publishes null even for the same editor.
    // Track its stable action identity across that gap, but invalidate an
    // awaited save if another editor registered (even if the old one replies).
    if (next && (next.save !== producer.current?.save || next.discard !== producer.current?.discard)) {
      producer.current = next
      producerVersion.current += 1
    }
    current.current = next
    setDraft(next)
  }, [])

  const requestLogout = useCallback((logout: () => Promise<void>) => {
    // A second click must not replace an intent already being resolved.
    if (resolvingRef.current || logoutRef.current || blockerRef.current.state !== 'unblocked') return
    setError(null)
    if (hasUnsavedWork(current.current)) {
      logoutRef.current = logout
      setLogoutAction(() => logout)
    }
    else {
      resolvingRef.current = true
      setResolving(true)
      void Promise.resolve().then(logout).catch(cause => {
        if (mounted.current) setError(cause instanceof Error ? cause.message : 'No se pudo cerrar la sesión.')
      }).finally(() => {
        resolvingRef.current = false
        if (mounted.current) setResolving(false)
      })
    }
  }, [])

  useEffect(() => {
    function beforeUnload(event: BeforeUnloadEvent) {
      if (!hasUnsavedWork(current.current)) return
      event.preventDefault()
      event.returnValue = ''
    }
    window.addEventListener('beforeunload', beforeUnload)
    return () => window.removeEventListener('beforeunload', beforeUnload)
  }, [])

  const blocked = blocker.state === 'blocked'
  const open = !resolving && (blocked || logoutAction !== null)
  function clearIntent() {
    if (blockerRef.current.state === 'blocked') blockerRef.current.reset()
    logoutRef.current = null
    setLogoutAction(null)
  }
  function stay() {
    if (resolvingRef.current) return
    clearIntent()
    setError(null)
  }

  async function continueAfter(action: 'save' | 'discard') {
    const active = current.current
    if (resolvingRef.current || active?.pending) return
    const version = navigationVersion.current
    const editorVersion = producerVersion.current
    const logout = logoutRef.current
    const destination = blockerRef.current
    resolvingRef.current = true
    setResolving(true)
    setError(null)
    try {
      // Release the modal's inertness and restore focus BEFORE round validation.
      // A failed save needs access to the fields or canonical comparison, not a
      // dialog on top of them. Never retry a failed/uncertain write here.
      await new Promise<void>(resolve => requestAnimationFrame(() => resolve()))
      if (!mounted.current) return
      if (navigationVersion.current !== version || current.current !== active) { clearIntent(); return }
      const succeeded = !active || !hasUnsavedWork(active) || (action === 'save' ? await active.save() : active.discard())
      if (!mounted.current) return
      const latest = current.current
      const sameProducer = !active ? !latest : latest?.save === active.save && latest.discard === active.discard
      // Both callbacks must publish a clean canonical baseline before leaving.
      // A different draft or a newer Back/Forward intent cancels this attempt.
      if (!succeeded || !sameProducer || producerVersion.current !== editorVersion || hasUnsavedWork(latest) || navigationVersion.current !== version) {
        clearIntent()
        if (!succeeded) setError('No se completó la salida. Revisá los marcadores o la comparación con el servidor; tu edición sigue acá.')
        return
      }
      // Logout is the sole destination when requested, including if a POP was
      // blocked before React rendered it. Clear that blocker, never follow it.
      if (logout) {
        if (blockerRef.current.state === 'blocked') blockerRef.current.reset()
        await logout()
      } else if (destination.state === 'blocked') destination.proceed()
      logoutRef.current = null
      setLogoutAction(null)
    } catch (cause) {
      if (!mounted.current) return
      clearIntent()
      setError(cause instanceof Error ? cause.message : 'No se pudo completar la salida. Tu edición sigue acá.')
    } finally {
      resolvingRef.current = false
      if (mounted.current) setResolving(false)
    }
  }

  return <DirtyNavigationContext.Provider value={{ register, requestLogout }}>
    {children}
    {!open && error ? <p role="alert" className="mx-auto max-w-6xl px-4 py-3 text-sm text-red-700">{error}</p> : null}
    {open ? <DirtyNavigationDialog pending={Boolean(draft?.pending)} resolving={resolving} error={error}
      onStay={stay} onSave={() => void continueAfter('save')} onDiscard={() => void continueAfter('discard')} /> : null}
  </DirtyNavigationContext.Provider>
}

export function useDirtyNavigation(): RegisterDraft {
  const context = useContext(DirtyNavigationContext)
  if (!context) throw new Error('DirtyNavigationProvider is required')
  return context.register
}

export function useGuardedLogout() {
  const context = useContext(DirtyNavigationContext)
  if (!context) throw new Error('DirtyNavigationProvider is required')
  return context.requestLogout
}

function DirtyNavigationDialog({ pending, resolving, error, onStay, onSave, onDiscard }: {
  pending: boolean
  resolving: boolean
  error: string | null
  onStay: () => void
  onSave: () => void
  onDiscard: () => void
}) {
  const ref = useRef<HTMLDialogElement>(null)
  useLayoutEffect(() => {
    const dialog = ref.current
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null
    dialog?.showModal()
    return () => { dialog?.close(); if (previous?.isConnected) previous.focus() }
  }, [])
  return <dialog ref={ref} aria-labelledby="dirty-navigation-title" aria-modal="true"
    onCancel={event => { event.preventDefault(); onStay() }}
    className="m-auto w-full max-w-md rounded-lg border border-ink-200 bg-surface p-6 text-ink-800 shadow-xl backdrop:bg-black/40">
    <h2 id="dirty-navigation-title" className="text-lg font-semibold text-ink-900">Hay cambios sin guardar</h2>
    <p className="mt-2 text-sm text-ink-600">Guardá los cambios, descartá la edición o permanecé acá. Si hay un guardado sin verificar, primero compará con el servidor.</p>
    {error ? <p role="alert" className="mt-3 text-sm text-red-700">{error}</p> : null}
    <div className="mt-5 flex flex-wrap gap-2">
      <Button type="button" disabled={pending || resolving} onClick={onSave}>Guardar y continuar</Button>
      <Button type="button" variant="secondary" disabled={pending || resolving} onClick={onDiscard}>Descartar y continuar</Button>
      <Button type="button" variant="ghost" disabled={resolving} onClick={onStay}>Permanecer</Button>
    </div>
  </dialog>
}
