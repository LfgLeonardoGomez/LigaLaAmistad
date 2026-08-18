import { useState } from 'react'
import type { FormEvent } from 'react'

import { api } from '../api/client'
import type { Team, Zone } from '../api/types'
import { useResource } from '../api/useResource'
import { Modal } from '../components/Modal'
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Field,
  Input,
  PageHeader,
  Select,
  Spinner,
  Table,
  Td,
  Th,
} from '../components/ui'
import { imageUrl } from '../api/images'

export function TeamsPage() {
  const zones = useResource<Zone[]>('/public/zones')
  const teams = useResource<Team[]>('/admin/teams')
  const [editing, setEditing] = useState<Team | null>(null)
  const [creating, setCreating] = useState(false)
  const [warning, setWarning] = useState<string | null>(null)

  function done(message?: string) {
    setEditing(null)
    setCreating(false)
    setWarning(message ?? null)
    teams.reload()
  }

  return (
    <>
      <PageHeader
        title="Parejas"
        description="Las parejas no se eliminan. Una que abandona la liga se da de baja y conserva su historial."
        action={<Button onClick={() => setCreating(true)}>Nueva pareja</Button>}
      />

      {teams.error && <Alert>{teams.error}</Alert>}
      {warning && (
        <div className="mb-4">
          <Alert tone="info">{warning}</Alert>
        </div>
      )}

      <Card>
        {teams.loading ? (
          <Spinner />
        ) : !teams.data?.length ? (
          <EmptyState>Todavía no hay parejas cargadas.</EmptyState>
        ) : (
          <Table
            head={
              <tr>
                <Th>Pareja</Th>
                <Th>Zona</Th>
                <Th>Estado</Th>
                <Th className="text-right">Acciones</Th>
              </tr>
            }
          >
            {teams.data.map((team) => (
              <tr key={team.id} className="hover:bg-ink-50">
                <Td>
                  <div className="flex items-center gap-3">
                    <Photo team={team} />
                    <span className="font-medium text-ink-900">
                      {team.player_one_name} / {team.player_two_name}
                    </span>
                  </div>
                </Td>
                <Td className="text-ink-600">
                  {zones.data?.find((zone) => zone.id === team.zone_id)?.name ?? '—'}
                </Td>
                <Td>
                  <Badge value={team.status} />
                </Td>
                <Td className="text-right">
                  <Button variant="ghost" onClick={() => setEditing(team)}>
                    Editar
                  </Button>
                </Td>
              </tr>
            ))}
          </Table>
        )}
      </Card>

      {creating && (
        <Modal title="Nueva pareja" onClose={() => setCreating(false)}>
          <CreateForm zones={zones.data ?? []} onDone={done} onCancel={() => setCreating(false)} />
        </Modal>
      )}

      {editing && (
        <Modal title="Editar pareja" onClose={() => setEditing(null)}>
          <EditForm team={editing} onDone={done} onCancel={() => setEditing(null)} />
        </Modal>
      )}
    </>
  )
}

function Photo({ team }: { team: Team }) {
  if (team.photo_url) {
    return (
      <img
        src={imageUrl(team.photo_url, { width: 72, height: 72 })}
        alt=""
        className="h-9 w-9 shrink-0 rounded-full object-cover ring-1 ring-ink-200"
      />
    )
  }
  return (
    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-ink-100 text-xs font-medium text-ink-400">
      {team.player_one_name.charAt(0).toUpperCase()}
    </span>
  )
}

function CreateForm({
  zones,
  onDone,
  onCancel,
}: {
  zones: Zone[]
  onDone: (warning?: string) => void
  onCancel: () => void
}) {
  const [playerOne, setPlayerOne] = useState('')
  const [playerTwo, setPlayerTwo] = useState('')
  const [zoneId, setZoneId] = useState('')
  const [photo, setPhoto] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      // Two calls behind one form: the upload endpoint needs an id, and the
      // id does not exist until the pair is created. Doing it here spares the
      // admin from creating a pair and then having to edit it to add a photo.
      const created = await api.post<Team>('/admin/teams', {
        zone_id: Number(zoneId),
        player_one_name: playerOne.trim(),
        player_two_name: playerTwo.trim(),
      })
      // The pair exists from here on. A failed upload must not look like a
      // failed creation, or the admin creates the same pair twice.
      if (photo) {
        try {
          await api.upload(`/admin/teams/${created.id}/photo`, photo)
        } catch (cause) {
          const detail = cause instanceof Error ? cause.message : 'error desconocido'
          onDone(`La pareja se creó, pero la foto no se pudo subir (${detail}). Podés agregarla desde Editar.`)
          return
        }
      }
      onDone()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'No se pudo crear')
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Field label="Jugador 1">
        <Input value={playerOne} onChange={(e) => setPlayerOne(e.target.value)} required autoFocus />
      </Field>
      <Field label="Jugador 2">
        <Input value={playerTwo} onChange={(e) => setPlayerTwo(e.target.value)} required />
      </Field>
      <Field label="Zona" hint="La zona no se puede cambiar después del alta.">
        <Select value={zoneId} onChange={(e) => setZoneId(e.target.value)} required>
          <option value="">Elegí una zona</option>
          {zones.map((zone) => (
            <option key={zone.id} value={zone.id}>
              {zone.name}
            </option>
          ))}
        </Select>
      </Field>

      <Field label="Foto" hint="Opcional. JPG, PNG o WebP, máximo 5 MB.">
        <Input
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={(e) => setPhoto(e.target.files?.[0] ?? null)}
          className="file:mr-3 file:rounded file:border-0 file:bg-ink-100 file:px-3 file:py-1.5 file:text-sm file:text-ink-700"
        />
      </Field>

      {error && <Alert>{error}</Alert>}

      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancelar
        </Button>
        <Button type="submit" disabled={saving}>
          {saving ? 'Guardando…' : 'Crear'}
        </Button>
      </div>
    </form>
  )
}

function EditForm({
  team,
  onDone,
  onCancel,
}: {
  team: Team
  onDone: () => void
  onCancel: () => void
}) {
  const [playerOne, setPlayerOne] = useState(team.player_one_name)
  const [playerTwo, setPlayerTwo] = useState(team.player_two_name)
  const [status, setStatus] = useState(team.status)
  const [photo, setPhoto] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      await api.patch(`/admin/teams/${team.id}`, {
        player_one_name: playerOne.trim(),
        player_two_name: playerTwo.trim(),
        status,
      })
      // Uploading is a separate call, and it can fail on its own. Doing it last
      // means a Cloudinary outage does not lose the name and status edits.
      if (photo) await api.upload(`/admin/teams/${team.id}/photo`, photo)
      onDone()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'No se pudo guardar')
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Field label="Jugador 1">
        <Input value={playerOne} onChange={(e) => setPlayerOne(e.target.value)} required autoFocus />
      </Field>
      <Field label="Jugador 2">
        <Input value={playerTwo} onChange={(e) => setPlayerTwo(e.target.value)} required />
      </Field>
      <Field label="Estado" hint="Una pareja dada de baja sigue en la tabla con sus puntos.">
        <Select value={status} onChange={(e) => setStatus(e.target.value as Team['status'])}>
          <option value="active">Activa</option>
          <option value="withdrawn">Dada de baja</option>
        </Select>
      </Field>
      <Field label="Foto" hint="JPG, PNG o WebP. Máximo 5 MB.">
        <Input
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={(e) => setPhoto(e.target.files?.[0] ?? null)}
          className="file:mr-3 file:rounded file:border-0 file:bg-ink-100 file:px-3 file:py-1.5 file:text-sm file:text-ink-700"
        />
      </Field>

      {error && <Alert>{error}</Alert>}

      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancelar
        </Button>
        <Button type="submit" disabled={saving}>
          {saving ? 'Guardando…' : 'Guardar'}
        </Button>
      </div>
    </form>
  )
}
