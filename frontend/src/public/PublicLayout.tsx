import { NavLink, Outlet } from 'react-router-dom'

import { ThemeToggle } from '../theme/ThemeToggle'

const NAV_ITEMS = [
  { to: '/', label: 'Inicio', end: true },
  { to: '/parejas', label: 'Parejas', end: false },
  { to: '/tabla', label: 'Tabla', end: false },
  { to: '/resultados', label: 'Resultados', end: false },
]

export function PublicLayout() {
  return (
    <div className="public-shell flex min-h-full flex-col">
      <header
        className="sticky top-0 z-20 backdrop-blur-md"
        style={{
          backgroundColor: 'color-mix(in srgb, var(--color-canvas) 86%, transparent)',
          borderBottom: '1px solid var(--color-rule)',
        }}
      >
        <div className="mx-auto flex w-full max-w-[1180px] items-center justify-between gap-4 px-4 py-3.5 sm:px-8">
          <NavLink to="/" className="flex min-w-0 items-center gap-2.5">
            <span
              className="display grid h-[34px] w-[34px] flex-none place-items-center rounded-full text-sm"
              style={{ border: '2px solid var(--color-accent)', color: 'var(--color-accent)' }}
            >
              LA
            </span>
            <span className="display text-[13px] leading-tight sm:text-[15px]">
              Liga
              <br />
              La Amistad
            </span>
          </NavLink>

          <div className="flex items-center gap-4">
            <nav>
              <ul className="flex items-center gap-3 sm:gap-5">
                {NAV_ITEMS.map((item) => (
                  <li key={item.to}>
                    <NavLink
                      to={item.to}
                      end={item.end}
                      className="display text-[11px] whitespace-nowrap sm:text-[13px]"
                      style={({ isActive }) => ({
                        color: isActive ? 'var(--color-accent)' : 'var(--color-fg)',
                        borderBottom: isActive
                          ? '2px solid var(--color-accent)'
                          : '2px solid transparent',
                        paddingBottom: '2px',
                      })}
                    >
                      {item.label}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </nav>
            <div className="hidden sm:block">
              <ThemeToggle />
            </div>
          </div>
        </div>
      </header>

      {/* Full width on purpose: each page wraps its own content in
          `.container-page`, which lets a hero or a photo band break out. */}
      <main className="w-full flex-1">
        <Outlet />
      </main>

      <footer
        className="mt-16"
        style={{ borderTop: '1px solid var(--color-rule)' }}
      >
        <div className="mx-auto flex w-full max-w-[1180px] flex-col gap-3 px-4 py-6 text-xs sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <span className="display" style={{ color: 'var(--color-accent)' }}>
            Liga La Amistad · Temporada 2026
          </span>
          <span style={{ color: 'var(--color-fg-muted)' }}>
            Pádel amateur · Dos zonas · Al mejor de tres sets
          </span>
          <div className="sm:hidden">
            <ThemeToggle />
          </div>
        </div>
      </footer>
    </div>
  )
}
