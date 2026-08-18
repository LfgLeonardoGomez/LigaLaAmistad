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

El hero y la banda de scroll usan una sola foto, `public/images/hero.jpg`, con
dos encuadres distintos. Se controla desde cuatro variables en `src/index.css`:

```css
:root {
  --hero-image: url('/images/hero.jpg');
  --hero-position: center 40%;
  --band-image: url('/images/hero.jpg');
  --band-position: center 80%;
}
```

Sobre la foto va un velo tenido con el color de fondo del tema activo, asi una
misma imagen sirve para las tres paletas.

Al elegir una foto nueva:

- **Ancho minimo 1280 px**, mejor 1920. Una imagen de 700 px se estira al doble
  en un monitor comun y se ve borrosa. Es lo primero que carga el visitante.
- **Menos de 300 KB.** Casi todos entran desde el telefono.
- **Centro despejado**, que es donde va el texto.

### La banda que parece una ventana

La seccion `.photo-band` deja la foto quieta mientras el contenido se desliza
por encima. Esta hecha con `clip-path: inset(0)` mas un hijo `position: fixed`,
y **no** con `background-attachment: fixed`, que es mas corto pero iOS Safari
lo ignora — y este sitio se lee sobre todo desde un telefono.

## Deploy en Vercel

En Vercel, **New Project** -> importar el repo. Como el repo tiene backend y
frontend juntos, hay una sola cosa que Vercel no adivina:

| Campo | Valor |
|---|---|
| **Root Directory** | `frontend` |
| Framework Preset | Vite (lo detecta solo) |
| Build Command | `npm run build` (por defecto) |
| Output Directory | `dist` (por defecto) |

### Variable de entorno

| Variable | Valor |
|---|---|
| `VITE_API_URL` | La URL publica de la API en Railway, sin barra final |

Se lee en tiempo de **build**, no de ejecucion: si la cambias, hay que
redesplegar para que tome efecto.

### El rewrite no es opcional

`vercel.json` manda todas las rutas desconocidas a `index.html`. Sin eso, el
ruteo del lado del cliente funciona mientras navegas, pero entrar directo a
`/tabla` o recargar la pagina devuelve 404. Medido sobre el build real:

```txt
ruta            sin rewrite  con rewrite
/                       200          200
/parejas                404          200
/tabla                  404          200
/resultados             404          200
/admin                  404          200
```

### Redespliegue automatico

Vercel redespliega con cada push a `main`. Como el repositorio tambien tiene el
backend, conviene evitar builds que no cambian nada.

Settings -> Git -> *Ignored Build Step*:

```bash
git diff --quiet HEAD^ HEAD -- ./
```

Corre parado en el *Root Directory*, que es `frontend/`. Si el commit no toco
nada de esta carpeta, termina con codigo 0 y Vercel cancela el build.

### Despues del primer deploy

Vercel te da un dominio. Hay que volver a Railway y ajustar tres variables,
o la sesion del panel no va a funcionar:

```txt
CORS_ORIGINS=https://tu-dominio.vercel.app
COOKIE_SAMESITE=none
COOKIE_SECURE=true
```

Vercel y Railway son sitios distintos, asi que la cookie de sesion viaja
cross-site. Con `lax` el navegador la descarta en silencio: el login responde
200 y todo lo que sigue responde 401.

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
