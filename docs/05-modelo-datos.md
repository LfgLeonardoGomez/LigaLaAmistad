# 05 — Modelo de datos inicial

## Zone

Representa una zona de la liga.

```txt
id
name
```

Ejemplos:

```txt
Zona A
Zona B
```

Notas:

- Son exactamente dos y se crean por seed.
- No se crean, editan ni eliminan desde la aplicación.

## Team

Representa una pareja.

```txt
id
zone_id
player_one_name
player_two_name
photo_url
status
created_at
updated_at
```

Estados:

```txt
active
withdrawn
```

Notas:

- No tiene nombre propio. El nombre visible se arma con los nombres de los jugadores.
- La foto es una sola por pareja.
- `zone_id` es **inmutable** después del alta.
- No se elimina nunca. Una pareja que abandona la liga pasa a `withdrawn` y conserva todo su historial.

### Por qué `status` y no un booleano `is_active`

Un `is_active` invita a usarse como "ocultar de la web", que es otra cosa. Acá el estado tiene consecuencia deportiva: una pareja `withdrawn` sigue en la tabla, sigue contando para sus rivales, y es la que dispara la regla de compensación al cierre de la liga.

Un valor con nombre explícito deja claro que es un estado de la liga, no una bandera de visibilidad.

## Match

Representa un partido entre dos parejas.

```txt
id
team_a_id
team_b_id
date
time
venue
status
photo_url
comment
created_at
updated_at
```

Estados:

```txt
pending
played
```

Lugares (`venue`):

```txt
boss_padel
cofam
arena
indoor
padelon
punto_de_oro
otro
```

El valor va en minúscula y la etiqueta visible la pone el front:

| Valor | Etiqueta |
|---|---|
| `boss_padel` | Boss Pádel |
| `cofam` | Cofam |
| `arena` | Arena |
| `indoor` | Indoor |
| `padelon` | Padelón |
| `punto_de_oro` | Punto de Oro |
| `otro` | Otro |

Notas:

- El partido tiene fecha fija.
- La hora es **opcional**: un partido se programa antes de que las parejas
  arreglen a qué hora juegan, y los partidos ya cargados no la tienen.
- El lugar es **opcional** y es una lista cerrada de clubes, no texto libre.
  Sin la lista cerrada, "Boss", "boss padel" y "Bos Padel" serían tres clubes
  distintos en la web.
- Ninguno de los dos se rellena hacia atrás: un partido sin hora ni lugar es un
  estado válido, no un dato faltante.
- No pertenece a una jornada del torneo.
- El ganador no se guarda: se calcula desde los sets.

### El partido no guarda zona

`Match` **no tiene** `zone_id`.

La zona de un partido es la zona de sus parejas. Al crear el partido se valida que `team_a.zone_id == team_b.zone_id`, y con esa validación cumplida la zona queda determinada.

Guardarla sería duplicar un dato ya conocido y abrir la puerta a que se desincronice.

Para filtrar partidos por zona se resuelve por la zona de las parejas. Con 90 partidos en toda la liga, el costo del join es irrelevante.

En el panel administrativo la zona sí aparece al crear un partido, pero como filtro del selector de parejas. Es interfaz, no dato persistido.

## MatchSet

Representa un set jugado dentro de un partido.

```txt
id
match_id
set_number
team_a_games
team_b_games
```

Ejemplo:

```txt
id: 1
match_id: 1
set_number: 1
team_a_games: 6
team_b_games: 3
```

El ganador del set se calcula comparando `team_a_games` y `team_b_games`.

Notas:

- Un partido tiene 2 o 3 sets, o ninguno si está pendiente.
- `set_number` es consecutivo desde 1.
- Al corregir un resultado se borran todos los sets del partido y se crean los nuevos.

## Sponsor

Representa un sponsor del torneo.

```txt
id
name
logo_url
url
is_active
created_at
updated_at
```

Acá `is_active` sí es una bandera de visibilidad: controla si el sponsor se muestra en la web pública. No tiene consecuencia de dominio.

## AdminUser

Representa un usuario administrador.

```txt
id
email
password_hash
is_active
created_at
updated_at
```

No hay roles en el MVP: todo administrador puede hacer lo mismo, incluido dar
de alta a otros administradores.

El primer registro se crea por seed. Los siguientes se crean desde el panel,
por un administrador ya logueado. No hay registro público.

`is_active` acá es una bandera de acceso: un administrador desactivado no puede
iniciar sesión, y si tenía una sesión abierta, se le corta en el siguiente
pedido. No se elimina nunca, para que el registro quede como rastro.

## Relaciones

```txt
Zone  1 ── N Team
Team  1 ── N Match como team_a
Team  1 ── N Match como team_b
Match 1 ── N MatchSet
```

`Zone` no tiene relación directa con `Match`. La zona de un partido se alcanza a través de sus parejas.

## Reglas derivadas del modelo

### Zona del partido

```txt
zona del partido = team_a.zone_id
invariante      = team_a.zone_id == team_b.zone_id
```

### Ganador de set

```txt
team_a_games > team_b_games => gana Team A
team_b_games > team_a_games => gana Team B
```

No se permiten empates en games dentro de un set.

### Ganador de partido

Se cuentan los sets ganados por cada pareja.

```txt
Si Team A gana 2 sets => gana Team A
Si Team B gana 2 sets => gana Team B
```

### Puntos

```txt
Resultado 2-0 => ganador 3 puntos, perdedor 0
Resultado 2-1 => ganador 2 puntos, perdedor 1
```

### Promedio de puntos

```txt
promedio = puntos / partidos jugados
partidos jugados == 0 => promedio = 0
```

Métrica solo administrativa.

## Qué no está en el modelo, a propósito

| Dato | Por qué no se guarda |
|---|---|
| Zona del partido | Se deriva de las parejas |
| Ganador del set | Se deriva de los games |
| Ganador del partido | Se deriva de los sets |
| Tabla de posiciones | Se calcula desde los partidos jugados |
| Puntos de una pareja | Se calculan al armar la tabla |

Todo dato derivable que se persiste es un dato que se puede desincronizar. Con el volumen de esta liga no hay ninguna razón de performance para hacerlo.

## Nota sobre playoffs

El modelo de playoffs se definirá más adelante.

Para no contaminar el MVP, la fase de zonas se modela primero de forma clara y simple.
