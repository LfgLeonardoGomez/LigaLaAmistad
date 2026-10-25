# Contrato compartido de Americanos v3 (G0 histórico preservado)

**Versión de componentes:3.0.0. Integrador:I. HTTP/DTO:2.2.0 (delta aditivo).** **31/31 tareas originales aceptadas; G3/G4 verificados.** Ensayos PostgreSQL solo descartables; no implica migración activa, despliegue ni archive. [Evidencia actual e historia](verification.md).

### Estado de implementación del slice — 2026-10-23

API/cliente **20 operaciones privadas reales**; puertos setup12/draft7,round4,qualification4 yplayoffs3 comparten `loadEvent`, no son conteos sumables. El delta aditivo2.2 agrega alta atómica por lote, limpieza de asignaciones de zona y numeración contigua visible de parejas; las capacidades de alta individual siguen disponibles. Flujo privado de draft a campeón y corrección final, confirmación irreversible/UUID recuperable, grupos congelados y editor Set completo. Sin autoPUT ni avance optimista. Login/cookies/permisos intactos. Ensayos2.3/7.3 verificados solo en PostgreSQL descartable autorizado; aplicación activa/despliegue siguen separados. G3/G4 del cambio cerrado originalmente.

### Delta3.0.0 — componentes, sin delta HTTP

`AmericanoPlayoffsPageProps` pasa de puerto readonly2 a `AmericanoPlayoffsOperations` (`loadEvent/loadPlayoffs/saveKnockout`) y requiere `onDirtyChange(draft:DirtyNavigationDraft|null):void`. Es incompatible para consumidores de la entrega readonly: declarar versión mayor, no ocultarlo como disponibilidad HTTP. Tipo, único consumidor productivo (`AmericanoStageRoute`) y productor actualizados coordinadamente; descriptor usa callbacks estables/getters vivos y se republica por estado. `AmericanoPlayoffsReadOperations` permanece exportado para consultas, pero no satisface props del editor. Fixtures solo DTO no producen props/descriptores y siguen válidos sin cambios. Typecheck y QA del consumidor real verifican el nuevo contrato. Resto de props/DTO y18 rutas conservados.

### Registro histórico de aprobación humana — 2026-10-21 / delta 2.1.0

Fuente: respuesta del usuario **«confirma todas ls decisiones que tenes ahi.»** a la consulta detallada. Confirma las recomendaciones D3/D6/D8 y el slice técnico, no sus alternativas. Esta nota registra una aprobación posterior a G0 y a las correcciones de v2.0.0; no reescribe su evidencia histórica.

- **D3 aprobado:** aleatorio equilibrado con diferencia <=1; manual desigual permitido. Persistir y mostrar reparto antes de generar, sin resorteo al generar. Congelar composición, nombres y configuración desde generación, sin regeneración.
- **D6 aprobado:** las seis plantillas actuales tienen `status='approved'`; cruces y destinos exactos en §1. No cambia el enum `approved|proposed`, que conserva `proposed` para futuras plantillas no aprobadas.
- **D8 aprobado:** terminales 6-0..6-4, 7-5, 7-6 y simétricos; sin set largo por ventaja. Corregir solo sin ningún descendiente jugado, incluso si no cambia ganador; reemplazar únicamente su lado del siguiente partido pendiente si cambia ganador. Final corregible tras completed con campeón atómico, grupos cerrados, sin borrar ni reabrir.
- **Slice autorizado:** las primeras siete operaciones de §2.1 (listado/creación, lectura/edición de evento, alta/edición/baja de inscripción), cliente HTTP tipado, wiring de listado/setup y rutas/menú admin. Reutilizar `get_current_admin` sin cambios, proteger todos los métodos, mutar solo en draft con revisión e identidad por evento/404, sin mutaciones de liga.
- **Capacidades aún no implementadas en este slice:** asignación manual de zonas, random, generación, rondas, clasificación y playoffs siguen explícitamente deshabilitadas. El split publicado usa `AmericanoDraftOperations`, `AmericanoSetupCapabilities`, `AmericanoListPageProps` y `AmericanoSetupPageProps` (§5), sin simular las18 operaciones. `can_generate` expresa elegibilidad de dominio, no disponibilidad de la operación. El subconjunto frontend draft ya fue verificado con API real; no completa5.1/5.2.
- **Límites y efecto metadata:** sin cambios de login/auth ni imports de registro en `migrations/env.py`/`database/session.py`, migraciones aplicadas, BD de usuario, builds, commits o despliegues. La cadena `main→router→service→models` sí registra las ocho tablas en metadata compartida por import, **sin ejecutar DDL de inicio**. Tablas creadas únicamente en SQLite nuevo descartable de pruebas con fixtures aisladas; no prueba locks PostgreSQL. Guard global/data router/logout queda fuera del slice. Activación del esquema productivo requiere autorización separada. Esta pasada documental no ejecuta tests ni servidores.

**Publicación frontend alineada:** las seis plantillas/etiquetas/fixtures reflejan D3/D6/D8 aprobados; `DecisionStatus.proposed` sigue válido para futuras plantillas. [verification.md](verification.md) conserva snapshots históricos; la primera sección registra el cierre vigente31/31.

### Registro histórico: delta 2.0.0 frente a 1.0.0

- Cambio incompatible **solo del contrato de componentes frontend**: `DirtyNavigationDraft` agrega `readonly pending:boolean` y `discard():boolean` reemplaza `discard():void`; `ScoreRowProps` requiere `zoneLabel:ZoneLabel`; `RoundDraftState` agrega `rebase(round):void`. HTTP conserva sus shapes. Al publicar2.0.0 D3/D6/D8 seguían pendientes; su aprobación posterior se registra en2.1.0 arriba.
- Consumidores actuales verificados: `AmericanoRoundPage` produce el descriptor y consume sus acciones en el diálogo local; es el único consumidor de `ScoreRow` y `useRoundDraft`. Tipos y estos consumidores se actualizan juntos. Los fixtures estáticos no producen descriptores ni props de estos componentes y no requieren cambios. El futuro `useDirtyNavigation`/guard/logout de I debe consumir la nueva semántica de §5 antes de integrarse; no está implementado por este delta.
- UUID se normaliza en DTO mediante `str(UUID(value))`: las representaciones textuales válidas de una misma UUID producen la misma string canónica minúscula con guiones. Backend debe comparar/persistir la identidad normalizada para replay, no el texto original. Esta normalización no implementa por sí sola el servicio transaccional de confirmación.

## Camino de consumo

1. B implementa DTO desde [tipos TypeScript](../../../frontend/src/api/americano-types.ts) y la matriz HTTP inferior; no importa modelos D para declarar DTO.
2. A implementa los tipos estándar y firmas de §4 dentro de sus módulos; D adapta persistencia y B adapta filas/DTO, sin contaminar el núcleo puro.
3. U/R importan **solo tipos** del archivo compartido, preparan exports/props de §5 y usan [escenarios](../../../frontend/src/pages/americanos/__fixtures__/scenarios.ts) exclusivamente desde un harness de desarrollo aislado.
4. Toda modificación incompatible vuelve a I: pausar consumidores afectados, actualizar contrato/tipos/fixtures juntos, verificar y publicar versión antes de reanudar.

Fuentes normativas: [D3–D9](design.md), [AE](specs/americano-admin-events/spec.md), [RW](specs/americano-round-workstation/spec.md), [AQ](specs/americano-qualification/spec.md), [AK](specs/americano-knockouts/spec.md). Los detalles mecánicos aquí fijados completan esas decisiones; no las reemplazan.

## 1. Vocabulario, identidad y decisiones aprobadas

| Concepto | Contrato v2 |
|---|---|
| IDs | Enteros positivos seguros para JSON/JavaScript; no UUID para entidades. `event_id`, `zone_id`, `registration_id`, `match_id`, `node_id` no son intercambiables. Registro = pareja fija; no introducir `team_id` ni referencias a liga. |
| Etiqueta de pareja | `player1_name` y `player2_name`, recortados/no vacíos. UI compone `nombre1 / nombre2`; no campo alternativo `team_name`. Los nombres repetidos son válidos; identidad por ID. |
| Estados | `draft`, `groups`, `review`, `playoffs`, `completed`. |
| Etapas | `quarterfinal`, `semifinal`, `final`; singular, sin alias `quarters`, `semi` ni valores traducidos en JSON. |
| Zonas/lados | `zone_count`: 1 o 2; `label`: `A`/`B`; `side`: `a`/`b`. IDs de zonas reales, nunca etiqueta usada como FK. |
| Orden | `registration_order`, `display_order`, ronda, posición de seed y `slot` son enteros **desde 1**. Orden de nodos: cuartos→semifinal→final, luego slot. |
| Pendiente/cero | GET: ambos games `null` o ambos completos; nunca un lado solo. 0-0 es resultado completo. Formulario de grupos: `ScoreInput`, `''` o un dígito; jamás `Number('')`. No existe ronda número 0; fixture `zeroZero` representa marcador 0-0. |
| Puntos | `points_half_units` entero >=0: triunfo +2, empate +1, derrota +0. Mostrar unidades/2 con coma decimal; no campo `points` flotante. Diferencia = games a favor menos en contra. |
| Orden deportivo | Solo `(-points_half_units,-games_diff)`; bloque empatado tiene `position_from..position_to`. `registration_order` estabiliza filas, no resuelve plazas. |
| Strings/fechas | JSON strings Unicode; fechas UTC RFC3339, por ejemplo `2026-10-20T12:00:00Z`. `confirmation_key` es string UUID válido, normalizado con `str(UUID(value))`, una clave por intención; respuestas en formato canónico minúsculo con guiones. |
| Forma cerrada | B rechaza extras; lecturas incluyen todos los campos declarados. Solo los campos marcados `?` en TS pueden omitirse. Nullable significa explícitamente `null`, no omisión. Enteros estrictos rechazan bool, strings numéricos y floats, incluso `1.0`. |

### Decisiones vigentes aprobadas (2026-10-21)

| Referencia | Estado | Consecuencia para los carriles |
|---|---|---|
| D3: aleatorio equilibrado, diferencia <=1 | Aprobado; manual desigual permitido |3.2/3.3 aceptadas; reparto guardado sin shuffle. Contención PostgreSQL3.3 aceptada previamente, sin nueva prueba en4.1. Ningún algoritmo aleatorio en G0/A. |
| D3: congelar composición/nombres/configuración al generar, sin regeneración | Aprobado, AE-03 |3.3 aceptada, incluso review cero partidos; congelación preservada en4.1. |
| D6: semifinales directas | Aprobado | Una zona 1-4/2-3; dos A1-B2/B1-A2. |
| D6: cuartos y final directos | Aprobado | Las seis plantillas actuales son approved; constructor8.1 puro aceptado. Confirmación real7.2 y cuadros completos integrados. Ninguna plantilla default oculta; proposed futuro preservado. |
| D8: terminal exacto del set, correcciones/final | Aprobado |8.2 pura aceptada tras P2 resuelto/revisión PASS;8.3 y editor8.4 aceptados con evidencia propia. Constructor8.1, snapshot y cuadro read-only no dependen del set. |

Plantillas aprobadas: cuartos una zona Q1=1-8,Q2=4-5,Q3=2-7,Q4=3-6; dos Q1=A1-B4,Q2=B2-A3,Q3=B1-A4,Q4=A2-B3. Final directa una zona1-2/dos A1-B1. Q1/Q2→S1 lados a/b; Q3/Q4→S2 a/b; S1/S2→F1 a/b. Semifinales usan S1/S2 en el orden aprobado. El parámetro explícito `seeding_template` conserva estos cruces y destinos.

Claves iniciales de plantilla: `quarterfinal-one-zone-v1`, `quarterfinal-two-zones-v1`, `semifinal-one-zone-v1`, `semifinal-two-zones-v1`, `final-one-zone-v1`, `final-two-zones-v1`. Las seis tienen status approved y etiquetas/fixtures alineados en la publicación actual. Son identificadores del seeding aprobado, no un selector público de reglamentos. B construye SeedRef con IDs reales A/B; A valida plantilla recibida, no busca una por key ni la aprueba.

## 2. HTTP, DTO y errores

### 2.1 Convenciones de transporte

Prefijo `/admin/americanos`, **todos los métodos protegidos** mediante la dependencia administrativa existente. Ruta de colección canónica sin slash final; no exigir redirect para usarla. `{e}`/`{r}`/`{n}` son IDs de evento/inscripción/nodo; `{number}` es número de ronda, no ID de fila.

El archivo `frontend/src/api/americano-types.ts` es el esquema exacto de campos JSON y exports; esta sección fija su semántica y asociación a cada endpoint. B reproduce los mismos nombres en `schemas.py`, sin importar TS ni depender de D. No hay envelope `data`, paginación, auth token nuevo ni propiedades de ORM implícitas.

| Método/ruta relativa | Solicitud completa | Respuesta exitosa | Operación de `AmericanoOperations` |
|---|---|---|---|
| GET colección | Sin body/query | 200 `ListEventsResponse` = `EventSummary[]` | `listEvents()` |
| POST colección | `CreateEventRequest` | 201 `EventDetail` | `createEvent(request)` |
| GET `/{e}` | Sin body | 200 `EventDetail` | `loadEvent(e)` |
| PATCH `/{e}` | `UpdateEventRequest` | 200 `EventDetail` | `updateEvent(e,request)` |
| POST `/{e}/registrations` | `RegistrationRequest` | 201 `EventDetail` | `addRegistration(e,request)` |
| POST `/{e}/registrations/bulk` | `BulkRegistrationRequest` | 201 `EventDetail` | `addRegistrations(e,request)` |
| PATCH `/{e}/registrations/{r}` | `UpdateRegistrationRequest` | 200 `EventDetail` | `updateRegistration(e,r,request)` |
| DELETE `/{e}/registrations/{r}` | **Query** `expected_revision=N`, sin body | 200 `EventDetail` | `deleteRegistration(e,r,{expected_revision})` |
| PUT `/{e}/zones` | `SetZonesRequest` | 200 `EventDetail` | `setZones(e,request)` |
| DELETE `/{e}/zones` | **Query** `expected_revision=N`, sin body | 200 `EventDetail` | `clearZones(e,{expected_revision})` |
| POST `/{e}/zones/randomize` | `RevisionRequest` | 200 `EventDetail` | `randomizeZones(e,request)` |
| POST `/{e}/fixture` | `RevisionRequest` | 200 `GenerateFixtureResponse` | `generateFixture(e,request)` |
| GET `/{e}/rounds/{number}` | Sin body | 200 `RoundResponse` | `loadRound(e,number)` |
| PUT `/{e}/rounds/{number}/results` | `SaveRoundRequest` | 200 `SaveRoundResponse` | `saveRound(e,number,request)` |
| GET `/{e}/standings` | Sin body | 200 `StandingsResponse` | `loadStandings(e)` |
| GET `/{e}/qualification` | Sin body | 200 `QualificationResponse` | `loadQualification(e)` |
| PUT `/{e}/tie-resolutions` | `SaveTieResolutionsRequest` | 200 `QualificationResponse` | `saveTieResolutions(e,request)` |
| POST `/{e}/confirm-qualifiers` | `ConfirmQualifiersRequest` | 200 `ConfirmationResponse` (también replay) | `confirmQualifiers(e,request)` |
| GET `/{e}/playoffs` | Sin body | 200 `PlayoffsResponse` | `loadPlayoffs(e)` |
| PUT `/{e}/playoffs/{n}/result` | `SaveKnockoutRequest` | 200 `PlayoffsResponse` | `saveKnockout(e,n,request)` |

La matriz publica las20 operaciones contractuales: setup12, GET ronda/standings, PUT resultados de ronda, GET qualification, PUT tie-resolutions, POST confirm-qualifiers, GET playoffs y PUT resultado eliminatorio. Los puertos comparten loadEvent. **POST `/{e}/fixture` + `RevisionRequest`→200 `GenerateFixtureResponse={event,first_round}`** conserva shape; `/generate` no es ruta publicada.

DELETE con query permite usar `api.delete(path)` sin cambiar el cliente base ni perder la revisión de D5. El cliente draft codifica `expected_revision` en query, verificado con HTTP real. No responder204: U necesita revisión/listado canónicos después de eliminar.

### 2.2 Solicitudes cerradas

| Tipo exportado | Campos y validación |
|---|---|
| `RevisionRequest` | `expected_revision: integer >=1`, requerido. |
| `GroupSourceRequest` | Lo anterior + `source_groups_revision: integer >=0`. |
| `CreateEventRequest` | `name: string` recortado no vacío, `zone_count:1\|2`, `start_stage:StartStage`; todos requeridos, sin revisión/inscripciones iniciales. |
| `UpdateEventRequest` | Revisión + `name?`, `zone_count?`, `start_stage?`; al menos uno presente, ninguno acepta null. Cambio de cantidad de zonas conserva A, crea/elimina B en draft; una zona asigna todas a A, pasar a dos conserva asignaciones A y permite completar reparto. |
| `RegistrationRequest` | Revisión + `player1_name`, `player2_name`, ambos strings recortados no vacíos; identidad y orden asignados por servidor. Una zona asigna A; dos permite `zone_id=null` hasta PUT de reparto. |
| `BulkRegistrationRequest` | Revisión + `registrations:RegistrationInput[]` con mínimo dos parejas; cada elemento contiene dos strings recortados no vacíos. Alta atómica en una revisión, con órdenes consecutivos. Sigue disponible el POST individual para una pareja. |
| `UpdateRegistrationRequest` | Revisión + uno o ambos nombres opcionales no vacíos, nunca null; no permite cambiar zona/orden/ID. |
| `SetZonesRequest` | Revisión + `zone_count`, `zone_a_registration_ids:integer[]` únicos y propios. Dos zonas: A=selección, B=complemento; una zona exige conjunto exacto de todas las inscripciones como A. Selección vacía válida en draft de dos, pero puede impedir generar. |
| Orden/numeración visible | `registration_order` es ordinal contiguo desde1, nunca el ID de fila. Al eliminar se compactan los supervivientes; la próxima alta usa el siguiente ordinal libre, incluso después de eliminar todas las parejas. |
| DELETE `/{e}/zones` | Query `expected_revision=N`; solo en borrador con dos zonas. Limpia a `zone_id=null` todas las parejas, tanto si el reparto guardado fue manual como aleatorio. En una propuesta manual, deseleccionar una pareja de A la muestra temporalmente como `Sin asignar`; al guardar, las no seleccionadas se asignan a B. |
| `SaveRoundRequest` | Revisión + `results:GroupResult[]`, conjunto exacto de partidos de la ronda. Cada uno `{match_id,games_a,games_b}`, games strict0..9, sin null/ausentes; duplicados, faltantes o extra422. |
| `SaveTieResolutionsRequest` | Ambas revisiones + `resolutions:TieResolution[]`, reemplazo completo de **todas y solo** plazas empatadas relevantes `{zone_id,position,registration_id}`. Sin selección incompleta, duplicados ni IDs ajenos al bloque. Lista vacía válida si no hay plazas a resolver. Slots firmes no se envían. |
| `ConfirmQualifiersRequest` | Ambas revisiones + `confirmation_key:string UUID`; validar string y normalizar con `str(UUID(value))` antes de comparar/persistir. No recibe seeds, plantilla ni nodos del navegador. |
| `SaveKnockoutRequest` | Revisión + `games_a`, `games_b`: enteros estrictos >=0, distintos; `set_complete:true` literal. Sin límite0..9/arrays de sets. D8 exige exactamente 6-0..6-4,7-5,7-6 y simétricos; no basta desigualdad para declarar set válido. |

### 2.3 Respuestas: esquema y responsabilidades

Los siguientes tipos y **todos sus campos** están declarados en TS; no agregar alias alternativos en un carril. Contadores y flags son calculados por B, no por el navegador.

| Tipo | Campos / significado |
|---|---|
| `Zone` | `id,label`; no incluye copias de parejas. |
| `Registration` | `id,zone_id:null\|ID,player1_name,player2_name,registration_order`; sin FK a liga. |
| `EventSummary` | `id,name,state,zone_count,start_stage,revision,groups_revision,registration_count,total_rounds,saved_rounds,max_unlocked_round,continuation`. Lista simple ordenada por ID descendente (presentación, no deporte). |
| `EventDetail` | Resumen + `zones,registrations,quotas,can_generate,configuration_issues,confirmed_at,champion_registration_id`. Registros ordenados por registration_order; zonas A/B. `can_generate` solo draft, composición completa y cupos suficientes. |
| `ZoneQuota` | `zone_id,required,registered,sufficient`; required = 8/4/2 dividido por cantidad de zonas, nunca redondeado. |
| `ConfigurationIssue` | `code:insufficient_registrations\|unassigned_registrations,zone_id:null\|ID,registration_ids,message`; para insuficiencia lista vacía, para no asignadas IDs reales. |
| `Continuation` | Unión cerrada `{kind:setup}`, `{kind:round,round_number}`, `{kind:qualification}`, `{kind:playoffs}`. No URL backend. |
| `GroupMatch` | `id,zone_id,display_order,registration_a,registration_b,games_a,games_b`; registros completos, IDs a<b, pendiente ambos null. No ID de ronda necesario: pertenece a la respuesta pedida. |
| `RestingRegistration` | `registration,reason:bye\|capacity\|zone_finished`; todas las que no juegan, sin duplicados. Bye lógico tiene prioridad sobre espera por capacidad; zona sin bloque vigente = zone_finished. |
| `RoundResponse` | `event_id,event_name,state,revision,groups_revision,number,total_rounds,max_unlocked_round,saved,locked,read_only,zones,matches,resting`. `saved` indica ronda completa persistida; `locked` indica secuencia; `read_only` indica cierre de grupos, independiente de locked. |
| `GenerateFixtureResponse` | `{event:EventDetail,first_round:RoundResponse\|null}`; null solo si cero partidos, review directo, total_rounds=0. No respuesta de fixture masivo para render. |
| `StandingRow` | `registration,played,won,drawn,lost,games_for,games_against,games_diff,points_half_units`; métricas solo guardadas. |
| `StandingBlock` | `position_from,position_to,points_half_units,games_diff,rows`; posiciones inclusivas, longitud=to-from+1, misma métrica para todas. Singleton también es bloque. |
| `ZoneStandings` | `zone,blocks`, bloques ordenados deportivamente y filas estables sin asignar seeds por orden visual. |
| `StandingsResponse` | `event_id,state,revision,groups_revision,frozen,zones`; frozen solo playoffs/completed. Ambas zonas en una respuesta, tabla vacía posible en draft. |
| `SaveRoundResponse` | `{round,standings}`, mismas revisiones/estado en ambos. El cliente adopta baseline tras éxito; no desbloquea antes. |
| `SeedRef` / `NodeRef` | Seed = `{zone_id,position}`, nodo lógico = `{stage,slot}`; no son IDs de BD. |
| `QualificationSlot` | SeedRef + `candidate_registration_ids,registration_id:null\|ID,requires_resolution`; slots para todas las posiciones1..q por zona. Singleton firme: un candidato; empatado: **todo** bloque original, no filtrar por otras selecciones. |
| `ResolvedSeed` / `TieResolution` | SeedRef + `registration_id`; forma igual pero roles distintos: resolved_seeds incluye firmes y manuales, resolutions solo manuales. |
| `SeedingTemplate` | `key,status:approved\|proposed,start_stage,zone_count,opening_pairs:[{a:SeedRef,b:SeedRef}]`; orden del array determina slot inicial1..N. Referencias a IDs de zonas de ese evento. |
| `BracketSource` | `{kind:seed,zone_id,position}` o `{kind:winner,stage,slot}`. Mantener fuente lógica aunque aún no exista participante. |
| `BracketDestination` | `{stage,slot,side}`; final null. |
| `BracketPreviewNode` | NodeRef + `source_a,source_b,registration_a_id,registration_b_id,next`; apertura resuelve solo seeds disponibles, etapas posteriores IDs null antes de jugar. Sin IDs de nodo inventados en preview. |
| `QualificationResponse` | `event_id,state,revision,source_groups_revision,standings,quotas,slots,missing_slots,resolved_seeds,seeding_template,bracket,blockers,can_confirm,frozen`. `missing_slots:SeedRef[]` solo selección pendiente. `blockers:[{code,message}]` con códigos `groups_incomplete,configuration_invalid,unresolved_ties,seeding_pending_approval`; can_confirm solo review y blockers vacío. `seeding_pending_approval` no corresponde a las seis plantillas actuales aprobadas; se conserva para futuras propuestas. Preview en draft/groups200 con bloqueos; tras cierre200 frozen usando snapshots canónicos, nunca habilita confirmar. |
| `QualifierSnapshot` | ResolvedSeed + `player1_name,player2_name,points_half_units,games_diff,source_groups_revision`; no ID artificial de snapshot requerido por UI. |
| `KnockoutNode` | `id,stage,slot,registration_a:null\|Registration,registration_b:null\|Registration,games_a,games_b,set_complete,next_match_id,next_side,winner_registration_id,can_edit,edit_block_reason`. `next_match_id`/side ambos null en final, ambos presentes en resto. Pendiente games null/set_complete false; jugado ambos enteros/set_complete true. Motivos: participants_pending, rules_pending_approval, descendant_played o null. `rules_pending_approval` se conserva en el shape, pero no describe D8 ya aprobado ni sustituye el gate de capacidad aún no implementada. |
| `PlayoffsResponse` | `event_id,event_name,state:playoffs\|completed,revision,groups_revision,start_stage,zones,snapshots,nodes,champion:null\|Registration`. Nodes ordenados por etapa/slot; campeón solo cuando final guardada. |
| `ConfirmationResponse` | `event:EventDetail,confirmation_key,confirmed_source_revision,confirmed_at,playoffs:PlayoffsResponse`; grupos source congelado, event/playoffs revision actual consistente. Replay devuelve campeón/resultados actuales si playoffs avanzó. |

### 2.4 Errores compatibles con el cliente existente

Error propio de Americano: cuerpo **plano**, sin objeto anidado en detail:

```json
{"detail":"El evento cambió; recargá antes de guardar.","code":"revision_conflict","message":"El evento cambió; recargá antes de guardar.","current_revision":7,"fields":[{"path":["expected_revision"],"code":"stale","message":"Revisión obsoleta."}]}
```

`detail === message`: `api/client.ts:readDetail` muestra el texto; `ApiError.body` conserva code/fields. `current_revision` obligatorio en errores409 cuando se conoce el evento; `fields` opcional, paths relativos al payload, números para índices (ej. `["results",2,"games_b"]`). No exponer IDs ajenos en mensajes. B normaliza también422 de validación **solo para este router**, sin cambiar handlers globales/auth. 401 sigue el cuerpo actual de auth (`{detail:string}`), fuera de `AmericanoErrorBody`; conserva evento de sesión existente. Errores de red continúan `ApiError(status=0,body=null)`.

| HTTP | Códigos exactos |
|---|---|
| 404 | `not_found`: evento o recurso anidado ajeno/inexistente; número de ronda inexistente. |
| 422 | `validation_error`, `invalid_configuration`, `invalid_reference` (ID ajeno en payload), `invalid_round_results`, `invalid_tie_resolution`, `invalid_set`. |
| 409 | `revision_conflict`, `groups_revision_conflict`, `state_conflict`, `round_locked`, `already_confirmed`, `descendant_played`, `participants_pending`, `decision_pending`. |

GET de ronda existente pero secuencialmente bloqueada devuelve409 `round_locked`, no sus marcadores; `locked` se conserva en shape para guards defensivos y respuestas compuestas. La UI carga continuación canónica tras conflicto. GET playoffs antes del cierre409 `state_conflict`. Confirmar grupos incompletos409 `state_conflict`; preview explica `groups_incomplete`. Referencia a partido propio de otra ronda422; ID de nodo anidado ajeno404.

`decision_pending` conserva compatibilidad para futuras reglas no aprobadas; no debe bloquear las seis plantillas actuales ni D8. El gate de capacidades ausentes del slice setup con fixture se expresa en su wiring/puerto, sin inventar endpoints implementados ni errores deportivos de aprobación pendiente.

## 3. Revisiones, estado y navegación

### 3.1 Contrato transaccional D5

- `revision` inicial1, incrementa **una vez por mutación exitosa** (también PUT idéntico aceptado); replay de confirmación no incrementa. GET nunca muta. Crear evento devuelve1. Rechazos/rollback no alteran revisiones.
- `groups_revision` inicial0; incrementa una vez por ronda guardada/corregida con cambio efectivo de scores; primera persistencia null→0 cuenta. PUT idéntico no incrementa ni borra resoluciones. Configuración, fixture, resoluciones y playoffs no la cambian.
- Cada escritor de evento existente bloquea evento **primero** (`FOR UPDATE`), relee fase/revisión, luego hijos; un commit. Usa transacción existente de SessionDep; helpers solo flush. Reads compuestas toman brevemente FOR SHARE para revisión/hijos coherentes. No mantener locks durante interacción.
- Reemplazo de ronda exacto/atómico, incluida corrección; nunca persistir parciales. Cambio efectivo elimina **todas** las resoluciones del evento. Tabla se recalcula desde resultados actuales, nunca suma incrementalmente una corrección.
- Resoluciones PUT requiere review y ambas revisiones; reemplaza conjunto completo y modifica solo revision. `source_groups_revision` de preview siempre es groups_revision guardada actual. `confirmed_source_revision` es la groups_revision confirmada, no la revision global.
- Confirmación: lock→si misma clave confirmada, replay canónico **antes** de rechazar revisión vieja→si otra clave ya cerró409→validar review/revisiones/cupos/resoluciones→recalcular→snapshot + constructor + todos los nodos + estado en un commit. Nunca confiar en seeds cliente. Si falla, no quedan snapshots/nodos/estado parcial.
- Carrera corrección/cierre: primer lock define orden; corrección invalida cierre viejo, o cierre bloquea corrección. PostgreSQL descartable con dos sesiones es la futura evidencia; SQLite no prueba locks.
- Timeout PUT: conservar borrador; GET canónico. Solo si saved y todos los IDs/games coinciden exactamente y la identidad de partidos/zonas/participantes se conserva adoptar baseline/revisión como éxito, incluso si grupos ya quedaron read-only. Si difieren, mostrar servidor y edición local: **usar servidor** descarta la edición; **conservar mi edición** adopta baseline/revisión canónicos manteniendo strings por match_id y habilita un posterior guardado completo explícito, nunca reenvía automáticamente. Esta última acción exige groups/review, sin locked/read_only y misma membresía exacta (IDs de partido, zona y ambos registros/lados); un cambio de orden visual no altera identidad. Otro409 requiere nueva comparación. GET fallido deja reconciliación pendiente, sin baseline inventado ni descarte exitoso; volver a comprobar no reutiliza una comparación anterior si falla. Confirmación reusa **misma** UUID normalizada ante respuesta perdida; una nueva UUID solo tras nueva intención válida.

### 3.2 Transiciones y continuación

| Estado | Escrituras/continuación |
|---|---|
| draft | Configuración, nombres, parejas y reparto. Generar solo con todos asignados y cupos suficientes. Continuación setup. |
| groups | Guardar primera pendiente o corregir guardadas. Generar una vez; composición/nombres/configuración congelados según D3 aprobado. Continuación primera no guardada. |
| review | Todas guardadas, corrección de cualquier ronda y resoluciones; sin auto-confirmar. Continuación qualification. Cero partidos entra aquí directamente con cero rondas. |
| playoffs | Solo resultados eliminatorios según D8 aprobado, cuando se implemente su capacidad; grupos/resoluciones/composición read-only. Continuación playoffs. |
| completed | Campeón persistido; consulta y corrección de final permitida según D8, actualizando campeón atómicamente y conservando completed/grupos cerrados. Continuación playoffs. |

`max_unlocked_round = min(prefijo_guardado+1,total_rounds)`; si total0 vale0. Todas guardadas→última ronda consultable en URL explícita, continuación por estado review/playoffs. Nunca montar ronda0 ni ronda vacía artificial.

URLs de UI: `/admin/americanos` listado; `/:eventId` resuelve continuación; `/:eventId/configuracion`; `/:eventId/rondas/:roundNumber`; `/:eventId/clasificados`; `/:eventId/playoffs`. Número/ID inválido o ronda bloqueada→continuación segura obtenida del evento. Conservar URL de ronda explícita desbloqueada al refrescar, incluso tras cierre con read_only. No localStorage de nombres/scores.

**Wiring vigente al cierre original:** HTTP/DTO2.1.0; componentes3.0.0. AmericanoEventRoute resuelve continuación canónica; setup10,round4 con mode editable y autoridad read_only backend; AmericanoStageRoute inyecta qualification4 o playoffs3+onDirtyChange. Guard/data router conservan límites Auth/público.1+1 no inventa ronda0; resultados/avance/campeón integrados.5.1/8.4 completas; G3/G4 pendientes.

Dirty de ronda: baseline persistido separado de strings locales. Guard5.3 implementado con guardar/descartar/permanecer para rutas/historial/enlaces/logout y beforeunload; bloquea también pending aunque dirty=false. Guardar exige éxito limpio sin pending; descartar restaura baseline y false cancela. Clasificación conserva solicitud incierta y exige recuperación/adopción explícita, sin POST automático.

### 3.3 Recuperación de setup draft publicada

- `Recargar evento` mantiene montado el editor y conserva propuesta, strings e identidad de inscripción durante/después del GET. Tras conflicto/fallo incierto, bloquear nuevas escrituras hasta obtener estado canónico y una adopción explícita. GET fallido conserva edición y bloqueo; invalida la comparación anterior, sin baseline inventado ni descarte automático. No promete conservar borradores tras recarga completa del documento.
- `Usar datos guardados` adopta evento/revisión canónicos y descarta propuesta; `Conservar mi edición` adopta revisión/baseline, conservando la propuesta, **sin enviar una escritura**. Requiere draft y, al editar pareja, que su ID siga existiendo. No recrear una inscripción eliminada ni trasladar asignaciones de zona obsoletas.
- El merge de configuración es **por campo contra el baseline previo**: conservar solo nombre, cantidad de zonas o etapa realmente editados; los campos no editados se toman del canónico, también al conservar una edición de pareja. Un posterior guardado explícito usa revisión actual y configuración fusionada; no sobreescribe cambios concurrentes de campos intactos.
- Ante POST de alta individual o por lote con respuesta incierta, mostrar advertencia de que pudo persistirse y pedir revisar las parejas guardadas. Keep no reenvía ni recrea automáticamente. Nombres repetidos son válidos; un nuevo envío explícito puede crear otra pareja y no se deduplica por nombre. No asumir que un fallo de red implica rollback.
- 3.2: propuesta de zonas conservada para comparar tras409/GET fallido, pero keep de asignación obsoleta bloqueado; adoptar canónico explícitamente, sin trasplantar IDs ni escribir. Guards locales config/pareja/zona impiden mutaciones incompatibles; no implementan5.3. PUT200 de zonas y POST201 de inscripción confirmados en servidor con respuesta perdida fueron verificados live: reconciliación GET explícita, sin reintento/duplicado automático.
- 3.3 implementada: generar requiere capacidad, draft/elegibilidad, sin edición config/pareja/zonas ni pending y confirmación nativa irreversible. Se adopta `response.event`; ante respuesta incierta, GET canónico automático puede adoptar estado generado read-only. Si GET falla, las escrituras siguen bloqueadas hasta verificar; si devuelve draft, requiere adopción explícita y nueva intención confirmada, nunca retry automático de POST. Live verificó dos respuestas realmente comprometidas y luego perdidas, GET exitoso/fallido y peticiones abortadas antes de llegar al backend. La concurrencia PostgreSQL de3.3 quedó validada por separado mediante veinte carreras reales; la recuperación de respuestas perdidas no sustituye esa prueba.

## 4. Contratos Python puros (A → B/D)

**Dependencias: biblioteca estándar solamente** (`dataclasses`, `typing`, `collections.abc`). Ningún import de SQLModel, Pydantic, Session, configuración, reloj, random o `app.main`. Paquete `americanos/__init__.py` deliberadamente no reexporta/importa modelos. Estos contratos no fueron código ejecutado por0.1. Las tareas1.1/1.2/1.3 se aceptaron puras por auditoría dedicada del código existente, sin RED retrospectivo;8.1/8.2 exclusivamente puras, P2 corregido/revisado PASS. No aceptan integración API/persistencia por sí mismas.

Todos los dataclasses aquí son `@dataclass(frozen=True)`; colecciones de salida `tuple`, no listas mutables compartidas. Firmas aceptan `Sequence`/`Mapping`. Las entradas pertenecen a **un evento**; B valida pertenencia antes de adaptar. Sin event_id en núcleo: no valida autorización. A valida unicidad/rangos y referencias internas, con `type(x) is int` donde corresponda para excluir bool. No mutar entradas. `AmericanoDomainError` deriva de ValueError y expone campos indicados; B traduce a HTTP. No usar HTTPException en A.

### 4.1 `fixture.py`: dueño de aliases y tipos de calendario

```python
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

StartStage = Literal['quarterfinal', 'semifinal', 'final']
ZoneLabel = Literal['A', 'B']
Side = Literal['a', 'b']
RestReason = Literal['bye', 'capacity', 'zone_finished']

# Exception attributes (A implements __init__, not a dataclass):
# AmericanoDomainError(ValueError):
#   code: str; message: str; path: tuple[str | int, ...]
#   __init__(code: str, message: str, path: tuple[str | int, ...] = ())

@dataclass(frozen=True)
class Pairing:
    registration_a_id: int
    registration_b_id: int

@dataclass(frozen=True)
class LogicalRound:
    number: int
    pairings: tuple[Pairing, ...]
    bye_registration_id: int | None

@dataclass(frozen=True)
class ZoneInput:
    zone_id: int
    label: ZoneLabel
    registration_ids: tuple[int, ...]

@dataclass(frozen=True)
class FixtureMatch:
    zone_id: int
    registration_a_id: int
    registration_b_id: int
    display_order: int

@dataclass(frozen=True)
class Rest:
    zone_id: int
    registration_id: int
    reason: RestReason

@dataclass(frozen=True)
class FixtureRound:
    number: int
    matches: tuple[FixtureMatch, ...]
    resting: tuple[Rest, ...]

def zone_pairings(registration_ids: Sequence[int]) -> tuple[LogicalRound, ...]: ...
def build_fixture(zones: Sequence[ZoneInput], capacity: int = 6) -> tuple[FixtureRound, ...]: ...
```

`registration_ids` vienen en orden de inscripción estable; no ordenarlos por ID para decidir Berger. `Pairing` y `FixtureMatch` canonicalizan lados por ID (a<b), preservan orden visual de la arista. Berger fija primer ID, empareja índices i y n-1-i para i=0..n/2-1, rota restantes un paso a derecha por bloque; impar agrega centinela al final, elimina sus aristas y registra bye. n<2 retorna tuple vacío. `build_fixture` llama zone_pairings por zona A/B, combina mismo índice lógico y corta consecutivamente en capacidad sin mezclar siguiente bloque. `capacity` strict1..6; default6; >6 no puede permitir violar AE-07. Zonas/IDs duplicados o pertenencia múltiple→invalid_configuration. Cero aristas→cero rondas. Rest incluye todas las parejas ociosas: bye si sentó centinela, capacity si su arista quedó en otro fragmento, zone_finished si zona no tiene bloque (incluye unipersonal). Sin IDs persistentes de partidos/rondas, los asigna D/B al guardar.

### 4.2 `standings.py`: tipos exactos de tabla

```python
@dataclass(frozen=True)
class StandingRegistration:
    id: int
    zone_id: int
    player1_name: str
    player2_name: str
    registration_order: int

@dataclass(frozen=True)
class SavedScore:
    match_id: int
    zone_id: int
    registration_a_id: int
    registration_b_id: int
    games_a: int
    games_b: int

@dataclass(frozen=True)
class StandingRow:
    registration: StandingRegistration
    played: int
    won: int
    drawn: int
    lost: int
    games_for: int
    games_against: int
    games_diff: int
    points_half_units: int

@dataclass(frozen=True)
class StandingBlock:
    position_from: int
    position_to: int
    points_half_units: int
    games_diff: int
    rows: tuple[StandingRow, ...]

@dataclass(frozen=True)
class ZoneStanding:
    zone_id: int
    blocks: tuple[StandingBlock, ...]

def calculate_standings(
    registrations: Sequence[StandingRegistration], saved_scores: Sequence[SavedScore],
) -> tuple[ZoneStanding, ...]: ...
```

No importar fixture para calcular cruces ni standings de liga. Puede importar aliases/error de fixture (sin efectos). Entradas solo completas/guardadas0..9, nada de None; B filtra rondas guardadas antes de llamar. Rechazar match_id o cruce repetido, score con registro/zona inexistente, lados iguales o cruzados. Registros sin partidos aparecen con cero. Zonas retornadas ordenadas por zone_id (B presenta por label); zona sin registros se completa como blocks vacío en B. Orden de filas empatadas registration_order; igual orden duplicado es inválido, no usar ID para seed.

### 4.3 `qualification.py`: cupos y selección, sin dependencias de bracket

Importa StartStage/error de fixture y `ZoneStanding` de standings. No importa modelos, schemas ni bracket; evita ciclo qualification↔bracket.

```python
from collections.abc import Mapping, Sequence

@dataclass(frozen=True)
class SeedRef:
    zone_id: int
    position: int

@dataclass(frozen=True)
class TieResolution:
    zone_id: int
    position: int
    registration_id: int

@dataclass(frozen=True)
class QualificationSlot:
    zone_id: int
    position: int
    candidate_registration_ids: tuple[int, ...]
    registration_id: int | None
    requires_resolution: bool

@dataclass(frozen=True)
class ResolvedSeed:
    zone_id: int
    position: int
    registration_id: int

@dataclass(frozen=True)
class QualificationPreview:
    slots: tuple[QualificationSlot, ...]
    missing_slots: tuple[SeedRef, ...]
    resolved_seeds: tuple[ResolvedSeed, ...]

def qualification_quotas(start_stage: StartStage, zone_ids: Sequence[int]) -> dict[int, int]: ...
def qualification_preview(
    blocks: Sequence[ZoneStanding], quotas: Mapping[int, int], resolutions: Sequence[TieResolution],
) -> QualificationPreview: ...
```

`qualification_quotas`: exactamente1/2 zonas únicas, total8/4/2; devuelve cupo por ID (8/4/2 o4/2/1). No hardcodear IDs/labels. Preview exige suficientes filas por cupo; insuficiencia→invalid_configuration, B emite preview HTTP con blocker/configuración antes de invocarlo. Para cada bloque que interseca1..q, singleton se resuelve automáticamente; si más de una candidata, todas las posiciones relevantes requieren elección, aun si todas clasifican. Bloque3..5 con q4 permite cualquier par distinto de esas tres para plazas3/4; no pide plaza5.

Preview acepta subconjunto válido de resoluciones para mostrar faltantes, pero rechaza duplicados, candidato ajeno o plaza no relevante (`invalid_tie_resolution`). **B exige conjunto completo en PUT**, y ambas revisiones; A no recibe ni decide revisiones. `requires_resolution` sigue true tras seleccionar; distingue plaza manual de firme. Candidates mantienen bloque original. Seeds resueltos son subconjunto hasta completar, no rellenar null con orden visual. Orden de slots/seeds por zone_id/position; B presenta zonas por label.

### 4.4 `bracket.py`: plantilla explícita, topología y reglas posteriores

Importa StartStage/Side de fixture y SeedRef/ResolvedSeed de qualification. Tipos de topología no importan validador de set ni lo ejecutan. Separación interna en el mismo archivo A, no crear capa/paquete adicional.

```python
@dataclass(frozen=True)
class NodeRef:
    stage: StartStage
    slot: int

@dataclass(frozen=True)
class SeedSource:
    kind: Literal['seed']
    zone_id: int
    position: int

@dataclass(frozen=True)
class WinnerSource:
    kind: Literal['winner']
    stage: StartStage
    slot: int

BracketSource = SeedSource | WinnerSource

@dataclass(frozen=True)
class OpeningPair:
    a: SeedRef
    b: SeedRef

@dataclass(frozen=True)
class SeedingTemplate:
    key: str
    status: Literal['approved', 'proposed']
    start_stage: StartStage
    zone_count: Literal[1, 2]
    opening_pairs: tuple[OpeningPair, ...]

@dataclass(frozen=True)
class BracketDestination:
    stage: StartStage
    slot: int
    side: Side

@dataclass(frozen=True)
class BracketLayoutNode:
    stage: StartStage
    slot: int
    source_a: BracketSource
    source_b: BracketSource
    next: BracketDestination | None

@dataclass(frozen=True)
class BracketNode:
    stage: StartStage
    slot: int
    source_a: BracketSource
    source_b: BracketSource
    registration_a_id: int | None
    registration_b_id: int | None
    games_a: int | None
    games_b: int | None
    set_complete: bool
    next: BracketDestination | None

def bracket_layout(start_stage: StartStage, seeding_template: SeedingTemplate) -> tuple[BracketLayoutNode, ...]: ...
def build_bracket(
    start_stage: StartStage, resolved_seeds: Sequence[ResolvedSeed], seeding_template: SeedingTemplate,
) -> tuple[BracketNode, ...]: ...
```

`bracket_layout` es la entrega de topología de8.1 para preview incompleta: B combina fuentes seed con resolved_seeds y deja winners null. No llamar build_bracket con seeds incompletos. Ambos requieren plantilla explícita, etapa coincidente, cantidad/zona/posiciones correctas, cada seed una vez, sin byes. `build_bracket` exige exactamente8/4/2 IDs únicos; apertura con ambos IDs, futuros nodos ambos None, games None/set_complete false. Devuelve7/3/1 nodos en orden, sin IDs BD. B inserta y traduce NodeRef→node_id para next_match_id, preservando side. Las fuentes winner siempre anteriores y cada destino/side único. Constructor puede verificar una plantilla **proposed** explícita sin aprobarla; **B bloquea confirmación real** si status no aprobado. No hay plantilla default ni selección por reglas de set.

Contrato8.2 **aceptado exclusivamente puro tras P2 corregido/revisado PASS** (ninguna convención/política fue instanciada o aprobada en G0; **D8 aprobado posteriormente el2026-10-21**). Estado DB/completed y persistencia atómica pertenecen a8.3, no implementada:

```python
@dataclass(frozen=True)
class FullSetScore:
    games_a: int
    games_b: int
    set_complete: bool

@dataclass(frozen=True)
class SetConvention:
    key: str
    minimum_winner_games: int
    win_by: int
    tiebreak_at: int | None
    tiebreak_winner_games: int | None

@dataclass(frozen=True)
class ValidatedSet:
    games_a: int
    games_b: int
    winner_side: Side

@dataclass(frozen=True)
class CorrectionPolicy:
    key: str
    block_played_descendants: bool
    allow_final_correction: bool

@dataclass(frozen=True)
class BracketChange:
    node: NodeRef
    score: ValidatedSet
    correction_policy: CorrectionPolicy

@dataclass(frozen=True)
class PropagationResult:
    nodes: tuple[BracketNode, ...]
    champion_registration_id: int | None

def validate_full_set(score: FullSetScore, convention: SetConvention) -> ValidatedSet: ...
def propagate_winner(nodes: Sequence[BracketNode], change: BracketChange) -> PropagationResult: ...
```

Convention parametriza objetivo mínimo y ventaja necesaria: al alcanzar objetivo, perdedor <= objetivo-win_by; si ganador supera objetivo, diferencia exactamente win_by, sin prolongar un set ya terminado. Si ambos llegan a tiebreak_at, terminal con ganador tiebreak_winner_games y perdedor tiebreak_at; no seguir por ventaja después de ese punto. D8 aprobado fija `minimum_winner_games=6`, `win_by=2`, `tiebreak_at=6`, `tiebreak_winner_games=7`: únicamente6-0..6-4,7-5,7-6 y simétricos. Rechazar5-3,6-5,empates y cualquier prolongación por ventaja; no ofrecer set largo ni selector de reglamentos. Validación rechaza negativos/bool/float, set_complete distinto de True y terminal no permitido; retorna lado ganador. Propagación consume score validado, verifica consistencia del lado con games, participantes conocidos y referencia existente, reemplaza resultado y, si cambia ganador, únicamente su lado del siguiente partido pendiente sin tocar el otro lado; final fija campeón. Retorna **todos los nodos nuevos**, sin mutar entrada. La política aprobada fija `block_played_descendants=True` y `allow_final_correction=True`: cualquier descendiente jugado bloquea toda corrección, aun mismo ganador; final corregible también tras completed. B valida nuevamente contra convención aprobada y persiste resultado+avance/campeón juntos, conservando completed al corregir final y grupos cerrados. Sin borrado automático, eliminación de resultados ni reapertura.8.2 pura aceptada calcula cambios/campeón sin estado DB;8.3 y la integración de resultados siguen fuera del slice vigente.

**Implementación revisada8.2:** `_index_bracket` valida tipo/stage/slot/existencia y reciprocidad de fuentes/destinos; `_validate_participants` exige participantes derivados del ganador de su fuente. Repro de campeón999 no ganador rechazado con `invalid_configuration`, path `('nodes',2,'registration_a_id')`; winner source ausente/final truncada rechazados.999 como seed legítima sigue válido; no es blacklist de IDs. Evidencia independiente final y TDD en `verification.md`.

## 5. Exportaciones frontend y preparación por inyección

Todas las pantallas/componentes/hooks tienen **exports nombrados**, sin default ni barrels nuevos. AmericanoOperations declara20 operaciones exactas, implementadas por puertos estrechos reales: draft7/setup12/round4/qualification4/playoffs3 con loadEvent compartido. Sin mocks productivos ni fallbacks. HTTP/DTO2.2.0 aditivo; componentes3.0.0 por nuevas props requeridas del editor. Importar tipos con import type.

| Tipo publicado | Contrato del slice setup con fixture |
|---|---|
| `AmericanoDraftOperations` | `Pick<AmericanoOperations, 'listEvents' \| 'createEvent' \| 'loadEvent' \| 'updateEvent' \| 'addRegistration' \| 'updateRegistration' \| 'deleteRegistration'>`; siete métodos de §2.1. |
| `AmericanoSetupCapabilities` | `Pick<AmericanoOperations, 'addRegistrations' \| 'setZones' \| 'clearZones' \| 'randomizeZones' \| 'generateFixture'>`; setup inyecta las cinco capacidades reales. El puerto draft conserva siete métodos y alta individual. |
| `AmericanoListPageProps` | `operations: Pick<AmericanoDraftOperations, 'listEvents' \| 'createEvent'>` y `onNavigate(target:AmericanoNavigation):void`. |
| `AmericanoSetupPageProps` | `operations: Pick<AmericanoDraftOperations, 'loadEvent' \| 'updateEvent' \| 'addRegistration' \| 'updateRegistration' \| 'deleteRegistration'> & Partial<AmericanoSetupCapabilities>`, `eventId:AmericanoId`, `onNavigate(target:AmericanoNavigation):void`. |

El wiring setup/round/clasificación/cuadro completo está publicado: grupos editables hasta cierre y eliminatorias a set completo hasta campeón.5.1/8.4 aceptadas. Estrategia/historia en tasks.md y verification.md; ninguna entrega autoriza migraciones/despliegue.

| Dueño/archivo | Export y contrato de entrada |
|---|---|
| U `AmericanosPage.tsx` | `AmericanosPage(props: AmericanoListPageProps)` |
| U `AmericanoSetupPage.tsx` | `AmericanoSetupPage(props: AmericanoSetupPageProps)` |
| U `AmericanoQualificationPage.tsx` | `AmericanoQualificationPage(props: AmericanoQualificationPageProps)`; puerto4 métodos `loadEvent/loadQualification/saveTieResolutions/confirmQualifiers`. |
| U `AmericanoPlayoffsPage.tsx` | `AmericanoPlayoffsPage(props:AmericanoPlayoffsPageProps)`; operations:AmericanoPlayoffsOperations (loadEvent/loadPlayoffs/saveKnockout), eventId,onNavigate,onDirtyChange requerido. Descriptor dirty/pending equivalente a ronda; null al desmontar. |
| R `AmericanoRoundPage.tsx` | `AmericanoRoundPage(props: AmericanoRoundPageProps)` |
| R `ScoreRow.tsx` | `ScoreRow(props: ScoreRowProps)` |
| R `StandingsDrawer.tsx` | `StandingsDrawer(props: StandingsDrawerProps)` |
| U `QualificationSlots.tsx` | `QualificationSlots(props: QualificationSlotsProps)` |
| R `useRoundDraft.ts` | `useRoundDraft(round: RoundResponse): RoundDraftState` |
| I `useDirtyNavigation.tsx` | `DirtyNavigationProvider` bajo data router; `useDirtyNavigation(): (draft: DirtyNavigationDraft \| null) => void` entrega callback estable compatible con `onDirtyChange`; `useGuardedLogout()` recibe la acción de logout. I mantiene el descriptor del puesto activo (ronda o eliminatorias) para rutas/logout; null en cleanup. Sin delta HTTP ni consumidores previos de un hook implementado. |

Props completas heredadas de2.0.0 (listado/setup usan el split2.1.0 de arriba; puesto de ronda v2 sin cambios):

- `AmericanoPageProps`: `operations`, `onNavigate(target:AmericanoNavigation):void`. U/R cargan a través de operations, sin imports al cliente incompleto ni fetch directo.
- `AmericanoEventPageProps`: lo anterior + `eventId:number` positivo ya parseado por wrapper I.
- `AmericanoRoundPageProps`: lo anterior + `roundNumber:number`, `onDirtyChange(draft:DirtyNavigationDraft|null):void`. R notifica descriptor actual y null en desmontaje; evita efectos que registren una dependencia recién creada por tecla innecesariamente. Descriptor `{dirty,readonly pending,save():Promise<boolean>,discard():boolean}`: `pending` es lectura viva de PUT/GET en curso **o reconciliación sin resolver**, no una copia que espera render. `save()` devuelve false en validación/fallo/conflicto/pendiente, true solo tras persistencia canónica verificada; antes de resolver true se publica dirty=false y pending queda false al terminar la operación. `discard()` devuelve false mientras hay operación en curso o resultado incierto sin GET canónico; true solo tras restaurar baseline (o adoptar el servidor de la comparación y resolver la reconciliación), publicando estado limpio sin pendiente. I debe bloquear rutas/logout si **dirty || pending**, no ofrecer descarte durante una escritura y comprobar el booleano de descarte antes de continuar: false SIEMPRE cancela salida. Tras guardar debe esperar true y releer pending; un guard que solo consulta dirty o ignora discard() es incompatible con v2. I decide diálogo y navegación; harness puede recoger descriptor sin router. Esta obligación no equivale a tener guard global integrado.
- `ScoreRowProps`: match, **zoneLabel (`ZoneLabel`, A/B real desde round.zones)**, value (`RoundDraftRow`), readOnly, errors por lado, onChange(matchId,side,ScoreInput), onAdvance(matchId,side), registerInput(matchId,side,HTMLInputElement|null). Nombre accesible incluye pareja, rival, zona y partido/display_order, nunca zone_id como etiqueta; zona ausente es respuesta inválida, no fallback al FK. onAdvance solo en vacío→dígito válido por input/paste de un dígito, no restauración/corrección; último no guarda.
- `StandingsDrawerProps`: open, standings|null, loading, error|null, onClose(), returnFocusTo:HTMLElement|null. R conserva captura del punto de carga, trap/Escape/restauración; abrir no cambia URL, ronda ni strings. Tabla solo guardados.
- `QualificationSlotsProps`: preview, registrations, resolutions, disabled, onChange(resolutions). Muestra todos los candidatos reales, selección de IDs únicamente; sorteo humano, sin random ni posición visual usada como desempate.
- `RoundDraftState`: rows, dirty, errors por match_id/lado, setScore, validate():SaveRoundRequest|null (incluye revisión del baseline), reset(), accept(round), **rebase(round)**. `accept` reemplaza baseline y strings; `rebase` reemplaza solo baseline/revisión y reordena strings conservados por match_id, después de revisión humana y verificación de membresía/permiso por el consumidor. Dirty compara strings con este baseline por identidad, no índice; reset restaura ese servidor, incluidos null→blanco y0→'0'. Baseline no cambia por un error ni por abrir cajón; nuevo round/event reinicia desde servidor; respuesta guardada se acepta explícitamente, no sobrescribir dirty ante refetch inesperado.

`AmericanoNavigation` contiene list/event/setup/round/qualification/playoffs con event_id y round_number según corresponda; I traduce a URLs de §3. No imports de router obligatorios para preparar componentes con props. No crear store, repositorio, nueva librería ni adaptador productivo; un harness futuro puede inyectar operaciones en memoria. Preparación con fixtures **no completa**5.2/6.x/7.4/8.4.

### Fixtures publicados, sin ruta ni comportamiento runtime

`scenarios` exporta draft, empty, zeroZero, sixMatches, byes, elevenFieldsDraft, ties, twoWayTies, review, resolvedReview, snapshot, bracket. También exports nombrados individuales (draftEvent, roundEvent, reviewEvent, etc.). Son constantes tipadas deterministas, sin random/reloj/fetch, métodos ni fallbacks. No están importadas por entrypoints/pantallas productivos; solo consumir desde harness dev aislado cuando exista. No se creó harness/ruta en G0.

- Evento102: cuatro parejas, semifinales aprobadas, tres rondas; empty y zeroZero distinguen null/0 con IDs301/302; no existe una ronda0.
- Evento103: 7+7, seis filas y dos byes reales; elevenFieldsDraft deja exactamente un campo vacío, conserva ceros. byes comparte ese escenario, sin simular generación.
- ties: cuatro parejas con todos sus partidos0-0, tres medios puntos cada una; twoWayTies cambia dos cruces a1-0 y produce dos bloques reales empatados.
- review/resolvedReview: cuatro plazas manuales reales; selección2/1/4/3 y cruces2-v-3,1-v-4; no ID como desempate.
- snapshot/bracket: cierre de semifinal aprobado, nodos401/402→403; sin resultados. Históricamente se publicaron con flags rules_pending_approval/participants_pending por D8 entonces pendiente. La publicación2.1.0 ya alinea etiquetas/flags con D8 aprobado; resultados/confirmación siguen fuera del slice draft y participants_pending solo corresponde a participantes faltantes. UUID y fecha fijas solo de fixture. Esta muestra no afirma confirmación ejecutada en BD.

## 6. Propiedad y entrega de W1

Reserva por **archivo completo**, D9 define el mapa general; autorización vigente prevalece sobre la ola histórica inferior. I integra exclusivamente `tasks.md`, `verification.md`, `contracts.md`, `design.md`, `proposal.md` y notas introductorias de disponibilidad AE/AK si hace falta. Backend/frontend3.3 entregados/revisados; el integrador no modifica implementación. La matriz inferior no autoriza nuevas capacidades ni operaciones Git.

| Carril | Puede empezar tras G0 / archivos propios | Dependencias y entrega |
|---|---|---|
| A | fixture.py→standings.py→qualification.py; bracket.py constructor8.1; tests puros correspondientes | Estándar solamente. A posee también **todas las definiciones puras de §4 en esos archivos**, no un nuevo common.py. Entregar por función/tipos estables. bracket_layout/build_bracket no esperan D/B/D8. |
| D | models.py, database/session.py, migrations/env.py, única revisión aditiva, test_americano_models.py | D declara enums DB str propios con valores exactos v1; sin dependencia de A o schemas. Preparar2.1→2.3; único dueño head. No ejecutar DDL, ni repair lateral de metadata. |
| B | schemas.py primero; luego service.py/router.py/main.py y tests API de D9 | DTO usan Literals/enums locales con valores v1, no importar models.py para definirlos. Servicio espera entregas de D y A por capacidad. Mapea dataclasses↔DTO/DB, revisiones/locks/errores. Ningún import de API/auth desde A. |
| U | AmericanosPage, AmericanoSetupPage; luego QualificationPage/PlayoffsPage y QualificationSlots | Solo TS compartido + primitives existentes, operations/onNavigate por props. fixtures únicamente harness de desarrollo. No import de live client/rutas inexistentes. |
| R | RoundPage/useRoundDraft/ScoreRow/StandingsDrawer | Mismos tipos/port, callbacks dirty/foco de §5. No esperar setup ni backend. Entrega preparación tipada, no aceptación live. |
| I | Contrato/checklist/types/fixtures/init compartido; cliente/rutas/main/App/Layout/useDirtyNavigation más adelante | No iniciar5.1/5.3 en G0. Coordina5 escritores máximo; espera cupo liberado. Cambios en scaffolding compartido solo I. |

Tests API clasificación B `test_americano_qualification_api.py` separados de `test_americano_qualification.py` puro A; bracket constructor y reglas son mismo A en momentos distintos. Revisores DOM/PRIV solo lectura. Hallazgo vuelve al dueño, sin revertir trabajo ajeno. No commits/stash/reset/clean/worktrees automáticos.

## 7. Registro histórico de verificación y apply G0

`openspec status --change admin-americanos --json` y `openspec instructions apply --change admin-americanos --json` confirmaron spec-driven, cuatro artefactos done, ready,0/31 antes de editar. No hay openspec/config.yaml: se usan instrucciones explícitas del lote y runners declarados, sin generar configuración/foundation.

| Tarea | Modo / baseline | RED | GREEN / evidencia | Triangulación/refactor |
|---|---|---|---|---|
| 0.1 | Excepción **type-only/contrato/constantes** autorizada; `npm run lint` baseline pasó | No aplicable: ninguna conducta productiva implementada, sin runner TS declarado | `npm run lint` final pasó; OpenSpec strict pasó (1 cambio,0 issues); revisión de imports y whitespace pasó | No assertions tautológicas ni tests espejo de constantes. TDD estricto queda requerido para comportamiento futuro A/B/R según runner disponible. |

No ejecutar pytest para este scaffold de solo docstring: el conftest raíz importa aplicación/engine y su fixture client borra/recrea tablas (`tests/conftest.py:18-35,48-63`). Para A, antes de ejecutar tests puros, I debe confirmar aislamiento del conftest o aprobar preparar harness puro propio: **no asumir que seleccionar un test evita conftest**. Recomendación, si pytest está disponible en el entorno declarado: desde backend `PYTHONPATH=src .venv/Scripts/python.exe -m pytest --noconftest tests/test_americano_fixture.py` para tests puramente estándar/autocontenidos (no instalar). Revisar que --noconftest no desactive fixtures realmente requeridas antes de usarlo. Para API/modelos, solo BD explícitamente descartable y propia por proceso, con autorización de ejecución correspondiente; PostgreSQL para locks, serializar si no hay recursos independientes. Ningún TEST_DATABASE_URL de usuario, servidor o migración en G0.

Comprobaciones ejecutadas:

- Antes de editar: `openspec status --change admin-americanos --json`; `openspec instructions apply --change admin-americanos --json`; desde frontend `npm run lint` → exit0.
- Después de publicar tipos/fixtures: desde frontend `npm run lint` → exit0, incluye ambos archivos bajo tsconfig strict/noUncheckedIndexedAccess.
- `openspec validate admin-americanos --strict --type change --no-interactive --json` → valid=true,0 issues, exit0. Esta es validación de artefactos, no prueba del comportamiento HTTP/puro futuro.
- `git diff --check` y `git diff --no-index --check -- /dev/null <archivo nuevo>` para tipos/fixtures/contrato → sin errores de whitespace; Git solo avisa normalización LF→CRLF. Se usa no-index porque openspec/ ya era untracked al comenzar.
- Búsqueda de `__fixtures__|americano-types|scenarios` en src TS/TSX: solo el import de tipos y la declaración scenarios dentro del propio fixture; ningún consumidor productivo. `git status --short --untracked-files=all` conserva los artefactos previos, sin editar otros archivos productivos.

Este archivo es también registro persistente de la única tarea entregada; no crear apply-progress adicional fuera de la reserva. Las comprobaciones finales se registran aquí tras ejecutarlas. Engram no está disponible entre las herramientas de esta sesión (recursos y templates MCP vacíos); no se simula mem_save. Topic solicitado para una sesión que lo disponga: `LigaLaAmistad` / `opsx/admin-americanos/apply`.

## 8. Estado actual y siguiente corte

**31/31 tareas aceptadas; G3/G4 verificados.** API/cliente **18 operaciones privadas reales**; puertos setup10/draft7,round4,qualification4 yplayoffs3 comparten `loadEvent`, no son conteos sumables. Contrato de componentes **3.0.0**; HTTP/DTO conserva shapes **2.1.0**. Confirmación, cuadro, resultados y campeón real integrados; grupos permanecen cerrados. No se activó en producción.

**Continuación acotada:** obtener autorización separada para ensayo PostgreSQL descartable2.3 (upgrade/down/reup preservando liga) y carrera7.3 (dos sesiones score/confirm), después consolidar9.3/handoff HIGH/CRITICAL. Alternativa sin DDL ahora: revisión estática adicional, sin presentarla como sustituto del ensayo. No commit/push/archivo/despliegue automáticos; trabajo local tras `5908f16`.
