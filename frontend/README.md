# Liga La Amistad — Panel de administración

React + TypeScript + Vite + Tailwind.

## Setup

```bash
npm install
npm run dev          # http://localhost:5173
```

The API must be running on port 8000. See `../backend/README.md`.

```bash
npm run build        # type check + production bundle
npm run lint         # type check only
```

## Configuration

Copy `.env.example` to `.env` if the API is not on `http://localhost:8000`.

**Use `localhost`, never `127.0.0.1`.** For cookies an IP address is its own
site, so a page served from `localhost` calling `127.0.0.1` makes a cross-site
request and the browser silently drops the `SameSite=Lax` session cookie. The
symptom is nasty: login answers 200 and every call after it answers 401.

The same rule bites in production. The front end on Vercel and the API on
Railway are genuinely different sites, so the backend must run with
`COOKIE_SAMESITE=none` and `COOKIE_SECURE=true` there.

## Layout

```txt
src/
  api/          fetch wrapper, response types, useResource hook
  auth/         AuthContext, login screen
  components/   layout, modal, shared UI primitives
  pages/        one file per admin screen
```

There is no state manager and no data-fetching library. The session lives in
`AuthContext`, and every screen loads its own data with `useResource`. Five
screens do not justify more than that.

The session is an httpOnly cookie, so JavaScript cannot read it. Whether a
session is alive is only known by asking `/auth/me`, which is what
`AuthContext` does on mount.

## Screens

| Ruta | Qué hace |
|---|---|
| `/parejas` | Alta y edición. No hay borrado: una pareja se da de baja. |
| `/partidos` | Alta, carga y corrección de resultados. |
| `/tabla` | Posiciones por zona, calculadas por la API. |
| `/sponsors` | Alta, edición, visibilidad y borrado. |
| `/administradores` | Alta, cambio de contraseña y desactivación. |

There is no public site here yet, and no sign-up screen: access is granted by
an existing administrator.
