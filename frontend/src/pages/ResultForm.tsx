import { useState } from 'react'
import type { FormEvent } from 'react'

import { api } from '../api/client'
import type { Match } from '../api/types'
import { Alert, Button, Field, Input } from '../components/ui'

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
 * Loads or replaces a result.
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
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const filled = rows.filter((row) => row.a !== '' && row.b !== '')
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
    }

    try {
      // POST loads a first result, PUT replaces an existing one.
      const path = `/admin/matches/${match.id}/result`
      if (match.status === 'played') await api.put(path, payload)
      else await api.post(path, payload)
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

      {hasTiedSet && <Alert>Un set no puede terminar empatado.</Alert>}
      {!hasTiedSet && filled.length >= 2 && setsWonByA !== 2 && setsWonByB !== 2 && (
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
        <Button type="submit" disabled={saving || filled.length < 2}>
          {saving ? 'Guardando…' : match.status === 'played' ? 'Corregir' : 'Cargar resultado'}
        </Button>
      </div>
    </form>
  )
}
