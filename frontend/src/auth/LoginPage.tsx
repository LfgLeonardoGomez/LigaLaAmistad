import { useState } from 'react'
import type { FormEvent } from 'react'

import { ApiError } from '../api/client'
import { Alert, Button, Card, Field, Input } from '../components/ui'
import { useAuth } from './AuthContext'

export function LoginPage() {
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)

    try {
      await login(email, password)
    } catch (cause) {
      setError(
        cause instanceof ApiError && cause.status === 429
          ? 'Demasiados intentos. Esperá unos minutos antes de volver a probar.'
          : cause instanceof Error
            ? cause.message
            : 'No se pudo iniciar sesión',
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-full items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <h1 className="text-lg font-semibold text-ink-900">Liga La Amistad</h1>
          <p className="mt-1 text-sm text-ink-500">Panel de administración</p>
        </div>

        <Card className="p-6">
          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <Field label="Email">
              <Input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="username"
                autoFocus
                required
              />
            </Field>

            <Field label="Contraseña">
              <Input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                required
              />
            </Field>

            {error && <Alert>{error}</Alert>}

            <Button type="submit" disabled={submitting} className="w-full">
              {submitting ? 'Entrando…' : 'Entrar'}
            </Button>
          </form>
        </Card>

        <p className="mt-4 text-center text-xs text-ink-400">
          El acceso lo da un administrador. No hay registro público.
        </p>
      </div>
    </div>
  )
}
