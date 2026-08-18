import { useState } from 'react'
import type { FormEvent } from 'react'

import { api } from '../api/client'
import type { Sponsor } from '../api/types'
import { useResource } from '../api/useResource'
import { Modal } from '../components/Modal'
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
import { imageUrl } from '../api/images'

export function SponsorsPage() {
  const sponsors = useResource<Sponsor[]>('/admin/sponsors')
  const [editing, setEditing] = useState<Sponsor | null>(null)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function remove(sponsor: Sponsor) {
    if (!confirm(`¿Eliminar a ${sponsor.name}?`)) return
    setError(null)
    try {
      await api.delete(`/admin/sponsors/${sponsor.id}`)
      sponsors.reload()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'No se pudo eliminar')
    }
  }

  async function toggle(sponsor: Sponsor) {
    setError(null)
    try {
      await api.patch(`/admin/sponsors/${sponsor.id}`, { is_active: !sponsor.is_active })
      sponsors.reload()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'No se pudo actualizar')
    }
  }

  return (
    <>
      <PageHeader
        title="Sponsors"
        description="Solo los activos se muestran en la web pública."
        action={<Button onClick={() => setCreating(true)}>Nuevo sponsor</Button>}
      />

      {(error || sponsors.error) && (
        <div className="mb-4">
          <Alert>{error ?? sponsors.error}</Alert>
        </div>
      )}

      <Card>
        {sponsors.loading ? (
          <Spinner />
        ) : !sponsors.data?.length ? (
          <EmptyState>Todavía no hay sponsors cargados.</EmptyState>
        ) : (
          <Table
            head={
              <tr>
                <Th>Sponsor</Th>
                <Th>Sitio</Th>
                <Th>Visible</Th>
                <Th className="text-right">Acciones</Th>
              </tr>
            }
          >
            {sponsors.data.map((sponsor) => (
              <tr key={sponsor.id} className="hover:bg-ink-50">
                <Td>
                  <div className="flex items-center gap-3">
                    <img
                      src={imageUrl(sponsor.logo_url, { width: 96, height: 96 })}
                      alt=""
                      className="h-8 w-8 rounded object-contain ring-1 ring-ink-200"
                    />
                    <span className="font-medium text-ink-900">{sponsor.name}</span>
                  </div>
                </Td>
                <Td className="max-w-xs truncate text-ink-500">{sponsor.url ?? '—'}</Td>
                <Td>
                  <button
                    type="button"
                    onClick={() => void toggle(sponsor)}
                    aria-pressed={sponsor.is_active}
                    className={`relative h-5 w-9 rounded-full transition-colors ${
                      sponsor.is_active ? 'bg-emerald-500' : 'bg-ink-300'
                    }`}
                  >
                    <span className="sr-only">
                      {sponsor.is_active ? 'Ocultar de la web' : 'Mostrar en la web'}
                    </span>
                    <span
                      className={`absolute top-0.5 h-4 w-4 rounded-full bg-surface transition-all ${
                        sponsor.is_active ? 'left-4.5' : 'left-0.5'
                      }`}
                    />
                  </button>
                </Td>
                <Td className="text-right">
                  <Button variant="ghost" onClick={() => setEditing(sponsor)}>
                    Editar
                  </Button>
                  <Button variant="ghost" onClick={() => void remove(sponsor)}>
                    Eliminar
                  </Button>
                </Td>
              </tr>
            ))}
          </Table>
        )}
      </Card>

      {(creating || editing) && (
        <Modal
          title={editing ? 'Editar sponsor' : 'Nuevo sponsor'}
          onClose={() => {
            setCreating(false)
            setEditing(null)
          }}
        >
          <SponsorForm
            sponsor={editing}
            onDone={() => {
              setCreating(false)
              setEditing(null)
              sponsors.reload()
            }}
            onCancel={() => {
              setCreating(false)
              setEditing(null)
            }}
          />
        </Modal>
      )}
    </>
  )
}

function SponsorForm({
  sponsor,
  onDone,
  onCancel,
}: {
  sponsor: Sponsor | null
  onDone: () => void
  onCancel: () => void
}) {
  const [name, setName] = useState(sponsor?.name ?? '')
  const [url, setUrl] = useState(sponsor?.url ?? '')
  const [logoUrl, setLogoUrl] = useState(sponsor?.logo_url ?? '')
  const [logo, setLogo] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)

    try {
      const payload = { name: name.trim(), url: url.trim() || null }

      if (sponsor) {
        await api.patch(`/admin/sponsors/${sponsor.id}`, payload)
        if (logo) await api.upload(`/admin/sponsors/${sponsor.id}/logo`, logo)
      } else {
        // The API requires a logo_url on creation, so a brand new sponsor is
        // created with a placeholder and the real logo is uploaded right after.
        const created = await api.post<Sponsor>('/admin/sponsors', {
          ...payload,
          logo_url: logoUrl.trim() || 'https://placehold.co/200x200?text=Logo',
        })
        if (logo) await api.upload(`/admin/sponsors/${created.id}/logo`, logo)
      }
      onDone()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'No se pudo guardar')
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Field label="Nombre">
        <Input value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
      </Field>

      <Field label="Sitio web" hint="Opcional.">
        <Input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://…"
        />
      </Field>

      {!sponsor && (
        <Field label="URL del logo" hint="Opcional si vas a subir un archivo.">
          <Input value={logoUrl} onChange={(e) => setLogoUrl(e.target.value)} placeholder="https://…" />
        </Field>
      )}

      <Field label="Subir logo" hint="JPG, PNG o WebP. Máximo 5 MB.">
        <Input
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={(e) => setLogo(e.target.files?.[0] ?? null)}
          className="file:mr-3 file:rounded file:border-0 file:bg-ink-100 file:px-3 file:py-1.5 file:text-sm file:text-ink-700"
        />
      </Field>

      {error && <Alert>{error}</Alert>}

      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancelar
        </Button>
        <Button type="submit" disabled={saving}>
          {saving ? 'Guardando…' : sponsor ? 'Guardar' : 'Crear'}
        </Button>
      </div>
    </form>
  )
}
