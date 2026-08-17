# 07 — Prompt para la web pública

Este documento es el prompt que se le pasa a una herramienta de diseño para
generar la web pública. Se versiona acá para que quede constancia de qué se
pidió, y para poder ajustarlo si el resultado no convence.

Todo lo que sigue, desde la línea divisoria, es el prompt.

---

## Contexto

Necesito la **web pública** de Liga La Amistad, una liga de pádel amateur de
barrio. La liga tiene **dos zonas** (Zona A y Zona B) con parejas que juegan
entre sí dentro de su zona.

El backend ya está construido, probado y funcionando. El repositorio es
`https://github.com/LfgLeonardoGomez/LigaLaAmistad`. **Leelo antes de escribir
nada**: ahí están el contrato real de la API, los modelos y el panel de
administración ya hecho, cuyo estilo de código hay que respetar.

Vos construís **solamente la parte pública**. El panel administrativo ya existe
y no se toca.

## Stack — no negociable

El proyecto ya está armado con esto y hay que integrarse, no empezar de cero:

- React 19 + TypeScript en modo estricto
- Vite
- Tailwind CSS v4 (se configura con `@tailwindcss/vite` y `@import 'tailwindcss'`,
  **no** con `tailwind.config.js`)
- react-router-dom v7
- Sin gestor de estado y sin librería de fetching. El proyecto usa un hook
  propio, `useResource`, y un wrapper de `fetch` en `src/api/client.ts`.
  **Reusalos, no traigas TanStack Query ni Redux.**
- Deploy en Vercel

No agregues dependencias sin justificarlo explícitamente. El criterio del
proyecto es mantener el código simple; ya se descartaron a propósito el patrón
Repository, Unit of Work y las librerías de fetching.

## Dónde vive

Va **en la misma aplicación de Vite** que el panel, no en un proyecto aparte.
Hoy `src/App.tsx` muestra el login cuando no hay sesión. Eso hay que
reestructurarlo:

- Las rutas públicas (`/`, `/parejas`, `/tabla`, `/resultados`) son accesibles
  **siempre**, con o sin sesión.
- El panel pasa a colgar de `/admin/*` y sigue detrás del login.
- El login pasa a `/admin/login`.

La web pública **no debe mostrar ningún acceso visible al panel**. El
administrador entra por URL directa.

## Contrato de la API — leelo con atención

Base URL configurable por `VITE_API_URL`. Los cinco endpoints públicos **no
requieren autenticación**.

```txt
GET /public/zones
GET /public/teams?zone_id=<opcional>
GET /public/matches?zone_id=<opcional>
GET /public/standings?zone_id=<obligatorio>
GET /public/sponsors
```

Formas de respuesta exactas:

```ts
Zone     { id, name }
Team     { id, zone_id, player_one_name, player_two_name, photo_url, status }
Match    { id, team_a_id, team_b_id, date, status,
           sets: [{ set_number, team_a_games, team_b_games }],
           winner_team_id }
Sponsor  { id, name, logo_url, url, is_active }
Standing { position, team_id, played, won, lost, points,
           sets_won, sets_lost, sets_diff,
           games_won, games_lost, games_diff, points_average }
```

### Tres cosas que te van a morder si no las tenés en cuenta

**1. La tabla y los partidos no traen nombres, solo `team_id`.**
`Standing` trae `team_id` y `Match` trae `team_a_id` / `team_b_id`. Para
mostrar "Ana / Bea" hay que traer `/public/teams` y cruzar por id en el
cliente. Armá un `Map<number, Team>` una sola vez y reusalo. Si no hacés esto,
la web muestra números.

**2. `zone_id` es obligatorio en standings.** No existe un endpoint que
devuelva las dos tablas juntas. Son dos llamadas, una por zona.

**3. Los partidos no traen su zona.** La zona de un partido se deriva de la
zona de sus parejas (ambas pertenecen siempre a la misma). Si querés mostrar u
ofrecer filtro por zona en resultados, resolvelo cruzando con `Team.zone_id`.

`/public/matches` ya devuelve **solo partidos jugados**. Los pendientes no
salen nunca en la web pública: no hay que filtrarlos, no llegan.

## Páginas y criterios de aceptación

### Home `/`

- Nombre y logo del torneo, con una presentación visual tipo *hero*.
- Se comunica el formato de la liga: dos zonas, partidos al mejor de tres sets,
  tabla que se actualiza con cada resultado.
- Accesos claros a parejas, tabla y resultados.
- Franja de sponsors.
- Si hay resultados recientes, mostrarlos como gancho.

### Parejas `/parejas`

- Se listan las parejas de **ambas** zonas, agrupadas o filtrables por zona.
- Cada pareja muestra jugador 1, jugador 2 y **una foto por pareja**, no una
  por jugador.
- `photo_url` puede venir en `null`: hace falta un placeholder digno, no una
  imagen rota.
- Se identifica claramente a qué zona pertenece cada pareja.

### Tabla `/tabla`

- Una tabla **por zona**, con selector o ambas visibles.
- Viene **ya ordenada** por la API. No la reordenes en el cliente: el orden
  incluye una cascada de desempate que el frontend no conoce.
- Columnas públicas: **posición, pareja, PJ, PG, PP, diferencia de sets y
  puntos**.
- **No** muestres las métricas administrativas: `games_won`, `games_lost`,
  `games_diff` ni `points_average` van en el panel, no acá.
- En pantallas chicas la tabla es lo más consultado del sitio. Que se lea bien
  en un teléfono es más importante que cualquier animación.

### Resultados `/resultados`

- Solo partidos jugados, ordenados del más reciente al más viejo.
- Cada partido muestra zona, fecha, las dos parejas con sus fotos, el resultado
  por sets y quién ganó.
- El ganador **viene calculado** en `winner_team_id`. No lo deduzcas vos.
- Filtro opcional por zona.

### Sponsors

- Puede ser una sección de la home o una página propia.
- Solo llegan los activos: `/public/sponsors` ya filtra.
- Cada sponsor muestra su logo. Si tiene `url`, es un enlace
  (`target="_blank"` con `rel="noopener noreferrer"`).

## Reglas del dominio que afectan la interfaz

- **Puntuación**: ganar 2-0 da 3 puntos, ganar 2-1 da 2 puntos, perder 1-2 da
  1 punto, perder 0-2 da 0. Si mostrás una leyenda del sistema de puntos, que
  diga exactamente esto.
- **Partidos al mejor de tres sets.** El tercer set puede ser un super
  tie-break, que se anota como 7-6. No hay que distinguirlos visualmente.
- **Una pareja puede estar dada de baja** (`status: "withdrawn"`) y **sigue
  apareciendo en la tabla con los puntos que realmente ganó**. No la escondas
  ni la muevas al final: marcala con discreción y dejala en su posición.
- **Las parejas no se eliminan nunca.** No existe el concepto de pareja
  borrada.
- El torneo tiene playoffs previstos, pero **no están implementados**. No
  inventes una sección de playoffs, llaves ni eliminatorias.

## Dirección de diseño

La referencia de inspiración es **La Velada del Año** de midudev: su energía,
su tipografía con presencia, la sensación de evento.

Pero adaptá, no copies. Son cosas distintas:

- La Velada es un evento único, masivo, de hype. Esto es una **liga de barrio
  que dura meses**, donde la gente entra a ver cómo salió su partido y cómo va
  en la tabla.
- Por eso: energía y personalidad, sí. Pero la **legibilidad de la tabla y de
  los resultados manda por encima de cualquier efecto**. Si una animación
  demora la lectura de un resultado, sacala.
- La mayoría va a entrar **desde el teléfono**, probablemente el mismo día que
  jugó. Diseñá mobile-first de verdad.

Lineamientos concretos:

- Paleta propia y con carácter. El panel administrativo usa grises fríos
  deliberadamente neutros; **la web pública no tiene por qué ser sobria**.
- Jerarquía tipográfica marcada. Los nombres de las parejas y los resultados
  son los protagonistas.
- Movimiento con criterio: transiciones sutiles, y respetar
  `prefers-reduced-motion`.
- Estados vacíos cuidados: al arrancar la liga no hay partidos jugados y la
  tabla está toda en cero. Ese es el **primer** estado que va a ver la gente,
  no un caso de borde.
- Estados de carga y de error explícitos. El backend puede estar caído.
- Accesibilidad real: contraste suficiente, foco visible, jerarquía correcta de
  encabezados, `alt` en las imágenes, tablas con `<th>` de verdad.

## Fuera de alcance

No construyas nada de esto:

- Panel administrativo, login o cualquier pantalla con sesión.
- Playoffs, llaves o eliminatorias.
- Perfil individual de jugador. La unidad del torneo es la **pareja**.
- Estadísticas o gráficos que la API no expone.
- Buscador, comentarios, notificaciones, modo oscuro con toggle, i18n.
- Cualquier endpoint nuevo. Trabajás con los cinco que existen.

## Qué espero recibir

- Código React + TypeScript que compile con `tsc --strict`, listo para pegar en
  el repo respetando su estructura (`src/pages/`, `src/components/`, `src/api/`).
- Los componentes públicos separados de los del panel.
- Comentarios solo donde expliquen un **porqué** que no se lee en el código.
- Una nota de qué decisiones de diseño tomaste y por qué, para poder discutirlas.

Si algo del contrato de la API te bloquea o te parece mal pensado, **decilo en
vez de inventar un endpoint**. El backend se puede cambiar; lo que no sirve es
un frontend que le pega a algo que no existe.
