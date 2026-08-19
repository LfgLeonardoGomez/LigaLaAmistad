import { useMemo, useState } from 'react'
import type { FormEvent } from 'react'

import { api } from '../api/client'
import type { Match, MatchStatus, Team, Zone } from '../api/types'
import { VENUE_LABELS, formatTime, teamName, venueLabel } from '../api/types'
import { useResource } from '../api/useResource'
import { Modal } from '../components/Modal'
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Field,
  FilterTabs,
  Input,
  PageHeader,
  Select,
  Spinner,
  Table,
  Td,
  Th,
} from '../components/ui'
import { ResultForm } from './ResultForm'

type Filter = MatchStatus | 'all'

const FILTERS: { value: Filter; label: string }[] = [
  { value: 'all', label: 'Todos' },
  { value: 'pending', label: 'Pendientes' },
  { value: 'played', label: 'Jugados' },
]

export function MatchesPage() {
  const [filter, setFilter] = useState<Filter>('all')
  const path = filter === 'all' ? '/admin/matches' : `/admin/matches?status=${filter}`

  const matches = useResource<Match[]>(path)
  const teams = useResource<Team[]>('/admin/teams')
  const zones = useResource<Zone[]>('/public/zones')

  const [creating, setCreating] = useState(false)
  const [editing, setEditing] = useState<Match | null>(null)
  const [loadingResult, setLoadingResult] = useState<Match | null>(null)
  const [error, setError] = useState<string | null>(null)

  const teamsById = useMemo(
    () => new Map((teams.data ?? []).map((team) => [team.id, team])),
    [teams.data],
  )

  function nameOf(id: number) {
    return teamName(teamsById.get(id))
  }

  async function run(action: () => Promise<unknown>) {
    setError(null)
    try {
      await action()
      matches.reload()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'No se pudo completar la acción')
    }
  }

  return (
    <>
      <PageHeader
        title="Partidos"
        description="Un partido con resultado queda congelado. Para corregir la fecha o las parejas, primero hay que deshacer el resultado."
        action={<Button onClick={() => setCreating(true)}>Nuevo partido</Button>}
      />

      <div className="mb-4">
      <FilterTabs
          label="Filtrar por estado"
          value={filter}
          onChange={setFilter}
          options={FILTERS.map((f) => ({ value: f.value, label: f.label }))}
        />
      </div>

      {error && (
        <div className="mb-4">
          <Alert>{error}</Alert>
        </div>
      )}
      {matches.error && (
        <div className="mb-4">
          <Alert>{matches.error}</Alert>
        </div>
      )}

      <Card>
        {matches.loading ? (
          <Spinner />
        ) : !matches.data?.length ? (
          <EmptyState>No hay partidos para este filtro.</EmptyState>
        ) : (
          <Table
            head={
              <tr>
                <Th>Fecha</Th>
                <Th>Partido</Th>
                <Th>Lugar</Th>
                <Th>Resultado</Th>
                <Th>Estado</Th>
                <Th className="text-right">Acciones</Th>
              </tr>
            }
          >
            {matches.data.map((match) => (
              <tr key={match.id} className="hover:bg-ink-50">
                <Td className="whitespace-nowrap text-ink-600">
                  <div className="flex flex-col gap-0.5">
                    <span>{match.date}</span>
                    {match.time && (
                      <span className="text-xs text-ink-500">{formatTime(match.time)}</span>
                    )}
                  </div>
                </Td>
                <Td>
                  <div className="flex flex-col gap-0.5">
                    <Side
                      name={nameOf(match.team_a_id)}
                      winner={match.winner_team_id === match.team_a_id}
                    />
                    <Side
                      name={nameOf(match.team_b_id)}
                      winner={match.winner_team_id === match.team_b_id}
                    />
                  </div>
                </Td>
                <Td className="whitespace-nowrap text-ink-600">
                  {venueLabel(match.venue) ?? '—'}
                </Td>
                <Td className="whitespace-nowrap font-mono text-xs text-ink-600">
                  {match.sets.length === 0
                    ? '—'
                    : match.sets
                        .map((set) => `${set.team_a_games}-${set.team_b_games}`)
                        .join('  ')}
                </Td>
                <Td>
                  <Badge value={match.status} />
                </Td>
                <Td>
                  <div className="flex justify-end gap-1">
                    <Button variant="ghost" onClick={() => setLoadingResult(match)}>
                      {match.status === 'played' ? 'Corregir' : 'Cargar resultado'}
                    </Button>
                    {match.status === 'played' ? (
                      <Button
                        variant="ghost"
                        onClick={() => {
                          if (!confirm('¿Deshacer el resultado? El partido vuelve a pendiente.')) return
                          void run(() => api.delete(`/admin/matches/${match.id}/result`))
                        }}
                      >
                        Deshacer
                      </Button>
                    ) : (
                      <>
                        <Button variant="ghost" onClick={() => setEditing(match)}>
                          Editar
                        </Button>
                        <Button
                          variant="ghost"
                          onClick={() => {
                            if (!confirm('¿Eliminar el partido?')) return
                            void run(() => api.delete(`/admin/matches/${match.id}`))
                          }}
                        >
                          Eliminar
                        </Button>
                      </>
                    )}
                  </div>
                </Td>
              </tr>
            ))}
          </Table>
        )}
      </Card>

      {creating && (
        <Modal title="Nuevo partido" onClose={() => setCreating(false)}>
          <CreateForm
            teams={teams.data ?? []}
            zones={zones.data ?? []}
            onDone={() => {
              setCreating(false)
              matches.reload()
            }}
            onCancel={() => setCreating(false)}
          />
        </Modal>
      )}

      {editing && (
        <Modal title="Editar partido" onClose={() => setEditing(null)}>
          <EditForm
            match={editing}
            onDone={() => {
              setEditing(null)
              matches.reload()
            }}
            onCancel={() => setEditing(null)}
          />
        </Modal>
      )}

      {loadingResult && (
        <Modal
          title={loadingResult.status === 'played' ? 'Corregir resultado' : 'Cargar resultado'}
          onClose={() => setLoadingResult(null)}
        >
          <ResultForm
            match={loadingResult}
            teamAName={nameOf(loadingResult.team_a_id)}
            teamBName={nameOf(loadingResult.team_b_id)}
            onDone={() => {
              setLoadingResult(null)
              matches.reload()
            }}
            onCancel={() => setLoadingResult(null)}
          />
        </Modal>
      )}
    </>
  )
}

function Side({ name, winner }: { name: string; winner: boolean }) {
  return (
    <span className={winner ? 'text-sm font-semibold text-ink-900' : 'text-sm text-ink-500'}>
      {name}
      {winner && <span className="ml-1.5 text-xs text-emerald-600">ganó</span>}
    </span>
  )
}

function CreateForm({
  teams,
  zones,
  onDone,
  onCancel,
}: {
  teams: Team[]
  zones: Zone[]
  onDone: () => void
  onCancel: () => void
}) {
  const [zoneId, setZoneId] = useState('')
  const [teamA, setTeamA] = useState('')
  const [teamB, setTeamB] = useState('')
  const [date, setDate] = useState('')
  const [time, setTime] = useState('')
  const [venue, setVenue] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  // The zone is only a filter for the selects. It is never sent: the API
  // derives a match's zone from its teams.
  const options = zoneId ? teams.filter((team) => team.zone_id === Number(zoneId)) : []

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      await api.post('/admin/matches', {
        team_a_id: Number(teamA),
        team_b_id: Number(teamB),
        date,
        // Both are optional: an empty field means "still to be agreed", which
        // the API stores as null, not as an empty string.
        time: time || null,
        venue: venue || null,
      })
      onDone()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'No se pudo crear el partido')
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Field label="Zona" hint="Solo filtra las parejas. El partido no guarda la zona.">
        <Select
          value={zoneId}
          onChange={(event) => {
            setZoneId(event.target.value)
            setTeamA('')
            setTeamB('')
          }}
          required
        >
          <option value="">Elegí una zona</option>
          {zones.map((zone) => (
            <option key={zone.id} value={zone.id}>
              {zone.name}
            </option>
          ))}
        </Select>
      </Field>

      <Field label="Pareja A">
        <Select value={teamA} onChange={(e) => setTeamA(e.target.value)} required disabled={!zoneId}>
          <option value="">Elegí una pareja</option>
          {options.map((team) => (
            <option key={team.id} value={team.id} disabled={String(team.id) === teamB}>
              {teamName(team)}
            </option>
          ))}
        </Select>
      </Field>

      <Field label="Pareja B">
        <Select value={teamB} onChange={(e) => setTeamB(e.target.value)} required disabled={!zoneId}>
          <option value="">Elegí una pareja</option>
          {options.map((team) => (
            <option key={team.id} value={team.id} disabled={String(team.id) === teamA}>
              {teamName(team)}
            </option>
          ))}
        </Select>
      </Field>

      <Field label="Fecha">
        <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
      </Field>

      <ScheduleFields
        time={time}
        venue={venue}
        onTimeChange={setTime}
        onVenueChange={setVenue}
      />

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

/**
 * Time and venue, shared by the create and the edit form. Both are optional:
 * a match is scheduled before the pairs agree on where and at what time, so
 * the select starts at "Sin definir" and stays there without complaining.
 */
function ScheduleFields({
  time,
  venue,
  onTimeChange,
  onVenueChange,
}: {
  time: string
  venue: string
  onTimeChange: (value: string) => void
  onVenueChange: (value: string) => void
}) {
  return (
    <>
      <Field label="Hora" hint="Opcional. Se puede cargar después, cuando las parejas la arreglen.">
        <Input type="time" value={time} onChange={(event) => onTimeChange(event.target.value)} />
      </Field>

      <Field label="Lugar" hint="Opcional. Uno de los clubes de la liga.">
        <Select value={venue} onChange={(event) => onVenueChange(event.target.value)}>
          <option value="">Sin definir</option>
          {Object.entries(VENUE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
      </Field>
    </>
  )
}

/**
 * Corrects the date, the time and the venue of a pending match.
 *
 * It leaves the pairs alone: swapping them is building another match, and
 * deleting this one and creating it again says that far more clearly.
 */
function EditForm({
  match,
  onDone,
  onCancel,
}: {
  match: Match
  onDone: () => void
  onCancel: () => void
}) {
  const [date, setDate] = useState(match.date)
  // The API answers `HH:MM:SS` and `<input type="time">` wants `HH:MM`.
  const [time, setTime] = useState(formatTime(match.time) ?? '')
  const [venue, setVenue] = useState(match.venue ?? '')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      // An explicit null is what erases a time or a venue already loaded.
      await api.patch(`/admin/matches/${match.id}`, {
        date,
        time: time || null,
        venue: venue || null,
      })
      onDone()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'No se pudo guardar el partido')
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Field label="Fecha">
        <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
      </Field>

      <ScheduleFields
        time={time}
        venue={venue}
        onTimeChange={setTime}
        onVenueChange={setVenue}
      />

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
