import type { ReactNode } from 'react'

export function PageTitle({ title, lead }: { title: string; lead?: string }) {
  return (
    <div className="py-[clamp(28px,6vw,56px)]">
      <h1 className="display text-[clamp(40px,9vw,86px)]">{title}</h1>
      {lead && (
        <p
          className="mt-3 max-w-[60ch] text-[clamp(15px,2vw,18px)] leading-relaxed text-pretty"
          style={{ color: 'var(--color-fg-muted)' }}
        >
          {lead}
        </p>
      )}
    </div>
  )
}

export function ZoneTabs({
  zones,
  selected,
  onSelect,
}: {
  zones: { id: number; name: string }[]
  selected: number | null
  onSelect: (id: number | null) => void
}) {
  const options: { id: number | null; name: string }[] = [
    { id: null, name: 'Todas' },
    ...zones.map((zone) => ({ id: zone.id as number | null, name: zone.name })),
  ]

  return (
    <div role="group" aria-label="Filtrar por zona" className="flex flex-wrap gap-2">
      {options.map((option) => {
        const active = option.id === selected
        return (
          <button
            key={String(option.id)}
            type="button"
            onClick={() => onSelect(option.id)}
            aria-pressed={active}
            className="display rounded-full px-5 py-2 text-xs transition-colors"
            style={{
              backgroundColor: active ? 'var(--color-accent)' : 'transparent',
              color: active ? 'var(--color-on-accent)' : 'var(--color-fg-muted)',
              border: `1px solid ${active ? 'var(--color-accent)' : 'var(--color-rule)'}`,
            }}
          >
            {option.name}
          </button>
        )
      })}
    </div>
  )
}

export function Panel({ children }: { children: ReactNode }) {
  return <div style={{ border: '1px solid var(--color-rule)' }}>{children}</div>
}

export function Notice({
  children,
  tone = 'muted',
}: {
  children: ReactNode
  tone?: 'muted' | 'hot'
}) {
  return (
    <p
      className="px-4 py-12 text-center text-sm"
      style={{
        border: '1px solid var(--color-rule)',
        color: tone === 'hot' ? 'var(--color-hot)' : 'var(--color-fg-muted)',
      }}
    >
      {children}
    </p>
  )
}

const MONTHS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

export function formatDate(value: string): string {
  const [year, month, day] = value.split('-').map(Number)
  if (!year || !month || !day) return value
  return `${day} ${MONTHS[month - 1]}`
}
