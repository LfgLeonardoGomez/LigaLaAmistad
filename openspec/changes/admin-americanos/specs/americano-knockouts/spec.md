# Eliminatorias flexibles de Americano

## Purpose

Jugar un cuadro privado desde cuartos, semifinales o final con parejas clasificadas inmutables, resultado a set único y avance hasta campeón.

**Disponibilidad actualizada2026-10-22:** D6/D8 aprobados; [contrato2.1.0](../../contracts.md) intacto. **14/31 aceptadas,17 pendientes** según [checklist](../../tasks.md); nuevas4.2/4.3 backend FULL PASS PostgreSQL y5.2/6.4 por auditorías dedicadas.1.x/8.x siguen puras, sin campeón persistido8.3 ni API playoffs. API13, setup10/round4 con `loadEvent` compartido; cinco APIs futuras de clasificación/confirmación/playoffs. Consulta real protegida montada; UI editable deshabilitada hasta aprobar5.3.5.1 PARTIAL;2.x/5.3/6.1–6.3/9.x/G2/G3/G4 pendientes. Próximo proponer5.3 con confirmación humana previa; seis plantillas approved/futuras proposed preservadas. [Evidencia e historia](../../verification.md); solo disponibilidad, requisitos inferiores intactos.

## ADDED Requirements

### Requirement: AK-01 Cuadro según etapa inicial y siembra explícita

El sistema MUST crear exclusivamente las etapas requeridas por 8/4/2 clasificados, con 7/3/1 partidos respectivamente, sin byes automáticos ni plantilla fija de liga. Con dos zonas, semifinales directas MUST cruzar A1-B2 y B1-A2; con una MUST cruzar 1-4 y 2-3. La previsualización MUST mostrar todos los cruces y sus siguientes destinos antes de confirmar.

**Siembra aprobada:** cuartos, semifinales y finales MUST usar la tabla siguiente. Q1/Q2 alimentan S1 lados a/b; Q3/Q4 alimentan S2 lados a/b; S1/S2 alimentan la final lados a/b. Las seis plantillas actuales MUST tener status approved; el enum puede conservar proposed para futuras plantillas aún no aprobadas.

| Inicio | Una zona | Dos zonas |
|---|---|---|
| Cuartos | Q1:1-8; Q2:4-5; Q3:2-7; Q4:3-6 | Q1:A1-B4; Q2:B2-A3; Q3:B1-A4; Q4:A2-B3 |
| Semifinal | S1:1-4; S2:2-3 | S1:A1-B2; S2:B1-A2 |
| Final | 1-2 | A1-B1 |

#### Scenario: Cuartos de dos zonas según siembra aprobada
- **GIVEN** ocho clasificados confirmados y la política de siembra aprobada
- **WHEN** se construye el cuadro
- **THEN** hay cuatro cuartos entre zonas, A1/B1 en mitades opuestas y los dos primeros de cada zona separados hasta una posible final, con los destinos indicados en la tabla.

#### Scenario: Inicio directo en semifinal o final
- **WHEN** se confirma un evento configurado en semifinal o final
- **THEN** se crean solo 3 o 1 partidos respectivamente, aplicando los cruces de su columna sin rondas preliminares ficticias.

### Requirement: AK-02 Resultado a un set completo distinto de grupos

Las eliminatorias MUST cargar games de un único set completo, con dos valores enteros no negativos y ganador único. MUST rechazar blanco, empate, decimales y payload de mejor de tres; MUST NOT aplicar puntos 1/0,5/0 ni limitarse al dígito 0-9 de grupos. La UI MUST describir `Set completo` y derivar el ganador de los games, nunca permitir elegir un vencedor contradictorio.

La convención **aprobada** es set tradicional con tie-break: la API MUST aceptar únicamente 6-0, 6-1, 6-2, 6-3, 6-4, 7-5, 7-6 y sus simétricos como terminales, además de exigir `set_complete=true`. MUST rechazar 5-3, 6-5, empates y cualquier otro terminal. MUST NOT implementar la alternativa de set largo por ventaja ni un selector de reglamentos. Valores completos y desiguales o la declaración del organizador no sustituyen la validación terminal. No se traslada el super tie-break ni los dos sets ganadores de liga.

#### Scenario: Registrar un set completo informado
- **GIVEN** ambos participantes conocidos y un set 6-4 declarado completo según la convención aprobada
- **WHEN** se guarda el resultado
- **THEN** se registra un solo marcador, gana quien tiene 6 y no se pide un segundo set ni se alteran puntos de grupos.

#### Scenario: Resultado incompleto o empatado
- **WHEN** se intenta guardar un campo vacío, 6-6, un decimal o un set todavía en curso declarado como tal
- **THEN** no se guarda ni avanza ningún participante.

#### Scenario: Resultado imposible bajo la convención aprobada
- **GIVEN** la convención tradicional con tie-break aprobada
- **WHEN** se informa 5-3, 6-5, 8-6 u otro marcador fuera de los terminales permitidos, incluso con `set_complete=true`
- **THEN** la API lo rechaza y explica la regla; no usa las reglas de la liga como sustituto.

### Requirement: AK-03 Avance automático atómico hasta campeón

El sistema MUST avanzar al ganador al destino fijado en el cuadro en la misma transacción que guarda el resultado y MUST habilitar un partido solo con ambos participantes conocidos. MUST declarar campeón y completar el evento al guardar la final. Los resultados de grupos y la siembra MUST permanecer inmutables.

#### Scenario: Avance de semifinal
- **WHEN** se guarda válidamente la primera semifinal
- **THEN** su ganador ocupa el lado correspondiente de la final, que no acepta resultado hasta conocer también el otro lado.

#### Scenario: Final y recuperación
- **WHEN** se guarda la final y se recarga el evento
- **THEN** se muestra el mismo campeón y estado completado junto con cuadro y grupos consultables.

#### Scenario: Fallo o conflicto al avanzar
- **WHEN** falla la propagación o llega una escritura con revisión antigua
- **THEN** no queda resultado sin avance ni avance sin resultado; se revierte o informa conflicto sin sobreescritura.

### Requirement: AK-04 Corrección conservadora sin destruir descendientes

**Política aprobada:** el sistema MUST permitir corregir un resultado eliminatorio solo si ningún descendiente tiene resultado; si cualquiera lo tiene MUST rechazar toda corrección, incluso con el mismo ganador, sin borrar datos. Si cambia ganador y los descendientes están pendientes MUST actualizar únicamente su lado del siguiente partido en la misma transacción, conservando el otro lado. La final MUST poder corregirse también tras completar el evento, actualizando resultado y campeón atómicamente y conservando completed y grupos cerrados. MUST NOT borrar automáticamente descendientes, eliminar resultados, regenerar cuadro ni reabrir grupos.

#### Scenario: Corregir antes de jugar la siguiente etapa
- **GIVEN** semifinal guardada y final sin resultado
- **WHEN** se corrige la semifinal cambiando ganador
- **THEN** se reemplaza el marcador y el finalista en una sola transacción, manteniendo el otro finalista.

#### Scenario: Corrección de antecesor con descendiente jugado
- **GIVEN** semifinal y final con resultado
- **WHEN** se intenta corregir la semifinal, incluso conservando el mismo ganador
- **THEN** se rechaza sin destruir la final, campeón ni resultado previo.

#### Scenario: Corrección de final
- **GIVEN** evento completado y final sin descendientes
- **WHEN** se corrige válidamente su resultado bajo la política aprobada
- **THEN** el campeón se actualiza atómicamente, el evento sigue completado y grupos/siembra no cambian.
