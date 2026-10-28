const STEPS = ['Configuración', 'Parejas', 'Zonas', 'Fixture']

export function SetupSteps({ current, onChange, canVisit = () => false }: {
  current: number
  onChange?: (step: number) => void
  canVisit?: (step: number) => boolean
}) {
  return <nav aria-label="Pasos del americano" className="rounded-lg border border-ink-200 bg-surface p-2 sm:p-3">
    <ol className="grid grid-cols-4 gap-1 sm:gap-3">
      {STEPS.map((label, index) => {
        const step = index + 1
        return <li key={label}>
          <button type="button" aria-current={current === step ? 'step' : undefined}
            disabled={!onChange || !canVisit(step)} onClick={() => onChange?.(step)}
            className={`flex w-full flex-col items-center gap-2 rounded-md px-1 py-3 text-xs font-medium focus-visible:outline-2 focus-visible:outline-ink-800 disabled:cursor-default sm:flex-row sm:px-3 sm:text-sm ${current === step ? 'bg-ink-900 text-surface' : 'text-ink-500 enabled:hover:bg-ink-50'}`}>
            <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border tabular-nums ${current === step ? 'border-current' : 'border-ink-300'}`}>{step}</span>
            <span className="max-w-full break-words text-[10px] leading-tight sm:text-sm">{label}</span>
          </button>
        </li>
      })}
    </ol>
  </nav>
}
