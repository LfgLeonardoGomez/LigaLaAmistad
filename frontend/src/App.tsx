import { Navigate, Route, Routes } from 'react-router-dom'

import { AuthProvider, useAuth } from './auth/AuthContext'
import { LoginPage } from './auth/LoginPage'
import { Layout } from './components/Layout'
import { AdminUsersPage } from './pages/AdminUsersPage'
import { MatchesPage } from './pages/MatchesPage'
import { SponsorsPage } from './pages/SponsorsPage'
import { StandingsPage } from './pages/StandingsPage'
import { TeamsPage } from './pages/TeamsPage'

function Routing() {
  const { admin, checking } = useAuth()

  // Without this gate the login screen flashes on every reload, because the
  // session is only known after /auth/me answers.
  if (checking) {
    return (
      <div className="flex min-h-full items-center justify-center">
        <p className="text-sm text-ink-400">Cargando…</p>
      </div>
    )
  }

  if (!admin) return <LoginPage />

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/parejas" element={<TeamsPage />} />
        <Route path="/partidos" element={<MatchesPage />} />
        <Route path="/tabla" element={<StandingsPage />} />
        <Route path="/sponsors" element={<SponsorsPage />} />
        <Route path="/administradores" element={<AdminUsersPage />} />
        <Route path="*" element={<Navigate to="/parejas" replace />} />
      </Route>
    </Routes>
  )
}

export function App() {
  return (
    <AuthProvider>
      <Routing />
    </AuthProvider>
  )
}
