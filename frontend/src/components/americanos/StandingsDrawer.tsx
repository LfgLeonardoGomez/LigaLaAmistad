import { useId, useLayoutEffect, useRef, useState } from 'react'
import type { StandingsDrawerProps } from '../../api/americano-types'
import { Button, Table, Td, Th } from '../ui'

export function StandingsDrawer({ open, standings, loading, error, onClose, returnFocusTo }: StandingsDrawerProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const [zoneId, setZoneId] = useState<number | null>(null)
  const titleId = useId()
  const zones = standings?.zones ?? []
  const activeZone = zones.find(entry => entry.zone.id === zoneId) ?? zones[0]

  useLayoutEffect(() => {
    const dialog = dialogRef.current
    if (!open || !dialog) return
    const fallback = document.activeElement instanceof HTMLElement ? document.activeElement : null
    dialog.showModal()
    return () => {
      dialog.close()
      const target = returnFocusTo?.isConnected ? returnFocusTo : fallback
      target?.focus({ preventScroll: true })
    }
  }, [open, returnFocusTo])

  if (!open) return null
  return (
    <dialog
      ref={dialogRef} aria-labelledby={titleId} aria-describedby={`${titleId}-notice`} aria-modal="true"
      onCancel={event => { event.preventDefault(); onClose() }}
      onKeyDown={event => {
        if (event.key !== 'Tab') return
        const elements = Array.from(event.currentTarget.querySelectorAll<HTMLElement>('button, [href], input, select, textarea, [tabindex]'))
          .filter(element => element.tabIndex >= 0 && !element.matches(':disabled, [hidden], [inert]') && element.getClientRects().length > 0 && getComputedStyle(element).visibility !== 'hidden')
        const first = elements[0]
        const last = elements[elements.length - 1]
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
      }}
      className="fixed inset-y-0 right-0 left-auto m-0 h-dvh max-h-none w-full max-w-xl border-l border-ink-200 bg-surface p-0 text-ink-800 shadow-2xl backdrop:bg-black/40"
    >
      <header className="flex items-center justify-between border-b border-ink-200 px-6 py-5">
        <h2 id={titleId} className="text-lg font-semibold text-ink-900">Tablas guardadas</h2>
        <Button type="button" variant="secondary" onClick={onClose}>Cerrar tablas</Button>
      </header>
      <div className="space-y-5 p-6">
        <p id={`${titleId}-notice`} className="rounded-md bg-amber-50 p-3 text-sm text-amber-700">
          Solo resultados guardados. Los cambios sin guardar no están incluidos.
        </p>
        {loading ? <p role="status">Cargando tablas…</p> : null}
        {error ? <p role="alert" className="text-sm text-red-700">{error}</p> : null}
        {!loading && !error && activeZone ? (
          <>
            {zones.length === 2 ? (
              <div role="tablist" aria-label="Zonas" className="flex gap-2">
                {zones.map((entry, index) => (
                  <button key={entry.zone.id} type="button" role="tab"
                    id={`${titleId}-tab-${entry.zone.id}`} aria-controls={`${titleId}-table`}
                    aria-selected={activeZone.zone.id === entry.zone.id}
                    tabIndex={activeZone.zone.id === entry.zone.id ? 0 : -1}
                    onClick={() => setZoneId(entry.zone.id)}
                    onKeyDown={event => {
                      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
                      event.preventDefault()
                      const target = event.key === 'Home' ? zones[0] : event.key === 'End' ? zones[zones.length - 1] : zones[(index + 1) % zones.length]
                      if (target) { setZoneId(target.zone.id); document.getElementById(`${titleId}-tab-${target.zone.id}`)?.focus() }
                    }}
                    className={`rounded-md px-4 py-2 text-sm font-medium focus-visible:outline-2 focus-visible:outline-ink-800 ${activeZone.zone.id === entry.zone.id ? 'bg-ink-900 text-surface' : 'bg-ink-50 text-ink-700'}`}
                  >Zona {entry.zone.label}</button>
                ))}
              </div>
            ) : <h3 className="text-sm font-semibold">Zona {activeZone.zone.label}</h3>}
            <div id={`${titleId}-table`} role={zones.length === 2 ? 'tabpanel' : undefined}
              aria-labelledby={zones.length === 2 ? `${titleId}-tab-${activeZone.zone.id}` : undefined}>
              <Table head={<tr><Th>Pos.</Th><Th>Pareja</Th><Th className="text-right">Puntos</Th><Th className="text-right">Dif. games</Th></tr>}>
                {activeZone.blocks.flatMap(block => block.rows.map(row => (
                  <tr key={row.registration.id}>
                    <Td className="tabular-nums">
                      {block.position_from === block.position_to ? block.position_from : <><span>{block.position_from}–{block.position_to}</span><span className="sr-only">, empatadas</span></>}
                    </Td>
                    <Td>{row.registration.player1_name} / {row.registration.player2_name}</Td>
                    <Td className="text-right font-medium tabular-nums">{(row.points_half_units / 2).toLocaleString('es-AR')}</Td>
                    <Td className="text-right tabular-nums">{row.games_diff > 0 ? '+' : ''}{row.games_diff}</Td>
                  </tr>
                )))}
              </Table>
              {activeZone.blocks.length === 0 ? <p className="py-8 text-center text-sm text-ink-500">Todavía no hay resultados guardados.</p> : null}
            </div>
          </>
        ) : null}
      </div>
    </dialog>
  )
}
