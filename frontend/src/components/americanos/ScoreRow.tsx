import { useCallback, useId } from 'react'
import type { ScoreInput, ScoreRowProps, Side } from '../../api/americano-types'

export function ScoreRow({ match, zoneLabel, value, readOnly, errors, onChange, onAdvance, onInvalidInput, registerInput }: ScoreRowProps) {
  const id = useId()
  const nameA = `${match.registration_a.player1_name} / ${match.registration_a.player2_name}`
  const nameB = `${match.registration_b.player1_name} / ${match.registration_b.player2_name}`
  const registerA = useCallback((element: HTMLInputElement | null) => registerInput(match.id, 'a', element), [registerInput, match.id])
  const registerB = useCallback((element: HTMLInputElement | null) => registerInput(match.id, 'b', element), [registerInput, match.id])

  function update(side: Side, next: string) {
    if (readOnly) return
    if (/^\d{2,}$/.test(next)) { onInvalidInput?.(); return }
    if (!/^[0-9]?$/.test(next)) return
    const previous = side === 'a' ? value.games_a : value.games_b
    onChange(match.id, side, next as ScoreInput)
    if (previous === '' && next !== '') onAdvance(match.id, side)
  }

  function score(side: Side, name: string, rival: string) {
    const error = errors[side]
    const games = side === 'a' ? value.games_a : value.games_b
    return (
      <div className="flex flex-col items-center gap-1">
        <input
          ref={side === 'a' ? registerA : registerB}
          type="text" inputMode="numeric" pattern="[0-9]" autoComplete="off"
          aria-label={`Games de ${name}, rival ${rival}, zona ${zoneLabel}, partido ${match.display_order}`}
          aria-invalid={Boolean(error)} aria-describedby={error ? `${id}-${side}-error` : undefined}
          value={readOnly && games === '' ? '—' : games} readOnly={readOnly}
          onFocus={event => event.currentTarget.select()}
          onChange={event => update(side, event.currentTarget.value)}
          onKeyDown={event => {
            if (!readOnly && (event.key === 'Backspace' || event.key === 'Delete')) {
              event.preventDefault()
              onChange(match.id, side, '')
            }
          }}
          onPaste={event => {
            event.preventDefault()
            const text = event.clipboardData.getData('text')
            if (/^[0-9]$/.test(text)) update(side, text)
            else if (/^\d{2,}$/.test(text)) onInvalidInput?.()
          }}
          className={`h-14 w-14 rounded-md border bg-surface text-center text-2xl font-semibold tabular-nums text-ink-900
            outline-none focus:ring-2 focus:ring-ink-800 focus:ring-offset-2 read-only:bg-ink-50
            ${error ? 'border-red-600 ring-1 ring-red-600' : 'border-ink-300'}`}
        />
        {error ? <span id={`${id}-${side}-error`} className="max-w-28 text-center text-xs text-red-700">{error}</span> : null}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-5 px-5 py-4">
      <p className="text-right text-sm font-medium text-ink-900">{nameA}</p>
      <div className="flex items-start gap-3">
        {score('a', nameA, nameB)}
        <span aria-hidden="true" className="pt-3 text-xl text-ink-400">–</span>
        {score('b', nameB, nameA)}
      </div>
      <p className="text-sm font-medium text-ink-900">{nameB}</p>
    </div>
  )
}
