# 02 — Reglas de negocio

## Parejas

Una pareja no tiene nombre propio ni alias en el MVP.

Una pareja se compone de:

- Jugador 1.
- Jugador 2.
- Foto de pareja.
- Zona.
- Estado en la liga.

Para mostrar una pareja en pantalla, el nombre visible se arma combinando ambos jugadores:

```txt
Jugador 1 / Jugador 2
```

Ejemplo:

```txt
Gómez / Pérez
```

### Qué se puede editar

- Se pueden corregir los nombres de jugador 1 y jugador 2.
- Se puede reemplazar la foto.
- **La zona no se puede modificar nunca.**

La zona se asigna al crear la pareja y queda fija para toda la liga. Cambiarla invalidaría el historial: los partidos ya jugados quedarían atribuidos a una zona a la que la pareja ya no pertenece, y la tabla de posiciones dejaría de tener sentido.

### Bajas de la liga

Las parejas no se eliminan del sistema. Están las 20 desde el inicio y las 20 quedan hasta el final.

Si una pareja abandona la liga, se marca con estado `withdrawn` (dada de baja). Esto no borra nada:

- Sus partidos ya jugados siguen contando para sus rivales.
- Sigue apareciendo en la tabla de posiciones.
- Sus partidos pendientes ya no se van a jugar.

En el MVP, marcar una pareja como dada de baja es **solo informativo**: el sistema lo muestra, no ajusta puntos.

La regla de compensación para las parejas que quedaron sin jugar contra ella se define en la sección [Compensación por baja](#compensación-por-baja).

## Zonas

El torneo tiene dos zonas:

- Zona A.
- Zona B.

Cada zona tiene 10 parejas.

En cada zona, las parejas juegan todos contra todos.

Las zonas son fijas y no se gestionan desde el sistema. Se crean por seed y sirven para agrupar parejas, separar tablas en la web pública y filtrar parejas al crear un partido.

## Partidos

Los partidos se crean individualmente.

No pertenecen a una jornada o fecha del torneo.

Cada partido tiene:

- Pareja A.
- Pareja B.
- Fecha fija.
- Estado.
- Sets cargados cuando ya fue jugado.

### La zona del partido es un dato derivado

Un partido **no guarda zona propia**. La zona del partido es la zona de sus parejas.

Al crear un partido se valida que ambas parejas pertenezcan a la misma zona. Cumplida esa validación, la zona del partido queda determinada y no hace falta almacenarla.

En el panel administrativo, la zona sí aparece al crear un partido, pero como **filtro de selección**: el administrador elige una zona para que el selector de parejas muestre solo las 10 de esa zona. Es una ayuda de interfaz, no un campo del partido.

### Estados

```txt
pendiente
jugado
```

Un partido pendiente todavía no tiene resultado.

Un partido jugado tiene sets cargados y ganador calculado automáticamente.

## Carga de resultados

El administrador carga los games de cada set.

Ejemplo:

```txt
Set 1: 6-3
Set 2: 4-6
Set 3: 7-6
```

El sistema calcula el ganador de cada set comparando los games:

```txt
Si games Pareja A > games Pareja B, gana el set Pareja A.
Si games Pareja B > games Pareja A, gana el set Pareja B.
```

El sistema calcula el ganador del partido contando sets ganados.

No se carga ganador manualmente.

## Corrección de resultados

Cargar un resultado mal es algo que va a pasar. El sistema tiene que permitir arreglarlo.

El administrador puede:

- **Corregir** el resultado de un partido jugado, reemplazando los sets cargados por los correctos.
- **Deshacer** el resultado, dejando el partido nuevamente en estado pendiente.

Una corrección reemplaza los sets completos, no los edita de a uno. Se borran los sets anteriores y se cargan los nuevos.

La tabla de posiciones no requiere ninguna acción adicional: como se calcula al vuelo desde los partidos jugados, queda correcta en la consulta siguiente.

## Formato de partido

Los partidos son al mejor de 3 sets.

Si el tercer set se juega como super tie-break, el administrador lo carga como `7-6`.

El sistema no distingue entre set normal y super tie-break.

### Consecuencia asumida

Anotar el super tie-break como `7-6` distorsiona levemente la diferencia de games, que es el tercer criterio de ordenamiento. Un super tie-break real de 10-8 entra a la tabla como 7-6.

Es una simplificación aceptada a conciencia para el MVP: evita modelar un tipo de set especial a cambio de un ruido mínimo en un criterio de desempate que casi nunca se llega a usar.

## Puntuación

### Victoria 2-0

```txt
Ganador: 3 puntos
Perdedor: 0 puntos
```

### Victoria 2-1

```txt
Ganador: 2 puntos
Perdedor: 1 punto
```

## Tabla de posiciones

La tabla se calcula automáticamente desde los partidos jugados.

El administrador no edita la tabla manualmente.

### Métricas calculadas

- Partidos jugados.
- Partidos ganados.
- Partidos perdidos.
- Sets a favor.
- Sets en contra.
- Diferencia de sets.
- Games a favor.
- Games en contra.
- Diferencia de games.
- Puntos.
- Promedio de puntos por partido.

### Promedio de puntos por partido

```txt
promedio = puntos / partidos jugados
```

Si la pareja no jugó ningún partido, el promedio es `0`.

Es una métrica **solo administrativa**. Sirve para dos cosas:

1. Comparar el rendimiento real de parejas que jugaron distinta cantidad de partidos.
2. Ser la base de la compensación por baja al cierre de la liga.

No se muestra en la tabla pública.

### Tabla pública

La tabla pública muestra solo:

- Posición.
- Pareja.
- Partidos jugados.
- Partidos ganados.
- Partidos perdidos.
- Diferencia de sets.
- Puntos.

### Tabla administrativa

La tabla administrativa muestra todas las métricas calculadas, incluido el promedio de puntos y el estado de la pareja (activa o dada de baja).

## Criterios de ordenamiento y desempate

El orden de la tabla se resuelve en dos etapas.

### Etapa 1 — Ordenamiento principal

Se ordena de forma descendente por, en este orden:

1. Puntos.
2. Diferencia de sets.
3. Diferencia de games.

En la práctica esta etapa resuelve casi todos los casos. La diferencia de games es un valor de grano fino: que dos parejas coincidan en los tres criterios es poco frecuente, y que coincidan tres o más es excepcional.

### Etapa 2 — Desempate

Si dos o más parejas quedan con puntos, diferencia de sets y diferencia de games **idénticos**, forman un grupo empatado.

Cada grupo se resuelve aplicando esta cascada en orden. Se corta en el primer criterio que separe a las parejas:

**1. Enfrentamiento directo.**

Aplica únicamente si el grupo es de exactamente 2 parejas **y ya jugaron el partido entre ellas**. Queda arriba la que lo ganó.

Si el grupo tiene más de 2 parejas, o si son 2 que todavía no se enfrentaron, este criterio **no aplica** y se pasa al siguiente.

La condición de "ya jugaron" es indispensable, no un detalle. A mitad de liga, dos parejas empatadas pueden tener su partido todavía pendiente. Sin esta condición el criterio no tendría con qué decidir.

**2. Mayor cantidad total de sets ganados.**

**3. Id de pareja ascendente.**

Este último criterio no es deportivo y no pretende serlo. Existe por una razón técnica concreta: **si no se define un criterio final, el orden de las parejas empatadas lo decide el motor de base de datos, y puede cambiar entre una consulta y otra.** La tabla pública mostraría un orden distinto en cada recarga de página.

Un criterio arbitrario pero estable garantiza que la tabla sea siempre la misma. Si alguna vez se llega a este caso, la definición deportiva la toma la organización fuera del sistema.

### El ordenamiento es una función pura

El cálculo de la tabla recibe las parejas de una zona y sus partidos jugados, y devuelve la lista ordenada. No consulta la base de datos ni depende del framework web.

Esto es intencional: es la lógica más delicada del sistema y así se puede testear con datos armados a mano, sin levantar nada.

## Compensación por baja

Regla de cierre de liga, **fuera del alcance del MVP**.

Si una pareja se da de baja habiendo jugado solo una parte de sus partidos, las parejas que nunca llegaron a enfrentarla quedan en desventaja: jugaron menos partidos y por lo tanto sumaron menos puntos posibles.

Al finalizar la liga, esas parejas reciben una compensación calculada a partir de **su propio promedio de puntos por partido**.

La idea es proyectar el rendimiento real de cada pareja sobre el partido que nunca pudo jugar: se le otorga lo que su nivel indica que habría sumado. Así el partido faltante no altera el orden relativo de la tabla.

### Fórmula

Para cada pareja activa que quedó sin jugar contra una pareja dada de baja:

```txt
compensación = promedio de puntos de la pareja beneficiada
             × cantidad de partidos no jugados contra parejas dadas de baja

puntos finales = puntos reales + compensación
```

### Condiciones

- Se aplica **una sola vez, al cierre de la liga**. Nunca durante la fase regular.
- La pareja dada de baja **no recibe compensación**: conserva únicamente los puntos que ganó en cancha.
- Si una pareja beneficiada no jugó ningún partido, su promedio es `0` y su compensación es `0`.
- Si se dan de baja varias parejas, la compensación se multiplica por la cantidad de partidos faltantes.

### El promedio se congela antes de compensar

El promedio de cada pareja se calcula **solo con partidos realmente jugados**, y se toma antes de aplicar ninguna compensación.

Esto no es un detalle de implementación: si el promedio se recalculara incluyendo puntos compensados, el cálculo se realimentaría a sí mismo y el resultado dependería del orden en que se procesan las parejas. Primero se congelan todos los promedios, después se compensa.

### Precisión

La compensación se conserva con 2 decimales y no se redondea a entero.

Redondear puede empujar a dos parejas a un empate artificial que en los números reales no existía, y obligaría a resolver por desempate algo que ya estaba definido.

### Alternativa descartada

Se evaluó usar como base el promedio de puntos que la pareja dada de baja **cedió a sus rivales**. Se descartó porque todas las parejas beneficiadas recibirían el mismo valor, sin distinguir su nivel: una pareja puntera y una del fondo de la tabla sumarían lo mismo por un partido que ninguna jugó.

## Historial de partidos

### Web pública

La web pública solo muestra partidos jugados.

Cada card de partido debe mostrar:

- Zona (derivada de las parejas).
- Fecha.
- Pareja A.
- Foto de Pareja A.
- Pareja B.
- Foto de Pareja B.
- Resultado por sets.
- Ganador.

### Panel administrativo

El panel administrativo muestra partidos separados en:

- Pendientes.
- Jugados.

## Sponsors

Un sponsor tiene:

- Nombre.
- Logo.
- URL opcional.
- Estado activo/inactivo.

## Playoffs

Todas las parejas clasifican a playoff.

La implementación de playoffs queda para una etapa posterior.

La idea definida para más adelante es:

### Ronda 1

Cruces entre zonas desde las posiciones 3 a 10:

```txt
3A vs 10B
4A vs 9B
5A vs 8B
6A vs 7B
7A vs 6B
8A vs 5B
9A vs 4B
10A vs 3B
```

### Ronda 2

Los 8 ganadores de la Ronda 1 se cruzan entre sí.

Quedan 4 ganadores.

### Ronda 3

Entran los clasificados directos:

```txt
1A, 2A, 1B, 2B
```

Se cruzan con los 4 ganadores de la Ronda 2.

Desde ahí siguen:

- Semifinal.
- Final.

## Decisiones pendientes

1. **Definición deportiva del empate perfecto.** El sistema resuelve el orden de forma determinística por id de pareja, y eso alcanza para que la tabla no tiemble. Si el caso llega a ocurrir de verdad, la organización define el criterio deportivo fuera del sistema.
2. **Formato de playoffs.** El cruce está definido a nivel conceptual; falta el modelo de datos y las reglas de avance.
