import { useId } from 'react'
import type { QualificationSlotsProps } from '../../api/americano-types'
import { Select } from '../ui'

export function QualificationSlots({ preview, registrations, resolutions, disabled, onChange }: QualificationSlotsProps) {
  const id = useId()
  const names = new Map(registrations.map(pair => [pair.id, `${pair.player1_name} / ${pair.player2_name} · #${pair.id}`]))
  const selected = (zoneId: number, position: number) => resolutions.find(value => value.zone_id === zoneId && value.position === position)?.registration_id
  return <div className="space-y-5">
    <p className="text-sm text-ink-600">Los empates relevantes se resuelven mediante un sorteo humano. Seleccioná su resultado; el sistema no sortea ni desempata por nombre o ID.</p>
    {preview.quotas.map(quota => {
      const zone = preview.standings.find(value => value.zone.id === quota.zone_id)?.zone
      const slots = preview.slots.filter(slot => slot.zone_id === quota.zone_id).sort((a, b) => a.position - b.position)
      return <fieldset key={quota.zone_id} className="space-y-3 rounded-md border border-ink-200 p-4">
        <legend className="px-2 text-sm font-semibold text-ink-800">Zona {zone?.label ?? 'no disponible'} · {quota.required} plazas</legend>
        {slots.map(slot => {
          const chosen = selected(slot.zone_id, slot.position)
          const labelId = `${id}-${slot.zone_id}-${slot.position}`
          const duplicate = chosen !== undefined && resolutions.some(value => value.zone_id === slot.zone_id && value.position !== slot.position && value.registration_id === chosen)
          const missing = slot.requires_resolution && (chosen === undefined || !slot.candidate_registration_ids.includes(chosen) || duplicate)
          return <div key={slot.position} className="grid items-start gap-2 sm:grid-cols-[8rem_1fr]">
            <label id={`${labelId}-label`} htmlFor={slot.requires_resolution ? labelId : undefined} className="pt-2 text-sm font-medium text-ink-700">Plaza {slot.position}</label>
            {slot.requires_resolution ? <div>
              <Select id={labelId} aria-describedby={`${labelId}-help`}
                aria-label={`Zona ${zone?.label ?? 'no disponible'}, plaza ${slot.position}`} aria-invalid={missing}
                disabled={disabled} value={chosen ?? ''} onChange={event => {
                  const raw = event.currentTarget.value
                  const next = raw === '' ? null : Number(raw)
                  if (next !== null && (!slot.candidate_registration_ids.includes(next) || resolutions.some(value => value.zone_id === slot.zone_id && value.position !== slot.position && value.registration_id === next))) return
                  const other = resolutions.filter(value => value.zone_id !== slot.zone_id || value.position !== slot.position)
                  onChange(next === null ? other : [...other, { zone_id: slot.zone_id, position: slot.position, registration_id: next }])
                }}>
                <option value="">Seleccioná según el sorteo humano</option>
                {slot.candidate_registration_ids.map(candidate => <option key={candidate} value={candidate}
                  disabled={resolutions.some(value => value.zone_id === slot.zone_id && value.position !== slot.position && value.registration_id === candidate)}>
                  {names.get(candidate) ?? `Pareja #${candidate} no disponible`}
                </option>)}
              </Select>
              <p id={`${labelId}-help`} className={`mt-1 text-xs ${missing ? 'text-amber-700' : 'text-ink-500'}`}>
                {duplicate ? 'Esta pareja ya ocupa otra plaza.' : missing ? 'Pendiente de resolución humana.' : 'Selección humana; se aplica al guardar todas las resoluciones.'}
              </p>
            </div> : <p className="py-2 text-sm text-ink-800">{slot.registration_id === null ? 'Plaza pendiente' : names.get(slot.registration_id) ?? `Pareja #${slot.registration_id}`} <span className="text-xs text-ink-500">· posición firme</span></p>}
          </div>
        })}
      </fieldset>
    })}
  </div>
}
