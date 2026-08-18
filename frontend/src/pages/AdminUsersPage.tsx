import { useState } from 'react'
import type { FormEvent } from 'react'

import { api } from '../api/client'
import type { Admin } from '../api/types'
import { useResource } from '../api/useResource'
import { useAuth } from '../auth/AuthContext'
import { Modal } from '../components/Modal'
import { MIN_PASSWORD_LENGTH, PasswordForm } from '../components/PasswordForm'
import {
  Alert,
  Button,
  Card,
  EmptyState,
  Field,
  Input,
  PageHeader,
  Spinner,
  Table,
  Td,
  Th,
} from '../components/ui'

export function AdminUsersPage() {
  const { admin: current } = useAuth()
  const admins = useResource<Admin[]>('/admin/users')
  const [creating, setCreating] = useState(false)
  const [resetting, setResetting] = useState<Admin | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function toggle(target: Admin) {
    setError(null)
    try {
      await api.patch(`/admin/users/${target.id}`, { is_active: !target.is_active })
      admins.reload()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'No se pudo actualizar')
    }
  }

  return (
    <>
      <PageHeader
        title="Administradores"
        description="No hay registro público: el acceso lo da un administrador. Los administradores no se eliminan, se desactivan."
        action={<Button onClick={() => setCreating(true)}>Nuevo administrador</Button>}
      />

      {(error || admins.error) && (
        <div className="mb-4">
          <Alert>{error ?? admins.error}</Alert>
        </div>
      )}

      <Card>
        {admins.loading ? (
          <Spinner />
        ) : !admins.data?.length ? (
          <EmptyState>No hay administradores.</EmptyState>
        ) : (
          <Table
            head={
              <tr>
                <Th>Email</Th>
                <Th>Estado</Th>
                <Th className="text-right">Acciones</Th>
              </tr>
            }
          >
            {admins.data.map((row) => {
              const isMe = row.id === current?.id
              return (
                <tr key={row.id} className="hover:bg-ink-50">
                  <Td>
                    <span className="font-medium text-ink-900">{row.email}</span>
                    {isMe && <span className="ml-2 text-xs text-ink-400">vos</span>}
                  </Td>
                  <Td>
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${
                        row.is_active
                          ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
                          : 'bg-ink-100 text-ink-600 ring-ink-300'
                      }`}
                    >
                      {row.is_active ? 'Activo' : 'Desactivado'}
                    </span>
                  </Td>
                  <Td className="text-right">
                    <Button variant="ghost" onClick={() => setResetting(row)}>
                      Cambiar contraseña
                    </Button>
                    <Button
                      variant="ghost"
                      disabled={isMe}
                      title={isMe ? 'No podés desactivar tu propia cuenta' : undefined}
                      onClick={() => void toggle(row)}
                    >
                      {row.is_active ? 'Desactivar' : 'Activar'}
                    </Button>
                  </Td>
                </tr>
              )
            })}
          </Table>
        )}
      </Card>

      {creating && (
        <Modal title="Nuevo administrador" onClose={() => setCreating(false)}>
          <CreateForm
            onDone={() => {
              setCreating(false)
              admins.reload()
            }}
            onCancel={() => setCreating(false)}
          />
        </Modal>
      )}

      {resetting && (
        <Modal title={`Contraseña de ${resetting.email}`} onClose={() => setResetting(null)}>
          <PasswordForm
            admin={resetting}
            onDone={() => setResetting(null)}
            onCancel={() => setResetting(null)}
          />
        </Modal>
      )}
    </>
  )
}

function CreateForm({ onDone, onCancel }: { onDone: () => void; onCancel: () => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      await api.post('/admin/users', { email: email.trim(), password })
      onDone()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'No se pudo crear')
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Field label="Email">
        <Input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoFocus
        />
      </Field>
      <Field label="Contraseña" hint={`Mínimo ${MIN_PASSWORD_LENGTH} caracteres.`}>
        <Input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          minLength={MIN_PASSWORD_LENGTH}
          autoComplete="new-password"
          required
        />
      </Field>

      {error && <Alert>{error}</Alert>}

      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancelar
        </Button>
        <Button type="submit" disabled={saving}>
          {saving ? 'Creando…' : 'Crear'}
        </Button>
      </div>
    </form>
  )
}
