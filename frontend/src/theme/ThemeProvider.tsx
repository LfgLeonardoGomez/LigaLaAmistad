import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

export const THEMES = ['velada', 'lima', 'papel'] as const
export type Theme = (typeof THEMES)[number]

export const DEFAULT_THEME: Theme = 'velada'

const STORAGE_KEY = 'liga-theme'

interface ThemeValue {
  theme: Theme
  setTheme: (theme: Theme) => void
  toggle: () => void
}

const ThemeContext = createContext<ThemeValue | null>(null)

function isTheme(value: unknown): value is Theme {
  return typeof value === 'string' && (THEMES as readonly string[]).includes(value)
}

function readStoredTheme(): Theme {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return isTheme(stored) ? stored : DEFAULT_THEME
  } catch {
    // Private mode and blocked storage both throw. The default is fine.
    return DEFAULT_THEME
  }
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(readStoredTheme)

  // The tokens hang off the root element, so the whole page — including the
  // parts React does not own, like the scrollbar — follows the theme.
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    try {
      localStorage.setItem(STORAGE_KEY, theme)
    } catch {
      // Not being able to remember the choice is not worth breaking the page.
    }
  }, [theme])

  const setTheme = useCallback((next: Theme) => setThemeState(next), [])
  const toggle = useCallback(
    () =>
      setThemeState((current) => {
        const next = THEMES.indexOf(current) + 1
        return THEMES[next % THEMES.length] ?? DEFAULT_THEME
      }),
    [],
  )

  const value = useMemo(() => ({ theme, setTheme, toggle }), [theme, setTheme, toggle])

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme(): ThemeValue {
  const value = useContext(ThemeContext)
  if (!value) throw new Error('useTheme must be used inside ThemeProvider')
  return value
}
