import { api } from './client'
import type { AmericanoDraftOperations, AmericanoSetupCapabilities, EventDetail, ListEventsResponse } from './americano-types'

const collection = '/admin/americanos'

// Stable identity: page load effects must not restart on each render.
export const americanoDraftOperations: AmericanoDraftOperations = {
  listEvents: () => api.get<ListEventsResponse>(collection),
  createEvent: (request) => api.post<EventDetail>(collection, request),
  loadEvent: (eventId) => api.get<EventDetail>(`${collection}/${eventId}`),
  updateEvent: (eventId, request) => api.patch<EventDetail>(`${collection}/${eventId}`, request),
  addRegistration: (eventId, request) => api.post<EventDetail>(`${collection}/${eventId}/registrations`, request),
  updateRegistration: (eventId, registrationId, request) =>
    api.patch<EventDetail>(`${collection}/${eventId}/registrations/${registrationId}`, request),
  deleteRegistration: (eventId, registrationId, { expected_revision }) =>
    api.delete<EventDetail>(`${collection}/${eventId}/registrations/${registrationId}?expected_revision=${encodeURIComponent(expected_revision)}`),
}

// Only implemented setup capabilities are published; generation remains unavailable.
export const americanoSetupOperations: AmericanoDraftOperations & Pick<AmericanoSetupCapabilities, 'setZones' | 'randomizeZones'> = {
  ...americanoDraftOperations,
  setZones: (eventId, request) => api.put<EventDetail>(`${collection}/${eventId}/zones`, request),
  randomizeZones: (eventId, request) => api.post<EventDetail>(`${collection}/${eventId}/zones/randomize`, request),
}
