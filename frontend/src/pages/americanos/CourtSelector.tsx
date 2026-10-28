interface CourtSelectorProps {
  value: number[]
  onChange: (courts: number[]) => void
  disabled?: boolean
}

export const ALL_COURTS = [1, 2, 3, 4, 5, 6]
const COURT_LAYOUT = [4, 5, 6, 1, 2, 3]

export function CourtSelector({ value, onChange, disabled = false }: CourtSelectorProps) {
  return <fieldset disabled={disabled} className="space-y-3">
    <legend className="mb-1 text-sm font-medium text-ink-800">Canchas disponibles</legend>
    <p className="text-xs text-ink-500">Elegí las canchas reales que se van a usar. Seleccioná al menos una.</p>
    <div className="grid max-w-sm grid-cols-3 gap-2 sm:gap-3">
      {COURT_LAYOUT.map(number => {
        const selected = value.includes(number)
        return <button key={number} type="button" aria-pressed={selected} aria-label={`Cancha ${number}`}
          onClick={() => onChange(selected ? value.filter(court => court !== number) : [...value, number].sort((a, b) => a - b))}
          className={`relative aspect-[1.5] min-h-16 overflow-hidden rounded-md border-2 p-2 text-center transition-colors focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ink-800 disabled:cursor-not-allowed ${selected ? 'border-emerald-800 bg-emerald-800 text-white' : 'border-ink-300 bg-ink-50 text-ink-500 hover:border-ink-500'}`}>
          <span aria-hidden="true" className="pointer-events-none absolute inset-2 border border-current opacity-30">
            <span className="absolute inset-x-0 top-1/2 border-t border-dashed border-current" />
            <span className="absolute inset-y-0 left-1/2 border-l border-current" />
          </span>
          <span className="relative rounded bg-inherit px-1 py-1 text-xs font-semibold sm:px-2 sm:text-sm">Cancha {number}</span>
          <span className="relative mt-1 block text-[9px] font-semibold uppercase tracking-wide sm:text-[10px]">{selected ? 'Seleccionada' : 'No disponible'}</span>
        </button>
      })}
    </div>
    <p role="status" className={`text-xs ${value.length ? 'text-ink-600' : 'text-red-700'}`}>
      {value.length ? `${value.length} ${value.length === 1 ? 'cancha · Hasta 1 partido' : 'canchas · Hasta ' + value.length + ' partidos'} por ronda.` : 'Seleccioná al menos una cancha para continuar.'}
    </p>
  </fieldset>
}
