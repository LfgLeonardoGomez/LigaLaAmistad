import { NavLink, Outlet } from 'react-router-dom'

import { useAuth } from '../auth/AuthContext'
import { Button } from './ui'

const NAV_ITEMS = [
  { to: '/admin/parejas', label: 'Parejas' },
  { to: '/admin/partidos', label: 'Partidos' },
  { to: '/admin/tabla', label: 'Tabla' },
  { to: '/admin/sponsors', label: 'Sponsors' },
  { to: '/admin/administradores', label: 'Administradores' },
]

export function Layout() {
  const { admin, logout } = useAuth()

  return (
    <div className="flex min-h-full flex-col">
      <header className="border-b border-ink-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <span className="text-sm font-semibold text-ink-900">Liga La Amistad</span>

          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-ink-500 sm:inline">{admin?.email}</span>
            <Button variant="secondary" onClick={() => void logout()}>
              Salir
            </Button>
          </div>
        </div>

        <nav className="mx-auto max-w-6xl px-4">
          <ul className="-mb-px flex gap-1 overflow-x-auto">
            {NAV_ITEMS.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  className={({ isActive }) =>
                    `inline-block whitespace-nowrap border-b-2 px-3 py-2.5 text-sm font-medium transition-colors ${
                      isActive
                        ? 'border-ink-900 text-ink-900'
                        : 'border-transparent text-ink-500 hover:border-ink-300 hover:text-ink-700'
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}
