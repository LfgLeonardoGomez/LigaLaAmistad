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

## Fotos del home

El hero y la banda de scroll usan `public/images/court.svg`, un marcador de
posición dibujado a mano para que el sitio nunca se vea roto. Para poner fotos
reales:

1. Dejá los archivos en `public/images/` (por ejemplo `hero.jpg` y `band.jpg`).
2. Cambiá las dos variables en `src/index.css`:

```css
:root {
  --hero-image: url('/images/hero.jpg');
  --band-image: url('/images/band.jpg');
}
```

Sobre la foto va un velo teñido con el color de fondo del tema activo, así una
misma imagen sirve para las tres paletas. Aun así, conviene elegir fotos con la
zona central despejada: ahí va el texto.

Optimizá antes de subirlas. Un JPG de cámara pesa varios MB y es lo primero que
carga el visitante, casi siempre desde el teléfono. Apuntá a menos de 300 KB y
un ancho máximo de 1920 px.

### La banda que parece una ventana

La sección `.photo-band` deja la foto quieta mientras el contenido se desliza
por encima. Está hecha con `clip-path: inset(0)` más un hijo `position: fixed`,
y **no** con `background-attachment: fixed`, que es más corto pero iOS Safari
lo ignora — y este sitio se lee sobre todo desde un teléfono.

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
