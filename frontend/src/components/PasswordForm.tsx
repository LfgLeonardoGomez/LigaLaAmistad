import { useState } from 'react'
import type { FormEvent } from 'react'

import { api } from '../api/client'
import type { Admin } from '../api/types'
import { Alert, Button, Field, Input } from './ui'

export const MIN_PASSWORD_LENGTH = 8

/**
 * Shared on purpose: the same form serves an admin changing their own password
 * from the header and an admin resetting somebody else's from the list. One
 * copy means the rules cannot drift apart.
 */
export function PasswordForm({
  admin,
  onDone,
  onCancel,
}: {
  admin: Admin
  onDone: () => void
  onCancel: () => void
}) {
  const [password, setPassword] = useState('')
  const [repeat, setRepeat] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const mismatch = repeat !== '' && password !== repeat

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (mismatch) return

    setSaving(true)
    setError(null)
    try {
      await api.patch(`/admin/users/${admin.id}`, { password })
      onDone()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'No se pudo cambiar')
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Field label="Nueva contraseña" hint={`Mínimo ${MIN_PASSWORD_LENGTH} caracteres.`}>
        <Input
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          minLength={MIN_PASSWORD_LENGTH}
          autoComplete="new-password"
          required
          autoFocus
        />
      </Field>

      {/* A typo in a password you cannot see locks you out of your own panel. */}
      <Field label="Repetir la contraseña">
        <Input
          type="password"
          value={repeat}
          onChange={(event) => setRepeat(event.target.value)}
          autoComplete="new-password"
          required
        />
      </Field>

      {mismatch && <Alert>Las dos contraseñas no coinciden.</Alert>}
      {error && <Alert>{error}</Alert>}

      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancelar
        </Button>
        <Button type="submit" disabled={saving || mismatch || password === ''}>
          {saving ? 'Guardando…' : 'Cambiar'}
        </Button>
      </div>
    </form>
  )
}
