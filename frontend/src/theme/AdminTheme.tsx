import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

type AdminTheme = 'light' | 'dark'

const STORAGE_KEY = 'liga-admin-theme'

interface Value {
  theme: AdminTheme
  toggle: () => void
}

const AdminThemeContext = createContext<Value | null>(null)

function systemPrefersDark(): boolean {
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
}

function readStored(): AdminTheme | null {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored === 'light' || stored === 'dark' ? stored : null
  } catch {
    return null
  }
}

/**
 * The panel's own light/dark, separate from the public site's palettes: this
 * is a workspace, not the league's identity.
 *
 * Starts on whatever the operating system says, because someone opening an
 * admin panel at night has already made that choice once. A manual pick
 * overrides it and is remembered.
 */
export function AdminThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<AdminTheme>(
    () => readStored() ?? (systemPrefersDark() ? 'dark' : 'light'),
  )

  useEffect(() => {
    document.documentElement.dataset.admin = theme
    // The public site must not inherit it when navigating away.
    return () => {
      delete document.documentElement.dataset.admin
    }
  }, [theme])

  // Follow the system while the user has not chosen for themselves.
  useEffect(() => {
    if (readStored() !== null) return
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = (event: MediaQueryListEvent) => setTheme(event.matches ? 'dark' : 'light')
    media.addEventListener('change', onChange)
    return () => media.removeEventListener('change', onChange)
  }, [])

  const toggle = useCallback(() => {
    setTheme((current) => {
      const next = current === 'dark' ? 'light' : 'dark'
      try {
        localStorage.setItem(STORAGE_KEY, next)
      } catch {
        // Not remembering the choice is not worth breaking the panel.
      }
      return next
    })
  }, [])

  const value = useMemo(() => ({ theme, toggle }), [theme, toggle])

  return <AdminThemeContext.Provider value={value}>{children}</AdminThemeContext.Provider>
}

export function useAdminTheme(): Value {
  const value = useContext(AdminThemeContext)
  if (!value) throw new Error('useAdminTheme must be used inside AdminThemeProvider')
  return value
}

export function AdminThemeToggle() {
  const { theme, toggle } = useAdminTheme()
  const dark = theme === 'dark'

  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={dark}
      title={dark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
      className="rounded-md p-2 text-ink-500 transition-colors hover:bg-ink-100 hover:text-ink-700"
    >
      <span className="sr-only">{dark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}</span>
      {dark ? (
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor" aria-hidden="true">
          <path d="M12 4a1 1 0 0 1 1 1v1a1 1 0 1 1-2 0V5a1 1 0 0 1 1-1Zm0 12a4 4 0 1 1 0-8 4 4 0 0 1 0 8Zm0 2a1 1 0 0 1 1 1v1a1 1 0 1 1-2 0v-1a1 1 0 0 1 1-1ZM4 12a1 1 0 0 1 1-1h1a1 1 0 1 1 0 2H5a1 1 0 0 1-1-1Zm14 0a1 1 0 0 1 1-1h1a1 1 0 1 1 0 2h-1a1 1 0 0 1-1-1ZM6.34 6.34a1 1 0 0 1 1.41 0l.71.71a1 1 0 0 1-1.41 1.41l-.71-.7a1 1 0 0 1 0-1.42Zm9.2 9.2a1 1 0 0 1 1.41 0l.71.71a1 1 0 0 1-1.42 1.41l-.7-.71a1 1 0 0 1 0-1.41Zm1.41-9.2a1 1 0 0 1 0 1.42l-.7.7a1 1 0 1 1-1.42-1.41l.71-.71a1 1 0 0 1 1.41 0ZM7.05 15.54a1 1 0 0 1 0 1.41l-.71.71a1 1 0 0 1-1.41-1.41l.7-.71a1 1 0 0 1 1.42 0Z" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor" aria-hidden="true">
          <path d="M21.64 13a1 1 0 0 0-1.05-.14 8 8 0 0 1-3.37.73 8.15 8.15 0 0 1-8.14-8.1 8.6 8.6 0 0 1 .25-2A1 1 0 0 0 8 2.36a10.14 10.14 0 1 0 14 11.69 1 1 0 0 0-.36-1.05Z" />
        </svg>
      )}
    </button>
  )
}
