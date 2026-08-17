import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

import { ApiError, api } from '../api/client'
import type { Admin } from '../api/types'

interface AuthValue {
  admin: Admin | null
  /** True until the initial /auth/me call settles. Avoids a login flash. */
  checking: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [admin, setAdmin] = useState<Admin | null>(null)
  const [checking, setChecking] = useState(true)

  // The token is in an httpOnly cookie, so JavaScript cannot read it. Asking
  // the API who we are is the only way to know whether a session is alive.
  useEffect(() => {
    api
      .get<Admin>('/auth/me')
      .then(setAdmin)
      .catch(() => setAdmin(null))
      .finally(() => setChecking(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    setAdmin(await api.post<Admin>('/auth/login', { email, password }))
  }, [])

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout', {})
    } catch (cause) {
      // An expired session already achieves what logout wanted.
      if (!(cause instanceof ApiError)) throw cause
    }
    setAdmin(null)
  }, [])

  const value = useMemo(
    () => ({ admin, checking, login, logout }),
    [admin, checking, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider')
  return value
}
