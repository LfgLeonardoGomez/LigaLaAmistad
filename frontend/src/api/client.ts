// `localhost` and not `127.0.0.1`, deliberately. An IP address is its own site
// for cookie purposes, so calling 127.0.0.1 from a page served on localhost is
// a cross-site request and the browser drops the SameSite=Lax session cookie.
// Login answers 200 and every call after it answers 401.
const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

/** An error carrying the status code, so callers can react to 401 or 409. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

/** FastAPI puts validation errors in a list; flatten it into one line. */
function readDetail(body: unknown, fallback: string): string {
  if (typeof body !== 'object' || body === null) return fallback
  const detail = (body as { detail?: unknown }).detail

  if (typeof detail === 'string') return detail

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item !== 'object' || item === null) return null
        const { loc, msg } = item as { loc?: unknown[]; msg?: string }
        const field = Array.isArray(loc) ? loc[loc.length - 1] : undefined
        return field ? `${String(field)}: ${msg}` : msg
      })
      .filter(Boolean)
    if (messages.length > 0) return messages.join(' · ')
  }

  return fallback
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      // The session lives in an httpOnly cookie, so every call must carry it.
      credentials: 'include',
      ...init,
    })
  } catch {
    throw new ApiError(0, 'No se pudo conectar con el servidor')
  }

  if (response.status === 204) return undefined as T

  const body = await response.json().catch(() => null)

  if (!response.ok) {
    // A 401 on any call means the session is gone, whatever screen asked for
    // it. Announcing it here is what stops a dead session from looking like
    // an empty table.
    if (response.status === 401) {
      window.dispatchEvent(new CustomEvent('liga:session-expired'))
    }
    throw new ApiError(response.status, readDetail(body, `Error ${response.status}`))
  }

  return body as T
}

function withJson(method: string, data: unknown): RequestInit {
  return {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, data: unknown) => request<T>(path, withJson('POST', data)),
  put: <T>(path: string, data: unknown) => request<T>(path, withJson('PUT', data)),
  patch: <T>(path: string, data: unknown) => request<T>(path, withJson('PATCH', data)),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),

  upload: <T>(path: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    // No Content-Type header: the browser has to set the multipart boundary.
    return request<T>(path, { method: 'POST', body: form })
  },
}
