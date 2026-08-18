import { Navigate, Outlet, Route, Routes } from 'react-router-dom'

import { AuthProvider, useAuth } from './auth/AuthContext'
import { LoginPage } from './auth/LoginPage'
import { Layout } from './components/Layout'
import { AdminUsersPage } from './pages/AdminUsersPage'
import { MatchesPage } from './pages/MatchesPage'
import { SponsorsPage } from './pages/SponsorsPage'
import { StandingsPage } from './pages/StandingsPage'
import { TeamsPage } from './pages/TeamsPage'
import { HomePage } from './public/HomePage'
import { PublicLayout } from './public/PublicLayout'
import { PublicResultsPage } from './public/ResultsPage'
import { PublicStandingsPage } from './public/StandingsPage'
import { PublicTeamsPage } from './public/TeamsPage'
import { AdminThemeProvider } from './theme/AdminTheme'
import { ThemeProvider } from './theme/ThemeProvider'

/** Everything under /admin needs a session. The public site never does. */
function RequireAdmin() {
  const { admin, checking } = useAuth()

  // Without this gate the login screen flashes on every reload, because the
  // session is only known once /auth/me answers.
  if (checking) {
    return (
      <div className="flex min-h-full items-center justify-center">
        <p className="text-sm text-ink-400">Cargando…</p>
      </div>
    )
  }

  if (!admin) return <LoginPage />

  return <Outlet />
}

export function App() {
  return (
    <ThemeProvider>
      <Routes>
        <Route element={<PublicLayout />}>
          <Route index element={<HomePage />} />
          <Route path="parejas" element={<PublicTeamsPage />} />
          <Route path="tabla" element={<PublicStandingsPage />} />
          <Route path="resultados" element={<PublicResultsPage />} />
        </Route>

        {/* AuthProvider lives here and not at the root on purpose: it asks
            /auth/me on mount, and a public visitor should not pay for an
            authentication check they will never need. */}
        <Route
          path="/admin"
          element={
            <AdminThemeProvider>
              <AuthProvider>
                <RequireAdmin />
              </AuthProvider>
            </AdminThemeProvider>
          }
        >
          <Route element={<Layout />}>
            <Route index element={<Navigate to="parejas" replace />} />
            <Route path="parejas" element={<TeamsPage />} />
            <Route path="partidos" element={<MatchesPage />} />
            <Route path="tabla" element={<StandingsPage />} />
            <Route path="sponsors" element={<SponsorsPage />} />
            <Route path="administradores" element={<AdminUsersPage />} />
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ThemeProvider>
  )
}
