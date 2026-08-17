import { THEMES, useTheme } from './ThemeProvider'
import type { Theme } from './ThemeProvider'

const LABELS: Record<Theme, string> = {
  velada: 'Clásico',
  lima: 'Neón',
  papel: 'Papel',
}

/** A segmented control. With three palettes, showing them all still beats a menu. */
export function ThemeToggle() {
  const { theme, setTheme } = useTheme()

  return (
    <div
      role="group"
      aria-label="Paleta de colores"
      className="flex items-center gap-0.5 rounded-full p-0.5"
      style={{ border: '1px solid var(--color-rule)' }}
    >
      {THEMES.map((option) => {
        const active = option === theme
        return (
          <button
            key={option}
            type="button"
            onClick={() => setTheme(option)}
            aria-pressed={active}
            className="rounded-full px-2.5 py-1 text-xs font-semibold tracking-wide uppercase transition-colors"
            style={{
              backgroundColor: active ? 'var(--color-accent)' : 'transparent',
              color: active ? 'var(--color-on-accent)' : 'var(--color-fg-muted)',
            }}
          >
            {LABELS[option]}
          </button>
        )
      })}
    </div>
  )
}
