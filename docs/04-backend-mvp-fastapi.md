# 04 — Backend MVP con FastAPI

## Objetivo del backend

El backend debe ser una API simple para administrar la liga y exponer datos públicos al frontend.

No debe intentar resolver casos genéricos de múltiples torneos ni una arquitectura empresarial innecesaria.

## Stack propuesto

- FastAPI.
- PostgreSQL.
- SQLModel como ORM.
- JWT en cookie httpOnly para autenticación administrativa.
- Cloudinary para almacenamiento de imágenes.
- `uv` como gestor de dependencias y entorno.
- pytest para tests.
- Alembic para migraciones.

### Sobre SQLModel

SQLModel unifica SQLAlchemy y Pydantic. Se eligió por familiaridad previa del desarrollador, sabiendo que el argumento de "una sola clase para todo" no aplica del todo acá: las representaciones pública y administrativa son distintas.

La separación entre modelo y esquema **se mantiene**:

```txt
models.py   → clases con table=True   → tablas en PostgreSQL
schemas.py  → clases sin table=True   → solo forma del JSON
```

Ambas heredan de `SQLModel`. Cambia el parámetro, no el concepto.

**Regla obligatoria:** las clases con `table=True` nunca se devuelven como respuesta de la API.

En una clase de tabla el id se declara `id: int | None = None`, porque antes del INSERT no existe. Exponer esa clase haría que el contrato público declare un `id` nullable que en la práctica nunca es nulo, obligando al frontend a chequear un caso imposible.

Las clases de respuesta viven en `schemas.py`, sin `table=True` y con `id: int` no opcional.

## Principios de diseño

- Una API monolítica modular.
- Separar rutas públicas de rutas administrativas.
- Mantener reglas de negocio en servicios reutilizables.
- No duplicar la tabla de posiciones en base de datos al inicio; calcularla desde partidos jugados.
- No permitir carga manual de ganador: se calcula desde los sets.
- No almacenar datos derivables. La zona de un partido y el ganador de un set son ejemplos de esto.

## Estructura tentativa

```txt
app/
  main.py
  seed.py
  core/
    config.py
    security.py
    cloudinary.py
  database/
    session.py
  auth/
    router.py
    models.py
    schemas.py
    service.py
  zones/
    models.py
    schemas.py
  teams/
    router.py
    models.py
    schemas.py
    service.py
  matches/
    router.py
    models.py
    schemas.py
    service.py
  standings/
    router.py
    schemas.py
    service.py
  sponsors/
    router.py
    models.py
    schemas.py
    service.py
```

`zones/` no tiene `router.py` ni `service.py`: las zonas son datos de seed, no una entidad gestionable. Solo existen su modelo y su esquema de salida, porque otras respuestas las referencian.

## Rutas públicas

```txt
GET /public/zones
GET /public/teams
GET /public/matches
GET /public/standings
GET /public/sponsors
```

### GET /public/teams

Acepta filtro opcional `zone_id`.

### GET /public/matches

Acepta `status`. Sin ese parámetro devuelve los jugados, que es lo que un
visitante entiende por "los resultados", y con `status=pending` devuelve los
programados, que es lo que usa el inicio para anunciar quién juega.

Esto reemplaza la regla original de que la web pública nunca mostraba
pendientes: saber quién juega es tan público como saber quién ganó.

Acepta filtro opcional `zone_id`. Como el partido no guarda zona, el filtro se resuelve por la zona de sus parejas.

### GET /public/standings

Debe devolver tabla simplificada por zona.

## Rutas administrativas

```txt
POST /auth/login
POST /auth/logout
GET  /auth/me
```

No hay registro público. El administrador inicial se crea con `seed.py`; a
partir de ahí, un administrador logueado puede dar de alta a los demás.

```txt
POST   /admin/users
GET    /admin/users
PATCH  /admin/users/{admin_id}
```

`PATCH` sirve para dos cosas: resetear la contraseña de un administrador y
darlo de baja con `is_active: false`. No se acepta cambiar el email.

No existe `DELETE /admin/users/{admin_id}`. Un administrador que ya no debe
entrar se desactiva; así el registro queda para auditoría.

Un administrador **no puede desactivarse a sí mismo**: la API responde `400`.
Sin esa regla, el único administrador activo podría dejar el sistema sin
acceso y sin forma de recuperarlo desde la aplicación.

La contraseña tiene un mínimo de 8 caracteres y nunca vuelve en una respuesta.

```txt
POST   /admin/teams
GET    /admin/teams
PATCH  /admin/teams/{team_id}
```

No existe `DELETE /admin/teams/{team_id}`. Las parejas no se eliminan.

Para dar de baja una pareja se usa `PATCH` cambiando su estado a `withdrawn`.

`PATCH /admin/teams/{team_id}` acepta solo `player_one_name`, `player_two_name`, `photo` y `status`. Si el cuerpo incluye `zone_id`, la API responde `400`.

```txt
POST   /admin/matches
GET    /admin/matches?status=pending
GET    /admin/matches?status=played
PATCH  /admin/matches/{match_id}
DELETE /admin/matches/{match_id}
```

`PATCH /admin/matches/{match_id}` sirve para corregir la fecha, la hora, el lugar o las parejas de un partido pendiente. Es también la forma de cargar hora y lugar cuando las parejas los arreglan después del alta. Un campo ausente no se toca; un `null` explícito borra la hora o el lugar ya cargados.

`DELETE /admin/matches/{match_id}` elimina un partido creado por error. Si el partido ya tiene resultado, primero hay que deshacerlo.

### Orden de los partidos

Los listados de partidos, público y administrativo, salen por `date`, después
por `time` y finalmente por `id`.

La hora es nullable, así que el orden de los nulos se declara explícitamente
(`NULLS LAST`) en vez de dejarlo al motor: PostgreSQL los pone al final en
`ASC` y SQLite los pone al principio, y los tests corren sobre SQLite mientras
producción corre sobre PostgreSQL. Sin declararlo, la suite validaría un orden
que producción no reproduce.

Los partidos sin hora quedan al final de su día: una hora sin acordar puede
caer en cualquier momento, así que no se la puede intercalar con las que ya
están fijas.

### Resultados

```txt
POST   /admin/matches/{match_id}/result
PUT    /admin/matches/{match_id}/result
DELETE /admin/matches/{match_id}/result
```

- `POST` carga el resultado de un partido pendiente. El partido pasa a `played`.
- `PUT` reemplaza el resultado de un partido ya jugado. Borra los sets anteriores y carga los nuevos. El partido sigue en `played`.
- `DELETE` borra los sets cargados. El partido vuelve a `pending`.

Los tres verbos aplican las mismas validaciones de sets.

**Nota de diseño:** ninguna de estas tres operaciones necesita recalcular ni invalidar nada. Como la tabla de posiciones no está materializada, se recalcula sola en la siguiente consulta. Esta es la principal ventaja de no persistir standings, y es la razón por la que corregir resultados es barato.

```txt
POST   /admin/sponsors
GET    /admin/sponsors
PATCH  /admin/sponsors/{sponsor_id}
DELETE /admin/sponsors/{sponsor_id}
```

## Servicio de tabla de posiciones

Es la lógica más delicada del sistema. `service.py` se parte en **dos funciones con responsabilidades distintas**.

```txt
standings/service.py

  get_standings(session, zone_id)      → acceso a datos
  calculate_standings(teams, matches)  → cálculo puro
```

El router llama a `get_standings`. Los tests atacan `calculate_standings`.

### `get_standings(session, zone_id)`

Trae de la base las parejas de la zona y sus partidos jugados con los sets, y delega el cálculo.

Es la única de las dos que conoce la base de datos. Mantiene el mismo patrón que el resto de los módulos: el acceso a datos vive en el service, no en el router.

No tiene lógica de negocio. Trae y delega.

### `calculate_standings(teams, matches)`

**Función pura.**

```txt
Entrada:
  - parejas de una zona
  - partidos jugados de esa zona, con sus sets

Salida:
  - lista ordenada de filas de tabla, con posición asignada
```

No accede a la base de datos, no depende de FastAPI, no lee configuración, no consulta la hora. Con los mismos datos de entrada devuelve siempre el mismo resultado.

Acá vive todo el conocimiento del torneo: puntuación, métricas, ordenamiento y desempate.

### Por qué se parten en dos

Porque cambian por razones distintas. `get_standings` cambia si cambia la persistencia; `calculate_standings` cambia si cambian las reglas del pádel. Mezclarlas significaría tocar la lógica del torneo cada vez que se toca una consulta.

Y sobre todo, por testeabilidad: una función que consulta la base obliga a levantar PostgreSQL para probar un desempate. Una función pura se prueba con datos armados a mano, en memoria, en milisegundos.

Si probar es caro, no se prueba. Por eso la separación no es cosmética.

### Qué necesita realmente `calculate_standings`

De cada partido usa únicamente:

```txt
team_a_id
team_b_id
sets: [(team_a_games, team_b_games), ...]
```

No usa la fecha, ni el estado, ni las fotos, ni la zona. Esa pobreza de requisitos es deliberada: cuanto menos necesita, más fácil es armarle un escenario de prueba.

### Pasos

1. Inicializar las métricas de cada pareja de la zona en cero.
2. Por cada partido jugado:
   - Sumar games a favor y en contra de cada pareja.
   - Determinar el ganador de cada set comparando games.
   - Sumar sets a favor y en contra.
   - Determinar el ganador del partido contando sets ganados.
   - Asignar puntos: 3-0 si fue 2-0, 2-1 si fue 2-1.
   - Sumar partido jugado, y ganado o perdido según corresponda.
3. Calcular derivados: diferencia de sets, diferencia de games y promedio de puntos.
4. Ordenar por puntos, diferencia de sets y diferencia de games, todos descendentes.
5. Aplicar desempate a los grupos que quedaron con esos tres valores idénticos.
6. Asignar posición.

### Desempate

Después del ordenamiento principal, se detectan grupos de parejas con puntos, diferencia de sets y diferencia de games idénticos. Cada grupo se resuelve con una cascada, cortando en el primer criterio que separe:

| Orden | Criterio | Condición de aplicación |
|---|---|---|
| 1 | Ganador del enfrentamiento directo | El grupo es de exactamente 2 parejas **y** el partido entre ellas ya está en `played` |
| 2 | Mayor cantidad total de sets ganados | Siempre |
| 3 | `id` de pareja ascendente | Siempre |

La condición del criterio 1 es obligatoria. Dos parejas pueden estar empatadas a mitad de liga con su partido todavía pendiente: sin la condición, el criterio no tiene resultado con el que decidir.

El criterio 3 garantiza que el orden sea determinístico. Sin él, el orden de las parejas empatadas queda librado al motor de base de datos y la tabla pública puede cambiar entre recargas.

### Casos de test mínimos

Todos apuntan a `calculate_standings` y se arman con objetos en memoria.

Una instancia de modelo no necesita base de datos para existir: `Team(...)` y `Match(...)` son objetos de Python hasta que se los agrega a una sesión. Los escenarios de prueba se construyen a mano, sin PostgreSQL, sin migraciones y sin servidor.

- Zona sin partidos jugados: todas en cero, orden estable.
- Victoria 2-0: 3 puntos y 0 puntos.
- Victoria 2-1: 2 puntos y 1 punto.
- Orden resuelto por puntos.
- Orden resuelto por diferencia de sets con puntos iguales.
- Orden resuelto por diferencia de games con puntos y sets iguales.
- Dos parejas empatadas en todo, **con** enfrentamiento directo jugado: decide el ganador de ese partido.
- Dos parejas empatadas en todo, **sin** enfrentamiento directo jugado: cae a sets ganados.
- Tres parejas empatadas en todo: cae a sets ganados sin intentar enfrentamiento directo.
- Empate perfecto: el orden es el mismo en dos ejecuciones consecutivas.
- Promedio de puntos con 0 partidos jugados: devuelve 0, no divide por cero.
- Pareja dada de baja: sigue apareciendo en la tabla con sus puntos reales.

## Validaciones importantes

### Crear partido

- Pareja A y Pareja B deben ser diferentes.
- Ambas parejas deben pertenecer a la misma zona.
- La fecha es obligatoria.
- La hora es opcional. Si viene, es una hora del día (`HH:MM`); la API la
  devuelve como `HH:MM:SS`.
- El lugar es opcional y tiene que ser uno de los valores de `MatchVenue`.
  Cualquier otro texto es `422`.
- El partido no recibe `zone_id`: la zona se deriva de las parejas.

### Editar pareja

- No se acepta modificar `zone_id`. La API responde `400` si viene en el cuerpo.
- No existe endpoint de eliminación.

### Cargar o corregir resultado

- El partido debe existir.
- `POST` requiere que el partido esté en `pending`.
- `PUT` y `DELETE` requieren que el partido esté en `played`.
- Deben cargarse 2 o 3 sets.
- Los números de set deben ser consecutivos desde 1.
- No puede haber games iguales dentro de un set.
- Una pareja debe ganar exactamente 2 sets.
- El ganador del partido se calcula automáticamente.

## Carga de imágenes

Flujo recomendado:

```txt
Frontend admin selecciona imagen
↓
Backend recibe archivo
↓
Backend sube archivo a Cloudinary
↓
Cloudinary devuelve URL
↓
Backend guarda URL en PostgreSQL
```

Se usa para:

- Fotos de parejas.
- Logos de sponsors.

## Seed inicial

`seed.py` crea los datos que el sistema da por existentes y no se gestionan desde la interfaz:

- Zona A y Zona B.
- El primer usuario administrador, con su contraseña ya hasheada.

Debe ser idempotente: correrlo dos veces no duplica nada.

## Autenticación

Para MVP:

- Login con email y contraseña.
- Password hasheada.
- Cookie httpOnly con token.
- Rutas admin protegidas.
- Sin roles.
- Sin registro público.

## Decisiones para evitar sobreingeniería

- No guardar standings materializadas al inicio.
- No guardar la zona del partido: se deriva de las parejas.
- No usar eventos ni colas.
- No usar microservicios.
- No crear sistema multi torneo.
- No agregar roles hasta que exista una necesidad real.
- No implementar playoffs en el primer slice.
- No implementar la compensación por baja en el primer slice.
