import { api } from './client'
import type {
  AmericanoDraftOperations, AmericanoPlayoffsOperations, AmericanoPlayoffsReadOperations, AmericanoQualificationOperations,
  AmericanoRoundOperations, AmericanoSetupCapabilities, ConfirmationResponse, EventDetail,
  GenerateFixtureResponse, ListEventsResponse, PlayoffsResponse, QualificationResponse,
  RoundResponse, SaveRoundResponse, StandingsResponse,
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
  addRegistrations: (eventId, request) => api.post<EventDetail>(`${collection}/${eventId}/registrations/bulk`, request),
  setZones: (eventId, request) => api.put<EventDetail>(`${collection}/${eventId}/zones`, request),
  clearZones: (eventId, { expected_revision }) =>
    api.delete<EventDetail>(`${collection}/${eventId}/zones?expected_revision=${encodeURIComponent(expected_revision)}`),
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

export const americanoQualificationOperations: AmericanoQualificationOperations = {
  loadEvent: americanoDraftOperations.loadEvent,
  loadQualification: (eventId) => api.get<QualificationResponse>(`${collection}/${eventId}/qualification`),
  saveTieResolutions: (eventId, request) =>
    api.put<QualificationResponse>(`${collection}/${eventId}/tie-resolutions`, request),
  confirmQualifiers: (eventId, request) =>
    api.post<ConfirmationResponse>(`${collection}/${eventId}/confirm-qualifiers`, request),
}

// Reading the bracket does not expose the future knockout score capability.
export const americanoPlayoffsReadOperations: AmericanoPlayoffsReadOperations = {
  loadEvent: americanoDraftOperations.loadEvent,
  loadPlayoffs: (eventId) => api.get<PlayoffsResponse>(`${collection}/${eventId}/playoffs`),
}

export const americanoPlayoffsOperations: AmericanoPlayoffsOperations = {
  ...americanoPlayoffsReadOperations,
  assignKnockoutCourt: (eventId, nodeId, request) =>
    api.put<PlayoffsResponse>(`${collection}/${eventId}/playoffs/${nodeId}/court`, request),
  saveKnockout: (eventId, nodeId, request) =>
    api.put<PlayoffsResponse>(`${collection}/${eventId}/playoffs/${nodeId}/result`, request),
}
