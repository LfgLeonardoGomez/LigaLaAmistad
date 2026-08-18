import { useState } from 'react'
import type { FormEvent } from 'react'

import { api } from '../api/client'
import { COMMENT_MAX_LENGTH } from '../api/types'
import type { Match } from '../api/types'
import { Alert, Button, Field, Input, Textarea } from '../components/ui'
import { imageUrl } from '../api/images'

interface SetRow {
  a: string
  b: string
}

const EMPTY_SET: SetRow = { a: '', b: '' }

function toRows(match: Match): SetRow[] {
  if (match.sets.length === 0) return [{ ...EMPTY_SET }, { ...EMPTY_SET }]
  return match.sets.map((set) => ({
    a: String(set.team_a_games),
    b: String(set.team_b_games),
  }))
}

/**
 * Loads or replaces a result, with its photo and its comment.
 *
 * The rules are validated by the API — this only avoids the obvious round trip
 * and shows the same rules to the person filling the form.
 */
export function ResultForm({
  match,
  teamAName,
  teamBName,
  onDone,
  onCancel,
}: {
  match: Match
  teamAName: string
  teamBName: string
  onDone: () => void
  onCancel: () => void
}) {
  const [rows, setRows] = useState<SetRow[]>(() => toRows(match))
  const [comment, setComment] = useState(match.comment ?? '')
  const [photo, setPhoto] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const isFilled = (row: SetRow) => row.a !== '' && row.b !== ''
  const filled = rows.filter(isFilled)

  // Sets are renumbered by position below, so a gap would quietly turn "set 1
  // and set 3" into "set 1 and set 2" and send scores under the wrong numbers.
  // Better to refuse than to guess what the admin meant.
  const firstEmpty = rows.findIndex((row) => !isFilled(row))
  const hasGap = firstEmpty !== -1 && rows.slice(firstEmpty).some(isFilled)
  const setsWonByA = filled.filter((row) => Number(row.a) > Number(row.b)).length
  const setsWonByB = filled.filter((row) => Number(row.b) > Number(row.a)).length
  const hasTiedSet = filled.some((row) => Number(row.a) === Number(row.b))

  function update(index: number, side: 'a' | 'b', value: string) {
    setRows((current) =>
      current.map((row, position) => (position === index ? { ...row, [side]: value } : row)),
    )
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)

    const payload = {
      sets: filled.map((row, index) => ({
        set_number: index + 1,
        team_a_games: Number(row.a),
        team_b_games: Number(row.b),
      })),
      comment: comment.trim() === '' ? null : comment.trim(),
    }

    try {
      // POST loads a first result, PUT replaces an existing one.
      const path = `/admin/matches/${match.id}/result`
      if (match.status === 'played') await api.put(path, payload)
      else await api.post(path, payload)
      // The upload is its own call and can fail on its own. Doing it last means
      // a Cloudinary outage does not take the score and the comment with it.
      // It also needs the match to be `played`, which the call above guarantees.
      if (photo) await api.upload(`${path}/photo`, photo)
      onDone()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'No se pudo guardar el resultado')
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 text-sm">
        <span className="truncate text-right font-medium text-ink-900">{teamAName}</span>
        <span className="text-xs text-ink-400">vs</span>
        <span className="truncate font-medium text-ink-900">{teamBName}</span>
      </div>

      {rows.map((row, index) => (
        <div key={index} className="grid grid-cols-[1fr_auto_1fr] items-end gap-3">
          <Field label={index === 0 ? 'Set 1' : `Set ${index + 1}`}>
            <Input
              type="number"
              min={0}
              value={row.a}
              onChange={(event) => update(index, 'a', event.target.value)}
              className="text-center"
            />
          </Field>
          <span className="pb-2 text-ink-400">—</span>
          <Field label="&nbsp;">
            <Input
              type="number"
              min={0}
              value={row.b}
              onChange={(event) => update(index, 'b', event.target.value)}
              className="text-center"
            />
          </Field>
        </div>
      ))}

      {rows.length < 3 && (
        <Button
          type="button"
          variant="secondary"
          onClick={() => setRows((current) => [...current, { ...EMPTY_SET }])}
        >
          Agregar tercer set
        </Button>
      )}

      <Field
        label="Comentario"
        hint={`Opcional. Quedan ${COMMENT_MAX_LENGTH - comment.length} caracteres.`}
      >
        <Textarea
          rows={3}
          maxLength={COMMENT_MAX_LENGTH}
          value={comment}
          onChange={(event) => setComment(event.target.value)}
          placeholder="La cargada para la pareja que perdió…"
        />
      </Field>

      <Field label="Foto del partido" hint="JPG, PNG o WebP. Máximo 5 MB.">
        <Input
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={(event) => setPhoto(event.target.files?.[0] ?? null)}
          className="file:mr-3 file:rounded file:border-0 file:bg-ink-100 file:px-3 file:py-1.5 file:text-sm file:text-ink-700"
        />
      </Field>

      {match.photo_url && !photo && (
        <div className="flex items-center gap-3">
          <img
            src={imageUrl(match.photo_url, { width: 160, height: 112 })}
            alt=""
            className="h-14 w-20 rounded object-cover ring-1 ring-ink-200"
          />
          <span className="text-xs text-ink-500">
            Ya hay una foto cargada. Si elegís otra, la reemplaza.
          </span>
        </div>
      )}

      {hasGap && <Alert>Completá los sets en orden, sin saltear ninguno.</Alert>}
      {!hasGap && hasTiedSet && <Alert>Un set no puede terminar empatado.</Alert>}
      {!hasGap && !hasTiedSet && filled.length >= 2 && setsWonByA !== 2 && setsWonByB !== 2 && (
        <Alert>Una pareja tiene que ganar exactamente dos sets.</Alert>
      )}
      {error && <Alert>{error}</Alert>}

      <p className="text-xs text-ink-500">
        El ganador no se carga: se calcula solo a partir de los sets.
      </p>

      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancelar
        </Button>
        <Button type="submit" disabled={saving || hasGap || filled.length < 2}>
          {saving ? 'Guardando…' : match.status === 'played' ? 'Corregir' : 'Cargar resultado'}
        </Button>
      </div>
    </form>
  )
}
