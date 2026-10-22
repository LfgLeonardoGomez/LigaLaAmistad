import { api } from './client'
import type {
  AmericanoDraftOperations, AmericanoRoundOperations, AmericanoSetupCapabilities,
  EventDetail, GenerateFixtureResponse, ListEventsResponse, RoundResponse, SaveRoundResponse, StandingsResponse,
} from './americano-types'

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

// Stable setup port publishes only implemented capabilities.
export const americanoSetupOperations: AmericanoDraftOperations & AmericanoSetupCapabilities = {
  ...americanoDraftOperations,
  setZones: (eventId, request) => api.put<EventDetail>(`${collection}/${eventId}/zones`, request),
  randomizeZones: (eventId, request) => api.post<EventDetail>(`${collection}/${eventId}/zones/randomize`, request),
  generateFixture: (eventId, request) => api.post<GenerateFixtureResponse>(`${collection}/${eventId}/fixture`, request),
}

// Stable round port: production mounting and editing are separate integration gates.
export const americanoRoundOperations: AmericanoRoundOperations = {
  loadEvent: americanoDraftOperations.loadEvent,
  loadRound: (eventId, roundNumber) => api.get<RoundResponse>(`${collection}/${eventId}/rounds/${roundNumber}`),
  loadStandings: (eventId) => api.get<StandingsResponse>(`${collection}/${eventId}/standings`),
  saveRound: (eventId, roundNumber, request) =>
    api.put<SaveRoundResponse>(`${collection}/${eventId}/rounds/${roundNumber}/results`, request),
}
