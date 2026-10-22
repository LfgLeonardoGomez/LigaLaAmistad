# Tabla, revisión y cierre de clasificados

## Purpose

Calcular posiciones con reglas de Americano, resolver solo empates relevantes y cerrar grupos de manera consistente antes de iniciar eliminatorias.

## ADDED Requirements

### Requirement: AQ-01 Puntuación exacta y orden deportivo limitado

El sistema MUST otorgar 1 punto por victoria, 0,5 a cada pareja por empate y 0 por derrota, usando exclusivamente resultados guardados. MUST ordenar por puntos descendentes y luego diferencia de games descendente, sin enfrentamiento directo, sets, ID ni otro desempate deportivo. MUST conservar empates iguales en ambos criterios como pendientes cuando afecten plazas/siembra. La tabla principal MUST mostrar posición, pareja, puntos y diferencia de games sin error de redondeo acumulado.

#### Scenario: Victoria y empate
- **GIVEN** P vence 5-3 a Q y luego empata 0-0 con R en rondas guardadas
- **WHEN** se calcula la tabla
- **THEN** P tiene 1,5 puntos y +2 de diferencia; Q tiene 0 y -2; R tiene 0,5 y 0; un partido con un campo vacío no aporta métricas.

#### Scenario: Solo dos criterios
- **GIVEN** P y Q tienen igual puntuación y diferencia, pero distinto ID o vencedor de enfrentamiento directo
- **WHEN** se muestra la clasificación
- **THEN** siguen empatados deportivamente; un orden visual estable no concede una posición de siembra ni clasificación.

#### Scenario: Corrección recalcula sin acumulación
- **GIVEN** una ronda guardada que dio una victoria a P
- **WHEN** se corrige íntegramente a empate antes del cierre
- **THEN** la nueva tabla refleja solo el resultado corregido y no suma puntos del resultado anterior.

### Requirement: AQ-02 Revisión al terminar grupos sin bloqueo anticipado

El sistema MUST abrir la revisión al completar todas las rondas y MUST mostrar posiciones/cupos de cada zona y empates relevantes antes de confirmar. Completar la última ronda MUST NOT bloquear grupos ni iniciar playoffs automáticamente. Los marcadores MUST seguir editables hasta la confirmación explícita.

#### Scenario: Última ronda guardada
- **WHEN** se guarda la última ronda pendiente
- **THEN** se presenta revisión de clasificados, no se crean nodos eliminatorios y sigue disponible corregir grupos.

#### Scenario: Intento de revisión definitiva con grupos incompletos
- **WHEN** se intenta confirmar con una ronda no guardada
- **THEN** la API rechaza el cierre e identifica que faltan resultados; no crea cuadro ni congela datos.

### Requirement: AQ-03 Resolución humana de empates relevantes entre dos o más parejas

El sistema MUST detectar bloques empatados que afecten entrada a clasificación o posición requerida por el cuadro. MUST permitir al administrador seleccionar las parejas reales de ese bloque para cada plaza afectada según el resultado de un sorteo humano. MUST impedir texto libre, parejas ajenas, duplicadas o una selección incompleta. MUST NOT sortear por software ni exigir ordenar no clasificadas o empates sin efecto en plazas/siembra.

#### Scenario: Tres empatadas para dos plazas
- **GIVEN** una zona con cupo 4, puestos 1 y 2 firmes y P/Q/R empatadas para puestos 3 a 5
- **WHEN** el administrador elige Q para plaza 3 y P para plaza 4
- **THEN** la revisión ubica Q y P en esas plazas, deja R afuera sin exigir ordenar más no clasificadas y permite continuar cuando no haya otros empates relevantes.

#### Scenario: Todas clasifican pero cambia el cruce
- **GIVEN** P y Q empatadas en puestos 1 y 2 que clasifican ambas
- **WHEN** esos puestos alimentan adversarios distintos del cuadro
- **THEN** se exige elegir P/Q para cada puesto antes de confirmar aunque no esté en juego su entrada.

#### Scenario: Empate irrelevante
- **GIVEN** cupo 4 y tres parejas empatadas en puestos 6 a 8
- **WHEN** se revisan clasificados
- **THEN** no se exige resolver ese empate ni se inventa un criterio deportivo para él.

#### Scenario: Resolución inválida o incompleta
- **WHEN** se repite una pareja en dos plazas, se elige una ajena al bloque o queda una plaza relevante sin seleccionar
- **THEN** la resolución se rechaza y confirmar permanece impedido.

### Requirement: AQ-04 Revisiones vigentes e invalidación de decisiones manuales

El sistema MUST asociar previsualización y resoluciones al estado guardado de grupos. Cualquier cambio efectivo en un resultado de grupos MUST invalidar las resoluciones manuales y previsualizaciones anteriores; antes de confirmar MUST recalcular desde resultados actuales y verificar la versión. Una pantalla obsoleta MUST recibir conflicto, no confirmar con una foto antigua.

#### Scenario: Corrección después del sorteo humano
- **GIVEN** una resolución guardada para P/Q/R empatadas
- **WHEN** se corrige una ronda y cambia el resultado
- **THEN** se invalida la resolución anterior, se muestra nueva clasificación y solo se vuelven a pedir las plazas que sigan empatadas y sean relevantes.

#### Scenario: Confirmación de una pestaña obsoleta
- **GIVEN** otra sesión guardó resultados o una nueva resolución
- **WHEN** una pestaña confirma con su revisión previa
- **THEN** recibe conflicto y debe cargar la revisión actual antes de confirmar.

### Requirement: AQ-05 Confirmación atómica y definitiva de grupos

El botón MUST denominarse `Confirmar clasificados e iniciar playoffs` y advertir que grupos y composición quedan de solo lectura sin reapertura en el MVP. Una única transacción MUST verificar integridad de resultados, cupos, empates y versiones, crear una instantánea de clasificados/siembra y todo el cuadro, bloquear grupos y pasar a playoffs. Cualquier fallo MUST revertir todo.

#### Scenario: Confirmación válida
- **GIVEN** todos los grupos guardados y todas las plazas relevantes resueltas sobre la revisión actual
- **WHEN** el administrador acepta la advertencia y confirma
- **THEN** se guardan instantánea y cuadro completos una sola vez, se inicia playoffs y grupos/tablas quedan consultables pero no editables.

#### Scenario: Error al crear el cuadro
- **WHEN** falla cualquier inserción durante la confirmación
- **THEN** no quedan instantáneas ni nodos parciales y los grupos permanecen en revisión editable.

#### Scenario: Reintento de confirmación
- **GIVEN** una confirmación exitosa cuya respuesta no llegó
- **WHEN** se reenvía la misma operación de confirmación
- **THEN** se devuelve el cierre canónico o un conflicto explícito recuperable, sin duplicar instantáneas ni cuadros; otra propuesta de cierre no reemplaza la primera.

#### Scenario: Carrera entre corrección y confirmación
- **WHEN** un administrador corrige grupos mientras otro confirma desde la misma versión
- **THEN** solo se acepta un orden consistente: la corrección gana e invalida el cierre viejo, o el cierre gana y la corrección se rechaza por bloqueo; nunca se crea un cuadro con resultados obsoletos.

### Requirement: AQ-06 Bloqueo impuesto por backend

Tras confirmar, el sistema MUST rechazar por API cualquier cambio a marcadores de grupos, composición, fixture o resoluciones y MUST mostrar resultados/tablas congelados también al recargar. El alcance inicial MUST NOT incluir una operación de reapertura.

#### Scenario: Edición directa tras confirmar
- **GIVEN** evento en playoffs o completado
- **WHEN** se intenta PUT de una ronda o cualquier modificación de grupos desde una pantalla vieja o cliente directo
- **THEN** responde conflicto de estado sin modificar resultados, instantáneas ni cuadro.
