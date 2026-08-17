import type { ReactNode } from 'react'

import type { Team } from '../api/types'

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

/** The pair's photo, or a striped placeholder while there is none. */
export function TeamAvatar({ team, size = 28 }: { team: Team | undefined; size?: number }) {
  const style = { width: size, height: size, border: '1px solid var(--color-rule)' }

  if (team?.photo_url) {
    return (
      <img
        src={team.photo_url}
        alt=""
        loading="lazy"
        className="flex-none rounded-full object-cover"
        style={style}
      />
    )
  }

  return (
    <span
      aria-hidden="true"
      className="flex-none rounded-full"
      style={{
        ...style,
        backgroundImage:
          'repeating-linear-gradient(45deg, transparent, transparent 4px, var(--color-rule) 4px, var(--color-rule) 5px)',
      }}
    />
  )
}

export function Pagination({
  page,
  pages,
  onChange,
}: {
  page: number
  pages: number
  onChange: (page: number) => void
}) {
  if (pages <= 1) return null

  const button = (label: ReactNode, target: number, disabled: boolean, current = false) => (
    <button
      key={`${label}-${target}`}
      type="button"
      onClick={() => onChange(target)}
      disabled={disabled}
      aria-current={current ? 'page' : undefined}
      className="display min-w-9 rounded px-3 py-2 text-xs transition-colors disabled:cursor-not-allowed disabled:opacity-40"
      style={{
        border: `1px solid ${current ? 'var(--color-accent)' : 'var(--color-rule)'}`,
        backgroundColor: current ? 'var(--color-accent)' : 'transparent',
        color: current ? 'var(--color-on-accent)' : 'var(--color-fg-muted)',
      }}
    >
      {label}
    </button>
  )

  return (
    <nav aria-label="Paginación" className="mt-6 flex flex-wrap items-center justify-center gap-2">
      {button('Anterior', page - 1, page === 1)}
      {Array.from({ length: pages }, (_, index) =>
        button(index + 1, index + 1, false, index + 1 === page),
      )}
      {button('Siguiente', page + 1, page === pages)}
    </nav>
  )
}

const MONTHS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

export function formatDate(value: string): string {
  const [year, month, day] = value.split('-').map(Number)
  if (!year || !month || !day) return value
  return `${day} ${MONTHS[month - 1]}`
}
