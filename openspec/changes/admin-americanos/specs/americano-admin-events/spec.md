# Americanos administrativos y fixture

## Purpose

Administrar eventos privados independientes con parejas fijas y generar un fixture intrazona completo, jugable en hasta seis canchas simultáneas.

**Disponibilidad:** D3/D6/D8 aprobados; componentes[3.0.0](../../contracts.md), HTTP/DTO2.1.0 intacto. **31/31 tareas aceptadas; G3/G4 verificados** según[checklist](../../tasks.md). API/cliente18; flujo privado completo hasta campeón/corrección final con grupos cerrados, guard dirty/pending y recuperación sin autoPUT. Ensayo/carrera PostgreSQL completados solo en entorno descartable; aplicación activa y despliegue requieren aprobación separada. [Evidencia/historia](../../verification.md); requisitos inferiores intactos.

## ADDED Requirements

### Requirement: AE-01 Acceso administrativo en todas las operaciones

El sistema MUST exigir la sesión administrativa vigente para todas las lecturas y escrituras de Americanos y ubicar la sección dentro del panel existente. MUST NOT depender de ocultar navegación como control de acceso; MUST preservar el mecanismo de autenticación actual.

#### Scenario: Administrador accede desde el panel
- **GIVEN** una sesión administrativa activa
- **WHEN** abre la pestaña `Americanos` o una URL directa `/admin/americanos/...`
- **THEN** accede a la sección dentro del Layout y la sesión existentes.

#### Scenario: Acceso directo sin sesión válida
- **GIVEN** un visitante sin cookie, con sesión vencida o con administrador inactivo
- **WHEN** intenta cualquier GET, POST, PUT, PATCH o DELETE de `/admin/americanos`, incluidos tablas, revisión y playoffs
- **THEN** la API responde 401 sin datos ni mutaciones; la ruta frontend requiere autenticación.

### Requirement: AE-02 Aislamiento de eventos y de la liga pública

El sistema MUST conservar múltiples eventos independientes con IDs estables, parejas propias e historial consultable. MUST impedir referencias cruzadas entre eventos y MUST excluir Americanos de contratos, tablas y enlaces públicos de liga.

#### Scenario: Dos eventos simultáneos
- **GIVEN** eventos E1 y E2 con parejas de nombres iguales
- **WHEN** se guardan resultados de E1
- **THEN** las rondas, tablas, clasificados y playoffs de E2 y de la liga no cambian.

#### Scenario: Identificador de otro evento
- **GIVEN** una ronda, pareja o nodo perteneciente a E2
- **WHEN** se envía ese ID en una operación bajo E1
- **THEN** la operación se rechaza sin modificar ninguno de los eventos; un recurso anidado ajeno responde 404 y una referencia inválida en un payload responde 422.

#### Scenario: Consulta pública tras operar un Americano
- **WHEN** un visitante consulta parejas, zonas, fixture, resultados o tablas públicas y recorre la navegación pública
- **THEN** obtiene únicamente los datos de liga y ningún enlace ni dato de Americanos, aun cuando haya eventos completos.

### Requirement: AE-03 Borradores y parejas fijas de cantidad variable

El sistema MUST permitir crear un evento vacío, identificarlo por nombre y registrar una cantidad variable de parejas con los dos nombres de sus integrantes. Las parejas MUST permanecer fijas dentro del evento. La falta de participantes MUST impedir generar fixture, no crear el borrador. La gestión inicial MUST ofrecer listado simple con nombre, estado y acceso al historial, sin eliminar eventos con actividad.

#### Scenario: Borrador vacío
- **WHEN** el administrador crea un evento con nombre y sin parejas
- **THEN** el evento aparece como borrador con instrucciones para registrar parejas y generar queda deshabilitado.

#### Scenario: Carga individual o por lote
- **WHEN** el administrador registra una pareja o agrega varias filas completas y confirma el lote
- **THEN** la pareja individual sigue disponible y el lote guarda todas las parejas en una sola operación atómica, con una revisión y `registration_order` consecutivo desde1.

#### Scenario: Numeración después de eliminar
- **GIVEN** se eliminaron todas las parejas de un borrador
- **WHEN** se registra una nueva pareja
- **THEN** la interfaz la identifica como pareja #1, sin mostrar el ID de base de datos.

#### Scenario: Cantidades no predefinidas
- **WHEN** se registran 5, 8, 14 o 17 parejas en borradores separados
- **THEN** todas se conservan sin un cupo fijo de 8, 14 o 20; la generación depende de zonas y cupos elegidos.

#### Scenario: Configuración ya generada
- **GIVEN** un fixture generado, incluso sin resultados todavía
- **WHEN** se intenta agregar/eliminar parejas, alterar nombres del evento o integrantes, cambiar composición/zonas/etapa o regenerar fixture
- **THEN** la API rechaza el cambio y la UI explica el bloqueo.

La congelación de composición, nombres y configuración al generar está **aprobada**: no existe regeneración ni inscripción tardía en este cambio.

### Requirement: AE-04 Asignación de una o dos zonas

El sistema MUST permitir una zona con todas las parejas o dos zonas mediante asignación manual o aleatoria. En manual MUST seleccionar Zona A con botones de parejas y asignar a Zona B todas las no seleccionadas, mostrando contadores y previsualización. Las zonas manuales MUST poder ser desiguales si satisfacen sus cupos. El reparto aleatorio MUST ser equilibrado con diferencia de tamaño <=1, persistirse y mostrarse en borrador antes de generar. Generar MUST conservar ese reparto sin volver a sortear. El equilibrio aleatorio aprobado MUST NOT imponerse al reparto manual.

#### Scenario: Una zona
- **WHEN** se selecciona una zona
- **THEN** todas las parejas quedan en Zona A y no se muestran controles de Zona B.

#### Scenario: Selección manual desigual
- **GIVEN** 9 parejas y comienzo en semifinales
- **WHEN** el administrador selecciona 5 para A
- **THEN** la previsualización muestra A=5, B=4, identifica cada pareja y permite generar porque cada zona tiene al menos 2 clasificables.

#### Scenario: Reparto aleatorio visible
- **GIVEN** 15 parejas y dos zonas
- **WHEN** solicita reparto aleatorio en borrador
- **THEN** el reparto equilibrado produce tamaños 8 y 7, cada pareja aparece una vez, se persiste y se muestra antes de generar; al generar se conserva sin volver a sortear.

#### Scenario: Descartar reparto guardado
- **GIVEN** existe un reparto manual o aleatorio guardado en un borrador de dos zonas
- **WHEN** el administrador descarta el reparto
- **THEN** todas las parejas quedan sin zona asignada y la acción incrementa la revisión del evento.

#### Scenario: Pareja A deseleccionada en la propuesta
- **GIVEN** una pareja está guardada en A y el administrador la deselecciona sin guardar la propuesta
- **WHEN** se actualiza la vista previa
- **THEN** aparece como sin asignar, no como parte de B; al guardar la propuesta, las parejas no seleccionadas quedan asignadas a B.

### Requirement: AE-05 Cupos según etapa inicial

El sistema MUST admitir inicio en cuartos, semifinales o final con 8, 4 o 2 clasificados respectivamente. Con una zona MUST tomar todos los cupos de ella; con dos MUST tomar 4, 2 o 1 de cada zona. MUST validar cupos por zona antes de generar y rechazar configuraciones insuficientes sin agregar byes eliminatorios.

#### Scenario: Matriz de clasificación
- **WHEN** se elige cada combinación de etapa y cantidad de zonas
- **THEN** se muestran y validan los cupos: cuartos=8 o 4+4; semifinal=4 o 2+2; final=2 o 1+1.

#### Scenario: Suficiencia total pero no por zona
- **GIVEN** 8 parejas repartidas 3+5 con inicio en cuartos
- **WHEN** se intenta generar
- **THEN** se informa que A requiere 4 parejas y no se guarda ningún fixture parcial ni se crean pases libres.

#### Scenario: Zona con una pareja
- **GIVEN** dos zonas de una pareja cada una e inicio en final
- **WHEN** se genera el evento
- **THEN** cada zona satisface su cupo de 1, no se inventan partidos ni rondas vacías y se abre revisión de clasificados sin confirmar automáticamente.

### Requirement: AE-06 Todos contra todos intrazona completo

El sistema MUST generar exactamente un partido por combinación no ordenada de dos parejas de una zona, sin autorivales ni cruces entre zonas. MUST soportar cantidades pares, impares y desiguales, y guardar el fixture completo una sola vez.

#### Scenario: Ocho parejas en una zona
- **WHEN** se genera el fixture
- **THEN** existen 28 partidos distintos, cada pareja enfrenta a otras 7 una vez, distribuidos en 7 rondas globales de 4 partidos.

#### Scenario: Catorce parejas en dos zonas de siete
- **WHEN** se genera el fixture
- **THEN** existen 42 partidos distintos, 21 por zona, distribuidos en 7 rondas globales de 6 partidos; en cada ronda descansa una pareja de cada zona.

#### Scenario: Zonas impares y desiguales
- **GIVEN** A=5 y B=4
- **WHEN** se genera el fixture
- **THEN** existen 10+6=16 partidos, ninguna pareja juega contra sí misma o contra otra zona y la navegación sigue disponible cuando B ya no tiene cruces pendientes.

### Requirement: AE-07 Rondas globales jugables de hasta seis partidos

El sistema MUST limitar cada ronda real a seis partidos en total entre ambas zonas y una participación por pareja. MUST mostrar descansos de las parejas sin partido en esa ronda. Cuando un bloque lógico exceda seis partidos MUST distribuirlo en varias rondas reales; no se exige optimizar el número total de rondas ni gestionar tiempos.

#### Scenario: Un bloque lógico de ocho partidos
- **GIVEN** 16 parejas en una zona, con 8 cruces en una ronda Berger
- **WHEN** se transforma ese bloque en rondas jugables
- **THEN** se generan rondas de como máximo 6 y 2 partidos respectivamente, nunca ocho partidos simultáneos; las parejas que esperan aparecen como descanso/espera de esa ronda real.

#### Scenario: Capacidad compartida
- **GIVEN** dos zonas cuyo bloque combinado contiene más de 6 partidos
- **WHEN** se genera el fixture
- **THEN** cada ronda global respeta el máximo conjunto de 6, no un máximo de 6 por zona.

#### Scenario: Generación concurrente
- **GIVEN** dos solicitudes de generación del mismo borrador y revisión
- **WHEN** compiten por guardarlo
- **THEN** solo una crea el fixture; la otra informa conflicto o devuelve el ya creado sin duplicar partidos ni rondas.
