import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'

import { useAuth } from '../auth/AuthContext'
import { AdminThemeToggle } from '../theme/AdminTheme'
import { Modal } from './Modal'
import { PasswordForm } from './PasswordForm'
import { Button } from './ui'

const NAV_ITEMS = [
  { to: '/admin/parejas', label: 'Parejas' },
  { to: '/admin/partidos', label: 'Partidos' },
  { to: '/admin/tabla', label: 'Tabla' },
  { to: '/admin/sponsors', label: 'Sponsors' },
  { to: '/admin/encuesta', label: 'Encuesta' },
  { to: '/admin/administradores', label: 'Administradores' },
]

export function Layout() {
  const { admin, logout } = useAuth()
  const [changingPassword, setChangingPassword] = useState(false)

  return (
    <div className="flex min-h-full flex-col">
      <header className="border-b border-ink-200 bg-surface">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <span className="text-sm font-semibold text-ink-900">Liga La Amistad</span>

          <div className="flex items-center gap-3">
            {/* Your own password used to live only in the admins list, behind
                a screen named after managing other people. This is where
                someone actually looks for it. */}
            <button
              type="button"
              onClick={() => setChangingPassword(true)}
              title="Cambiar mi contraseña"
              className="hidden rounded-md px-2 py-1 text-sm text-ink-500 transition-colors hover:bg-ink-100 hover:text-ink-700 sm:inline-block"
            >
              {admin?.email}
            </button>
            <AdminThemeToggle />
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

      {changingPassword && admin && (
        <Modal title="Cambiar mi contraseña" onClose={() => setChangingPassword(false)}>
          <PasswordForm
            admin={admin}
            onDone={() => setChangingPassword(false)}
            onCancel={() => setChangingPassword(false)}
          />
        </Modal>
      )}
    </div>
  )
}
