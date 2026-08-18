# 03 — Historias de usuario

## Visitante público

### Ver home del torneo

Como visitante, quiero ver una página inicial atractiva del torneo para entender rápidamente qué es Liga La Amistad.

#### Criterios de aceptación

- Se muestra nombre/logo del torneo.
- Se muestra una presentación visual tipo hero.
- Se muestran accesos a parejas, tabla, resultados y sponsors.
- Se comunica el formato general de la liga.

### Ver parejas participantes

Como visitante, quiero ver las parejas participantes para conocer quiénes juegan la liga.

#### Criterios de aceptación

- Se listan las parejas de ambas zonas.
- Cada pareja muestra jugador 1, jugador 2 y foto.
- Se puede identificar a qué zona pertenece cada pareja.

### Ver tabla pública

Como visitante, quiero ver la tabla de posiciones para conocer cómo va cada zona.

#### Criterios de aceptación

- Se muestra una tabla por zona.
- La tabla se ordena automáticamente según las reglas del torneo.
- La tabla muestra posición, pareja, PJ, PG, PP, diferencia de sets y puntos.
- La tabla no muestra métricas administrativas más detalladas.
- El orden es estable: dos consultas seguidas sin partidos nuevos devuelven exactamente el mismo orden.

### Ver partidos jugados

Como visitante, quiero ver el historial de partidos jugados para consultar resultados anteriores.

#### Criterios de aceptación

- La página de resultados muestra solo partidos jugados.
- Cada partido muestra zona, fecha, parejas, fotos, resultado por sets y ganador.

### Ver los próximos partidos

Como visitante, quiero ver qué partidos están programados para saber quién
juega y cuándo.

#### Criterios de aceptación

- El inicio muestra los próximos partidos, del más cercano al más lejano.
- Cada uno muestra zona, fecha y las dos parejas.
- No muestra marcador ni permite abrirlo: todavía no hay nada que ver.
- Se aclara que la hora la arreglan las parejas, porque no se guarda.

### Ver sponsors

Como visitante, quiero ver los sponsors del torneo para conocer quiénes acompañan la liga.

#### Criterios de aceptación

- Se muestran sponsors activos.
- Cada sponsor muestra logo.
- Si tiene URL, se puede acceder al link.

## Administrador

### Iniciar sesión

Como administrador, quiero iniciar sesión para acceder al panel privado.

#### Criterios de aceptación

- El administrador puede ingresar con email y contraseña.
- Las rutas privadas requieren autenticación.
- No existen roles diferenciados.
- El primer administrador existe desde el seed inicial; no hay registro público ni alta desde la interfaz.

### Crear pareja

Como administrador, quiero crear una pareja para registrar participantes del torneo.

#### Criterios de aceptación

- Se cargan jugador 1, jugador 2, zona y foto.
- La foto se sube a Cloudinary.
- Se guarda la URL de la foto.
- La pareja se crea con estado activo.
- La pareja aparece en la web pública.

### Editar pareja

Como administrador, quiero editar una pareja para corregir datos o cambiar su foto.

#### Criterios de aceptación

- Se pueden modificar nombres de jugadores.
- Se puede reemplazar la foto.
- **No se puede modificar la zona.** El campo no se ofrece en el formulario de edición y la API rechaza el cambio.
- No existe eliminación de parejas.

### Dar de baja una pareja

Como administrador, quiero marcar una pareja como dada de baja cuando abandona la liga, para dejar constancia sin perder su historial.

#### Criterios de aceptación

- La pareja pasa a estado dado de baja.
- No se elimina ningún dato.
- Sus partidos jugados siguen contando en la tabla.
- La pareja sigue apareciendo en la tabla de posiciones.
- El estado se ve en la tabla administrativa.
- El MVP no ajusta puntos de nadie a partir de esta baja.

### Crear partido pendiente

Como administrador, quiero crear un partido para registrar que dos parejas tienen un encuentro organizado.

#### Criterios de aceptación

- Se selecciona una zona como filtro y el selector de parejas muestra solo las parejas de esa zona.
- Se selecciona Pareja A.
- Se selecciona Pareja B.
- Pareja A y Pareja B deben ser distintas.
- La API valida que ambas parejas pertenezcan a la misma zona, independientemente del filtro de la interfaz.
- Se carga una fecha fija.
- El partido queda en estado pendiente.
- El partido no almacena zona propia: su zona se deriva de las parejas.

### Ver partidos pendientes

Como administrador, quiero ver partidos pendientes para saber cuáles todavía no tienen resultado cargado.

#### Criterios de aceptación

- Se listan partidos pendientes separados de los jugados.
- Cada partido muestra zona, fecha y parejas.

### Cargar resultado

Como administrador, quiero cargar los sets de un partido jugado para que el sistema actualice la tabla.

#### Criterios de aceptación

- Se cargan 2 o 3 sets.
- Cada set tiene games de Pareja A y games de Pareja B.
- No se aceptan sets con games iguales.
- Una pareja debe ganar exactamente 2 sets.
- El sistema calcula ganador de cada set.
- El sistema calcula ganador del partido.
- El sistema asigna puntos según si el resultado fue 2-0 o 2-1.
- El partido pasa a estado jugado.
- La tabla se actualiza automáticamente.

### Corregir resultado cargado

Como administrador, quiero corregir el resultado de un partido ya jugado para arreglar una carga equivocada.

#### Criterios de aceptación

- Se pueden reemplazar los sets de un partido en estado jugado.
- El reemplazo sustituye el resultado completo, no edita sets individuales.
- Se aplican las mismas validaciones que en la carga original.
- El ganador se recalcula automáticamente.
- La tabla refleja la corrección en la siguiente consulta, sin ninguna acción extra.

### Deshacer resultado

Como administrador, quiero borrar el resultado de un partido para volver a dejarlo pendiente.

#### Criterios de aceptación

- Se eliminan los sets cargados.
- El partido vuelve a estado pendiente.
- El partido deja de aparecer en la web pública.
- La tabla deja de contabilizar ese partido.

### Ver partidos jugados en admin

Como administrador, quiero ver partidos jugados para revisar resultados cargados.

#### Criterios de aceptación

- Se listan partidos jugados separados de los pendientes.
- Cada partido muestra resultado por sets y ganador.
- Desde el listado se puede corregir o deshacer el resultado.

### Ver tabla administrativa

Como administrador, quiero ver la tabla completa para auditar posiciones y métricas.

#### Criterios de aceptación

- Se muestra una tabla por zona.
- Se muestran PJ, PG, PP, sets a favor, sets en contra, diferencia de sets, games a favor, games en contra, diferencia de games, puntos y promedio de puntos por partido.
- Se indica si una pareja está dada de baja.

### Crear sponsor

Como administrador, quiero crear sponsors para mostrarlos en la web pública.

#### Criterios de aceptación

- Se carga nombre.
- Se carga logo.
- El logo se sube a Cloudinary.
- Se puede cargar URL opcional.
- El sponsor aparece en la web pública si está activo.

### Editar sponsor

Como administrador, quiero editar sponsors para mantener actualizada la información.

#### Criterios de aceptación

- Se puede modificar nombre.
- Se puede modificar logo.
- Se puede modificar URL.
- Se puede activar o desactivar.
