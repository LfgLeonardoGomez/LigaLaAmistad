import { useEffect } from 'react'
import type { ReactNode } from 'react'

import type { Team } from '../api/types'
import { imageUrl } from '../api/images'

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
        src={imageUrl(team.photo_url, { width: size, height: size })}
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

/**
 * A dialog wearing the public site's tokens.
 *
 * The panel has its own `Modal`, built on the admin palette. Reusing it here
 * would drag the admin's whites and greys into a themed page.
 */
export function PublicModal({
  title,
  onClose,
  children,
}: {
  title: string
  onClose: () => void
  children: ReactNode
}) {
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKeyDown)
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    return () => {
      document.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = previousOverflow
    }
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-4 sm:items-center"
      style={{ backgroundColor: 'color-mix(in srgb, var(--color-canvas) 80%, transparent)' }}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="card w-full max-w-md"
        style={{ backgroundColor: 'var(--color-canvas)' }}
      >
        <div
          className="flex items-center justify-between gap-3 px-4 py-3"
          style={{ borderBottom: '1px solid var(--color-rule)' }}
        >
          <h2 className="display text-sm">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar"
            className="rounded p-1 transition-opacity hover:opacity-70"
            style={{ color: 'var(--color-fg-muted)' }}
          >
            <svg viewBox="0 0 20 20" className="h-4 w-4" fill="currentColor" aria-hidden="true">
              <path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
            </svg>
          </button>
        </div>

        <div className="p-4">{children}</div>
      </div>
    </div>
  )
}
