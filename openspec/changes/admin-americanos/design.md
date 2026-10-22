## Context

Módulo privado y aditivo de Americanos dentro del admin existente. Las specs definen aceptación. **D3/D6/D8 aprobados el2026-10-21**, seis plantillas/etiquetas/fixtures alineados. Contrato **[2.1.0](contracts.md)** sin cambios. **14/31 aceptadas,17 pendientes** según [checklist](tasks.md): nuevas4.2/4.3 backend con PostgreSQL FULL PASS y5.2/6.4 por auditorías dedicadas;1.x/8.x siguen puras.5.1 PARTIAL;2.x/5.3/6.1–6.3/9.x/G2/G3/G4 pendientes. [Estado actual e historia](verification.md).

### Aprobación humana y slice vigente — actualizado2026-10-22

Fuente: **«confirma todas ls decisiones que tenes ahi.»**, en respuesta a la consulta detallada sobre las recomendaciones D3/D6/D8 y el slice técnico. Se aprueban esas recomendaciones, no las alternativas. La nota es posterior a G0 y a las correcciones documentadas; preserva su historia.

Tras «continuamos» posterior al commit previo `2bc5abf`,1.1/1.2/1.3 se aceptaron puras por auditoría dedicada del código existente, sin RED retrospectivo, y3.3 backend/frontend se implementó/revisó. I integra solo documentación; no agrega aceptación por suites verdes.8.2 pura conserva P2 resuelto: fuentes recíprocas/participantes derivados del ganador;999 no ganador/fuente winner ausente/final truncada rechazados y999 seed legítima aceptada. Estado DB/campeón atómico siguen en8.3; API playoffs ausente.

El backend publica **13 operaciones privadas**, incluido PUT de ronda. Cliente draft siete/setup diez/round cuatro, con `loadEvent` compartido. Quedan cinco operaciones futuras: GET qualification, PUT resoluciones, POST confirmación y GET/PUT playoffs. Fixture conserva `RevisionRequest` → `{event,first_round}`; zonas/random, `EventDetail` directo.5.2/6.4 aceptadas;5.1 PARTIAL. Recuperación explícita/merge por campo y generación incierta en contrato §3.3.

**Disponibilidad actual:** generación confirmada, recuperación GET y consulta real de ronda/tablas montada bajo el guard admin existente; UI editable deshabilitada hasta aprobar5.3. Nombres/configuración congelados, sin resorteo/regeneración;1+1 review sin ronda0.4.2/4.3 incluyen guardado atómico, revisiones/invalidation y contención PostgreSQL independiente tras P2 de binding int32 corregido, DTO JSON-safe intacto. Frontend: rutas adicionales en App, wrappers/setup, RoundPage/hook/ScoreRow y puertos API; main/Layout/auth conservados. Mismas ocho tablas por import, sin DDL de arranque; migración/activación productiva separadas.

### Base verificada

| Evidencia actual | Consecuencia |
|---|---|
| `docs/06-modo-de-trabajo.md:13-26` pide servicios función con `Session`, sin Repository/UoW, y decisiones deportivas humanas. | Mantener ese patrón y distinguir supuestos de reglas aprobadas. |
| `backend/src/app/auth/deps.py:12-32` valida cookie y administrador activo; `matches/router.py:17-21` aplica la dependencia al router. | Reutilizar `get_current_admin` en todo el router nuevo, incluidos GET. |
| `matches/service.py:125-146,195-237` requiere 2/3 sets y conecta resultados con playoffs de liga. | No invocarlo para Americanos. |
| `standings/service.py:18-21,132-179` usa 3/2/1/0 y desempates adicionales; `playoffs/models.py:169-194` fija 19 nodos. | Crear cálculo y cuadro propios; reutilizar solo el patrón de función pura. |
| `public/router.py:49-83,140-142` consulta tablas y servicios de liga. | No insertar registros de Americano en esas tablas ni ampliar contratos públicos. |
| `frontend/src/App.tsx:22-75`, `components/Layout.tsx:10-18`, `api/client.ts:45-87` delimitan admin, navegación y cliente con credenciales. | Integrar ahí conservando la colocación de proveedores y manejo de sesión. |
| `frontend/src/main.tsx:13-15` usa `BrowserRouter`; `package.json` no declara runner frontend. | El guard de navegación necesita una adaptación explícita; no inventar tests frontend existentes. |
| `backend/tests/conftest.py:18-20,48-63` usa SQLite temporal por defecto y borra/recrea tablas. | Verificación futura exclusivamente sobre BD descartable; concurrencia real requiere PostgreSQL descartable. |
| `backend/migrations/env.py:15-21` enumera imports de metadata; `database/session.py:17-32` registra modelos para tests. | Agregar import de modelos propios en ambos lugares; revisar el Migration Plan antes de autogenerar. |

Artefactos redactados en español, siguiendo `README.md` y `docs/`; encabezados estructurales de OpenSpec conservados según el CLI instalado 1.4.1.

## Goals / Non-Goals

**Goals:** eventos aislados, configuración variable, fixture completo con capacidad global 6, puesto de escritorio de una ronda, tabla exacta, cierre consistente y eliminatorias flexibles privadas. Preservar liga en curso y datos públicos. Contratos verificables y unidades pequeñas de implementación.

**Non-Goals:** los límites de `proposal.md`, en particular regenerar/reabrir grupos, trasladar parejas de liga, reservas/horarios, publicación, nuevas dependencias, event sourcing o rediseñar autorización.

## Decisions

### D1. Dominio aditivo y límites de integración

Nuevo `backend/src/app/americanos/`:

| Archivo propuesto | Responsabilidad |
|---|---|
| `models.py`, `schemas.py` | Persistencia propia y DTO explícitos con IDs acotados al evento. |
| `fixture.py` | Cruces Berger y distribución global determinista. |
| `standings.py`, `qualification.py` | Métricas exactas, bloques empatados y asignación de plazas relevantes. |
| `bracket.py` | Plantillas 8/4/2, destinos, validación de set y avance/corrección como cálculos puros. |
| `service.py` | Funciones con `Session`, aislamiento, transacciones y composición de respuestas. |
| `router.py` | Endpoints síncronos con `SessionDep`, DTO/response models y `dependencies=[Depends(get_current_admin)]`. |

Registrar únicamente este router en `app/main.py`. No llamar a servicios deportivos de liga. Ningún cambio en `app/auth/`, CORS, cookies o permisos. No crear repositorios ni UoW.

**Alternativa:** añadir `event_id` a modelos de liga. Ahorra entidades inicialmente, pero cambia consultas públicas, unicidades, reglas y migración de datos activos; se descarta por riesgo de filtración y regresión. **Alternativa:** servicio separado; agrega despliegue/auth/comunicación sin necesidad operativa.

### D2. Modelo persistente y aislamiento de referencias

IDs enteros estables, estilo actual; nombres visibles `jugador 1 / jugador 2`, sin fotos ni vínculo a personas/parejas de liga. Timestamps reutilizan el mixin existente. Estado y etapas como enums Python persistidos en texto con CHECK, evitando nuevos tipos enum PostgreSQL si no aportan valor.

| Tabla propuesta | Datos principales e invariantes |
|---|---|
| `americano_events` | `id`, `name`, `state`, `zone_count` (1/2), `start_stage`, `revision >= 1`, `groups_revision >= 0`, `confirmed_at`, `confirmation_key`, `confirmed_source_revision`, `champion_registration_id?`. Estado inicial `draft`. |
| `americano_zones` | `id`, `event_id`, `label` A/B; UNIQUE(event_id,label), UNIQUE(event_id,id). |
| `americano_registrations` | `id`, `event_id`, `zone_id?` (solo en borrador puede faltar), dos nombres no vacíos, `registration_order`; UNIQUE(event_id,id), UNIQUE(event_id,registration_order). Nombres no son identidad ni se exige unicidad nominal. |
| `americano_rounds` | `id`, `event_id`, `number >= 1`, `saved_at?`; UNIQUE(event_id,number), UNIQUE(event_id,id). Desbloqueo derivado del prefijo de rondas guardadas, no de un cursor cliente. |
| `americano_group_matches` | `id`, `event_id`, `round_id`, `zone_id`, `registration_a_id`, `registration_b_id`, `display_order`, `games_a?`, `games_b?`; parejas canónicas `a_id < b_id`, UNIQUE(event_id,a_id,b_id), UNIQUE(round_id,display_order). Ambos games NULL o ambos enteros 0..9. |
| `americano_tie_resolutions` | `id`, `event_id`, `zone_id`, `source_groups_revision`, `position`, `registration_id`; UNIQUE(event_id,zone_id,position) y UNIQUE(event_id,registration_id). Solo posiciones relevantes, no orden completo de eliminados. |
| `americano_qualifier_snapshots` | `id`, `event_id`, `zone_id`, `position`, `registration_id`, nombres, `points_half_units`, `games_diff`, `source_groups_revision`; UNIQUE(event_id,zone_id,position), UNIQUE(event_id,registration_id). Inmutables tras confirmar. |
| `americano_knockout_matches` | `id`, `event_id`, `stage`, `slot`, lados nullable, games nullable, `set_complete`, `next_match_id?`, `next_side?`; UNIQUE(event_id,stage,slot). Final sin destino; resultados solo con lados conocidos y games completos/desiguales. |

Todas las tablas hijas indexan `event_id`; índices compuestos para ronda por número, partidos por (event_id,round_id), registros por (event_id,zone_id), nodos por (event_id,stage,slot). UNIQUE ya cubre varios accesos; no duplicar índices equivalentes. FK compuestas `(event_id, child_id)` a identidades UNIQUE homólogas impiden referencias entre eventos, incluidos lados/destinos/campeón; declarar UNIQUE(event_id,id) en toda tabla destino, incluidos nodos eliminatorios. Pertenencia a la misma zona y una participación por ronda se verifican además en generación/servicio antes de persistir. Rutas siempre cargan por `(event_id,id)`; nunca `session.get(child,id)` sin verificar dueño.

No cascadas a tablas de liga ni endpoints de eliminación de eventos activos. Eliminación de una inscripción únicamente en `draft` y sin referencias; el borrado de registros de evento no es requisito del MVP. Snapshots guardan clasificados, no una copia masiva de todos los partidos; la tabla congelada puede recomputarse porque grupos y parejas quedan bloqueados.

**Alternativa:** torneo completo en JSON; simplifica una inserción pero pierde FKs, restricciones y consultas de conflictos. **Elección:** filas normalizadas con una única revisión de concurrencia por evento, sin contadores/event sourcing innecesarios.

### D3. Estados, configuración y límites aprobados

```text
draft --generar fixture--> groups --guardar última ronda--> review
                              (si no hay partidos: review directo)
review --corregir grupos--> review [invalida resoluciones/preview]
review --confirmar atómicamente--> playoffs --guardar final--> completed
completed --corregir final permitida--> completed [actualiza campeón]
```

- `draft`: nombres/inscripciones, una/dos zonas, etapa inicial y reparto editables; evento vacío válido, generación inválida si cupos no alcanzan.
- `groups`: solo la primera no guardada puede estrenarse; todas las guardadas siguen editables. No se permite borrar resultados guardados dejándolos incompletos: toda corrección reemplaza ronda completa.
- `review`: todos los partidos guardados; ningún bloqueo todavía. Volver a cargar resultados es posible sin regresar a borrador.
- `playoffs`/`completed`: grupos, composición, fixture y resoluciones inmutables en backend; lecturas siguen habilitadas.

**Aprobado el2026-10-21:** congelar composición, nombres/integrantes y configuración al generar (incluso antes de jugar), no regenerar; reparto aleatorio equilibrado con diferencia de tamaño <=1. El reparto manual puede ser desigual. No imponer mínimo 2 por zona si el cupo es 1: una zona unipersonal produce cero partidos y esa pareja descansa todas las rondas de la otra zona. Dos zonas unipersonales con final pasan a revisión sin rondas vacías. No hay clasificación automática por confirmación implícita.

La asignación aleatoria se guarda en borrador y se muestra antes de generar. Se puede ajustar manualmente antes del fixture; generar no vuelve a sortear. No hay random en desempates deportivos. **Alternativa:** aleatorizar durante generación ahorra una acción, pero vuelve opaco el reparto; se descarta.

**Estado3.2/3.3 aceptado:** reparto manual/random persistido/visible y cupos insuficientes guardables en draft (ej.1+8, `can_generate=false`); una zona exige todas, random diferencia <=1 y manual desigual. Generar consume membresía/orden guardados sin shuffle y congela todos los mutadores existentes;0 partidos entra review sin rondas. Contención PostgreSQL3.3 aceptada previamente;4.1 preserva estas reglas.

### D4. Algoritmos puros con contratos explícitos

| Función propuesta | Entrada → salida / validación |
|---|---|
| `zone_pairings(registration_ids)` | IDs únicos en orden estable → lista de rondas Berger de aristas intrazona y bye lógico; n<2 da lista vacía, n impar usa centinela, no partido ficticio. |
| `build_fixture(zones, capacity=6)` | Rondas lógicas por zona → rondas globales numeradas con cruces, orden visual y parejas ociosas; función pura, sin BD, reloj ni sorteo. |
| `calculate_standings(registrations, saved_scores)` | Marcadores completos guardados → métricas por pareja y bloques ordenados por `(-points_half_units,-games_diff)`; empate conserva bloque/rango de posición. |
| `qualification_preview(blocks, quotas, resolutions)` | Bloques y resoluciones de revisión vigente → plazas firmes, plazas empatadas con candidatos reales, faltantes y seeds resueltos; no hace random. |
| `build_bracket(start_stage, resolved_seeds, seeding_template)` | Exactamente 8/4/2 seeds únicos y plantilla explícita → 7/3/1 nodos acíclicos, destinos y slots, sin BD ni byes. Constructor independiente del validador de set y de correcciones; las seis plantillas actuales están aprobadas, una futura propuesta no se aprueba por construirla. |
| `validate_full_set(score, convention)`, `propagate_winner(nodes, change)` | Set bajo D8 aprobado → ganador y cambios en destino/campeón, o error; corrección falla si cualquier descendiente ya tiene resultado, aun mismo ganador. |

**Distribución de rondas:**
1. Generar Berger independientemente por zona; cada bloque lógico i contiene el i-ésimo conjunto de A más el i-ésimo de B si existen.
2. Orden estable de aristas por zona y posición Berger. Cada bloque tiene parejas disjuntas, también entre zonas.
3. Dividir el bloque en fragmentos consecutivos de <=6 partidos; cada fragmento es una ronda global real. No mezclar fragmentos con el siguiente bloque lógico.
4. Numerar globalmente; calcular ociosas como todas las inscriptas menos las que juegan ese fragmento. Distinguir `bye` lógico de `espera por capacidad/zona terminada` en el texto de descanso.

Esto garantiza cobertura y ausencia de solapamiento sin prometer optimización. Ejemplos: 8 en una zona → 7x4=28; 7+7 → 7x6=42; 16 en una zona → 15 bloques de 8 divididos 6+2, 30 rondas reales y 120 partidos; 5+4 → 5 bloques globales, 16 partidos, B termina antes. No se muestran 8 partidos concurrentes aunque fueran una ronda Berger.

**Alternativa:** empaquetado greedy entre todos los bloques podría reducir rondas, pero añade conflictos de jugadores y vuelve impredecibles los ejemplos; **no necesario** para el MVP. No agregar librería de optimización.

Puntuación: victoria suma 2 unidades enteras, empate 1 a cada una, derrota 0; presentación `units / 2` formateada como `0`, `0,5`, `1`, etc. El contrato expone `points_half_units`, no floats acumulados. `games_diff = games_for - games_against`; no usar sets ni enfrentamiento directo. Un orden por `registration_order` solo estabiliza filas dentro de bloques con rango compartido (`3–5`, `empatadas`); jamás decide un seed.

### D5. Transacciones, revisiones e idempotencia mínima

Cada mutación de un evento existente recibe `expected_revision`, adquiere **primero** su fila mediante `SELECT ... FOR UPDATE`, recarga estado (`populate_existing` si procede), valida revisión y estado, hace todos los cambios y confirma **una vez**. Las revisiones se incrementan al mutar; `groups_revision` solo cambia si cambian marcadores guardados. Todos los escritores, incluidos configuraciones, resoluciones y playoffs, usan el mismo orden evento → hijos. No locks globales, procesos en segundo plano ni llamadas externas dentro de la transacción.

El `SessionDep` es compartido con auth: su lectura de `AdminUser` puede haber abierto una transacción. El servicio usa esa transacción y controla `commit`/`rollback`; no anidar ciegamente `with session.begin()` ni copiar helpers de liga que hagan commits parciales. Helpers puros o persistentes internos solo `flush`. Las lecturas compuestas de puesto, tabla y revisión toman brevemente `FOR SHARE` sobre evento antes de leer hijos para devolver un estado/revisión consistente respecto de los escritores; no mantener el bloqueo durante trabajo de usuario.

```text
PUT ronda(expected_revision, resultados completos)
  lock evento → comprobar groups/review y revisión → cargar ronda/partidos propios
  → exigir conjunto exacto de IDs y ambos enteros 0..9 → validar desbloqueo
  → escribir toda la ronda → si cambió: groups_revision++, eliminar resoluciones
  → derivar review si terminó → revision++ → construir respuesta coherente → commit
  cualquier error → rollback (sin tabla parcial ni nuevo desbloqueo)

POST confirmar(expected_revision, source_groups_revision, confirmation_key)
  lock evento → si misma clave ya confirmada: devolver confirmación canónica
  → si ya cerrado con otra clave: 409
  → comprobar review/revisiones → releer todos los resultados y recalcular bloques
  → verificar resoluciones actuales y cupos → snapshot de seeds
  → construir e insertar cuadro completo → state=playoffs, confirmed_at/key/source
  → revision++ → commit único; fallo revierte todos los pasos
```

Clave UUID generada una vez por intención de confirmar y conservada durante reintentos; se guarda en evento (no nuevo servicio de idempotencia). Constraints únicas por seed y nodo refuerzan la ausencia de duplicados. Replay de la misma clave devuelve estado canónico sin mutar aunque la revisión enviada sea la antigua; otra clave recibe conflicto. El servidor nunca confía en seeds completos enviados por el navegador.

Corrección vs cierre: quien obtiene lock primero determina el orden. Si corrige, aumenta revisión e invalida preview; si confirma, el siguiente escritor encuentra bloqueo de estado. Lecturas viejas no generan snapshots nuevos. Resultado playoff y avance comparten también la transacción del evento; final y campeón se actualizan juntos.

Tras timeout de guardar ronda: mantener formulario sin afirmar éxito, GET canónico; si los marcadores guardados coinciden exactamente, adoptar revisión y estado guardado; si difieren, mostrar comparación/conflicto. No reintento automático que sobrescriba a otro admin. Error 401 sigue el mecanismo actual de sesión; no exponer datos a visitante para recuperar una edición.

**Alternativa:** solo revisión optimista requiere CAS y mucho cuidado con lecturas de hijos; solo locks no detectan formularios viejos. Se eligen lock corto + revisión para simplificar la carrera, a costa de serializar escrituras de un evento. PostgreSQL es la evidencia necesaria para locks; SQLite no prueba esa garantía.

### D6. Empates relevantes, snapshots y cuadro aprobado

Una zona con cupo q consume las posiciones 1..q como seeds. Para cada bloque empatado que interseque ese rango, pedir pareja para cada posición relevante si hay más de una candidata posible; la selección puede incluir parejas que ocupaban visualmente posiciones fuera del cupo dentro del mismo bloque. Rechazar duplicados, candidatos ajenos y slots no pertinentes. No pedir ordenar plazas >q. Guardar selección estructurada de IDs, no texto ni moneda generada por software.

Editar un marcador efectivo elimina todas las resoluciones de ese evento (invalidación conservadora y sencilla) y cambia `groups_revision`; aunque el mismo empate persista, se requiere revisar otra vez. Guardar una resolución cambia `revision`, no `groups_revision`. Preview incluye ambas, bloques y faltantes. Confirmación recalcula todo y verifica ambas; las resoluciones se aceptan solo para su `source_groups_revision`.

Cruces aprobados: semifinales directas A1-B2/B1-A2; una zona 1-4/2-3, sin cambios. **Cuartos/final aprobados el2026-10-21**: cuartos una zona Q1=1-8, Q2=4-5, Q3=2-7, Q4=3-6; dos zonas Q1=A1-B4, Q2=B2-A3, Q3=B1-A4, Q4=A2-B3. Q1/Q2→S1 lados a/b, Q3/Q4→S2 lados a/b; S1/S2→final lados a/b. Final directa: 1-2 o A1-B1. Evita revancha intrazona en cuartos y separa A1/A2, B1/B2 y A1/B1 en mitades opuestas. La preview muestra parejas y destinos antes de congelar. Las seis plantillas actuales son `approved`, con etiquetas/fixtures publicados y alineados; `proposed` permanece solo para futuras plantillas aún no aprobadas. Esto no implementa confirmación ni playoffs.

**Alternativa:** sortear todo el cuadro agrega reglas no aprobadas y no garantiza separación de favoritos; se recomienda seeding determinista y visible. La instantánea no se reordena por cambios posteriores porque no existen cambios de grupos tras el cierre.

### D7. API y frontend de escritorio

Prefijo backend `/admin/americanos`, siempre protegido; `{e}` es ID de evento. DTO cerrados a campos conocidos; nombres trim no vacíos; enteros estrictos excluyen booleanos/strings/float. Errores estructurados compatibles con `ApiError.body`: `code`, `message`, `current_revision?`, `fields?`. 401 sesión; 404 recurso anidado ajeno/inexistente; 422 payload/configuración inválidos; 409 revisión, fase, ronda bloqueada o conflicto destructivo. Ningún endpoint público nuevo.

| Método y ruta relativa | Contrato resumido |
|---|---|
| GET/POST `/` (sin slash final obligatorio) | Lista simple de eventos / crear borrador con nombre, zonas y etapa; devuelve ID, estado, revisión. |
| GET/PATCH `/{e}` | Resumen/continuación, contadores y configuración / editar campos de borrador con revisión. |
| POST `/{e}/registrations` | Agregar pareja propia en borrador con revisión. |
| PATCH/DELETE `/{e}/registrations/{id}` | Corregir/eliminar inscripción solo en borrador; IDs estables de las demás. |
| PUT `/{e}/zones` | `expected_revision`, `zone_count`, `zone_a_registration_ids`; para dos, complemento=B; para una, todas=A. |
| POST `/{e}/zones/randomize` | Reparto equilibrado aprobado, persistido/visible y retornado como EventDetail directo; solo borrador de dos zonas, implementado y aceptado3.2. |
| POST `/{e}/fixture` | Validar cupos y composición completa, generar y guardar fixture una sola vez, devolver ronda 1/continuación. |
| GET `/{e}/rounds/{number}` | Una ronda con partidos/zonas/descansos, `revision`, `saved`, `locked`, `total_rounds`, `max_unlocked_round`; no listado masivo para render. |
| PUT `/{e}/rounds/{number}/results` | `expected_revision`, lista exacta `{match_id,games_a,games_b}`; reemplazo completo, devuelve ronda, revisión y tabla actualizada. |
| GET `/{e}/standings` | Ambas zonas juntas, métricas exactas y bloques empatados; solo resultados guardados. |
| GET `/{e}/qualification` | Preview con revisiones, plazas/candidatas/faltantes y cruces; incompleta muestra motivo. |
| PUT `/{e}/tie-resolutions` | `expected_revision`, `source_groups_revision`, lista completa de plazas relevantes `{zone_id,position,registration_id}`; reemplazo atómico. |
| POST `/{e}/confirm-qualifiers` | Revisiones y `confirmation_key`; retorna cierre/cuadro canónicos. |
| GET `/{e}/playoffs` | Nodos por etapas, participantes, marcadores, campeón y revisión. |
| PUT `/{e}/playoffs/{node_id}/result` | Revisión, games y declaración `set_complete=true`, conforme D8; resultado y propagación juntos. |

GET de resultados sin cargar devuelve `null`, jamás `0` por defecto. PUT completo rechaza null/ausencia; frontend mantiene strings `''` o dígito y convierte solo al enviar, no usa `Number('')`. Un borrador recién creado puede no tener asignación completa; generar sí la exige. El cliente incluye el `expected_revision` actual en cada mutación.

Frontend propuesto:

| Ubicación | Responsabilidad |
|---|---|
| `src/api/americanos.ts`, `src/api/americano-types.ts` | Métodos/DTO propios mediante `api/client.ts`; no reutilizar contracts de liga. |
| `src/pages/americanos/AmericanosPage.tsx` | Lista de eventos, botón crear y estado vacío. Ruta `/admin/americanos`. |
| `.../AmericanoSetupPage.tsx` | Borrador, inscripciones y botones seleccionables con contadores A/B, cupos y preview. `/admin/americanos/:eventId/configuracion`. |
| `.../AmericanoRoundPage.tsx` | Orquesta carga y navegación de `/admin/americanos/:eventId/rondas/:roundNumber`; una ronda montada. |
| `.../AmericanoQualificationPage.tsx` | Candidatas reales por plaza, sorteo humano informado, advertencia/cierre. `/admin/americanos/:eventId/clasificados`. |
| `.../AmericanoPlayoffsPage.tsx` | Cuadro propio por etapa, set único, corrección permitida y campeón. `/admin/americanos/:eventId/playoffs`. |
| `src/components/americanos/ScoreRow.tsx`, `StandingsDrawer.tsx`, `QualificationSlots.tsx` | Presentación acotada; identidad estable por match ID; no lógica deportiva en componentes. |
| `src/pages/americanos/useRoundDraft.ts`, `useDirtyNavigation.ts` | Strings de edición, referencia a baseline, refs de foco, guard de navegación y reconciliación de revisión. |

En `/admin/americanos/:eventId`, resolver continuación desde estado servidor: draft → configuración; groups → primera no guardada; review → clasificados; playoffs/completed → cuadro. URL explícita de ronda ya desbloqueada se respeta; fallback a continuación segura. No guardar cada foco como estado servidor ni persistir nombres/marcadores en localStorage. Recargar con edición pendiente muestra advertencia nativa; si se abandona, se recupera solo lo guardado.

**Disponibilidad de consulta, no cambio de reglas:** App monta resolución canónica, setup y rondas con `mode="consultation"` bajo el guard admin existente. Review/historial ofrecen última ronda solo si `total_rounds` positivo coincide con `max_unlocked_round`; no ronda0. Clasificación/playoffs muestran etapa pendiente, sin APIs futuras. Setup inyecta diez métodos/round cuatro con `loadEvent` compartido;5.2/6.4 aceptadas,5.1 PARTIAL y UI editable/G2 pendientes. `read_only` de dominio no equivale a modo UI consulta. Contrato18 operaciones preservado; `/generate` no es endpoint publicado.

**Lenguaje visual:** puesto operativo sobrio, ancho dentro del Layout admin, jerarquía evento → ronda → filas; números tabulares y separación clara de zonas. Reutilizar tokens/tema/tipografía existentes, contraste y foco visibles; no incorporar fuentes, librerías ni rediseñar público. Cabecera con ronda n/N, estado guardado, anterior/siguiente, `Ver tablas` y acción primaria explícita. Cajón lateral superpuesto, no barra fija. No animaciones decorativas que retrasen carga.

**Foco:** orden estable por `display_order`, A/B. Autoavance solo ante transición vacío→dígito por entrada directa; sustituir un valor ya lleno, restaurar respuesta, cerrar cajón o reenfocar no dispara avance. Backspace/Delete vacían sin salto; Tab/Shift+Tab nativos. Pegar un único dígito válido funciona; pegar múltiples caracteres se rechaza. Completar último no envía formulario. Labels incluyen pareja, rival y zona. Errores enlazados con `aria-describedby`/`aria-invalid`, anuncio de guardado/error con región de estado. Drawer con diálogo etiquetado, trap de foco, Escape y restauración al campo previamente enfocado o al botón disparador si ya no existe. `Modal.tsx` actual no implementa trap/restauración: reutilizar apariencia, implementar esa conducta en el componente nuevo, sin asumirla existente.

**Guard real de navegación (hallazgo técnico; fuera del slice actual):** `useBlocker` necesita data router; no funciona en `BrowserRouter` declarativo actual. Propuesta futura: adaptación mecánica en `src/main.tsx` y `src/App.tsx` a `createBrowserRouter` + `createRoutesFromElements` + `RouterProvider`, conservando rutas, elementos y límites Theme/Auth/Admin tal como hoy. Añadir hook de bloqueo únicamente en formularios Americano dirty; `beforeunload` cubre recarga/salida de documento. Confirmación guardar/descartar/permanecer también para Back/Forward y enlaces admin; logout debe pasar por el mismo guard antes de ejecutar cierre de sesión. Validar URLs públicas y que no monten `AuthProvider` tras esta adaptación.

Fuente consultada: React Router 7.9.4 `useBlocker` (docs/código vía Context7); versión declarada del proyecto `^7.9.0`. **Alternativa:** interceptar clicks y `popstate` a mano mantiene el bootstrap, pero falla con historial/teclado o añade hacks; no se recomienda. La adaptación es un checkpoint MEDIUM con regresión de navegación, no cambio de autenticación ni de requisitos públicos.

Rendimiento: respuestas agregadas sin fetch por fila; tabla se actualiza desde respuesta de guardar o consulta al abrir cajón, no por cada tecla. Derivar dirty contra baseline sin efectos duplicados, estado de marcador local, referencias estables, no cálculos deportivos en renders. No agregar un store global, biblioteca de consultas ni memoización indiscriminada para hasta seis filas.

### D8. Set completo y correcciones aprobados

**Regla aprobada, completada el2026-10-21:** un set completo tradicional con tie-break, ganador por games, sin empate. Dos enteros estrictos no negativos, distintos, `set_complete=true` declarado por organizador y marcador terminal exacto válido; un marcador desigual por sí solo no demuestra finalización deportiva. No usar 0..9 de grupos ni arrays de sets.

**Terminales aprobados:** únicamente 6-0 a 6-4, 7-5 o 7-6 y simétricos. Rechazar 5-3, 6-5, empates y cualquier otro terminal. La alternativa de set largo por ventaja no fue elegida; no implementar prolongaciones ni selector.8.2 pura aceptada tras P2 resuelto:329 PASS del productor y exploración independiente874 estados/4980 operaciones legales/5312 rechazos por descendientes.8.3/resultados playoff no habilitados; reglas independientes de liga.

**Política de corrección aprobada:** permitir reemplazo de resultado solo si ningún descendiente tiene resultado; si cualquiera lo tiene, bloquear incluso correcciones que mantengan ganador. Así se evita destruir partidos jugados o reconstruir historia. Si cambia ganador y siguiente partido está pendiente, actualizar únicamente su lado; el otro lado se conserva. Un descendiente pendiente no tiene marcador parcial persistido. La final se puede corregir también después de completed porque no tiene descendientes; resultado y campeón cambian en la misma transacción, manteniendo completed y grupos cerrados. Sin borrado automático, eliminación de resultados ni reapertura de grupos.

Las alternativas de permitir correcciones con ganador igual pese a descendientes jugados o borrar en cascada no fueron elegidas y no forman parte de la aprobación.

### D9. Ejecución multiagente por contratos y archivos disjuntos

El usuario autorizó continuar y el trabajo paralelo previo; la entrega estable3.3 ya cuenta con revisiones independientes DOM y live. Se recomienda **3–5 escritores simultáneos como máximo**, más revisores de solo lectura para próximos slices autorizados. Olas expresan disponibilidad, no autorización futura. Este cierre de I solo integra los cinco docs principales y disponibilidad introductoria AE/AK, sin modificar implementación ni lanzar nuevos agentes.

#### Contrato inicial y gates

La tarea **0.1** ya fue aceptada: consolidó `contracts.md` dentro de este cambio y publicó el mínimo compartido `frontend/src/api/americano-types.ts` y fixtures deterministas de desarrollo en `frontend/src/pages/americanos/__fixtures__/scenarios.ts`. El checkpoint fijó los puntos siguientes; la aprobación posterior2.1.0 y el slice actual prevalecen sobre el alcance de ejecución general de este plan:

- DTO completos de solicitudes/respuestas D7, null frente a cero, unidades de puntos, IDs de evento y errores/status; `revision`, `groups_revision`, `source_groups_revision`, `expected_revision` y replay de `confirmation_key` sin ambigüedades.
- Firmas/tipos de funciones puras D4, forma de filas/bloques/seeds/nodos y claves de una plantilla de siembra explícita; estados/transiciones D3 y condiciones de continuación/bloqueo.
- Tipos frontend y fixtures de borrador, ronda vacía/0-0, seis filas, descansos, tablas empatadas, revisión, cierre y cuadro. Un adaptador en memoria de desarrollo puede consumirlos por inyección para preparar UI; no agrega un servicio ni una dependencia.
- Registro visible del estado humano de D3/D6/D8: estaban abiertas en G0 y fueron aprobadas posteriormente el2026-10-21. El constructor genérico sigue consumiendo plantilla explícita; el cierre real usa el seeding aprobado sin acreditar una capacidad implementada. Frontend ya publicó etiquetas/fixtures alineados; no queda esa decisión pendiente.

El mismo integrador congela esta versión y comunica el mapa de propiedad. No se exige completar todos los algoritmos antes de modelos, ni toda la API antes de UI. Cambiar un contrato pasa por el integrador: detener **solo los consumidores afectados**, acordar productor/tipos/fixtures, actualizar juntos, revalidar y publicar nueva versión antes de reanudar. Ningún worker decide silenciosamente una regla deportiva pendiente.

| Gate | Entrega verificable / responsables |
|---|---|
| G0 Contratos | 0.1 aceptada: DTO, firmas, estados, tipos y fixtures coherentes; integrador habilita carriles. |
| G1 Dominio + esquema | Salidas puras, modelos y DTO compatibles por subconjunto consumido; A/D/B entregan evidencia focalizada. Backend de borradores puede avanzar con modelos+DTO sin esperar el constructor de cuadro. DDL preparado sigue pendiente de autorización para ejecutarlo. |
| G2 Backend + UI tipada | Setup y ronda se conectan a `api/americanos.ts` real; I/B/U/R comprueban shapes, errores, revisiones, guard y red perdida. Una pantalla con mocks no satisface integración ni completa su checkbox. |
| G3 Confirmación + cuadro | Constructor8.1, clasificación, snapshot y confirmación conectados;7.2 entrega también GET privado del cuadro y U entrega la parte read-only de8.4 para que7.4 abra un destino real. Seeding aprobado aplicado y evidencia de atomicidad/bloqueo/replay/carrera. No espera validador8.2 de set ni PUT8.3; resultados playoff sí los requieren.8.4 completa su checkbox solo tras su segunda entrega live de resultados. |
| G4 Privacidad + regresión | Revisiones independientes de invariantes y UI/privacidad, evidencias integradas y checklist aceptado por I; auth CRITICAL y migración HIGH conservan sus checkpoints. |

#### Carriles y propiedad exclusiva de archivos

I=integrador/contratos; A=algoritmos; D=datos/migración; B=backend/API; U=setup/revisión/cuadro UI; R=puesto de ronda. I puede coordinar sin escribir mientras hay cinco escritores activos. No se crean más capas ni se divide `service.py` por paralelismo: **un solo B** escribe todos los servicios y routers nuevos, secuencialmente por capacidades.

| Propietario | Archivos reservados durante apply |
|---|---|
| I | Artefactos del cambio, incluido checklist y futuro `contracts.md`; `frontend/src/api/americano-types.ts`, `api/americanos.ts`, `api/client.ts` si hiciera falta; `src/App.tsx`, `src/main.tsx`, `components/Layout.tsx`, `pages/americanos/useDirtyNavigation.ts`, `pages/americanos/__fixtures__/scenarios.ts`; inicialización compartida de paquetes y `backend/tests/conftest.py` si fueran necesarios. El cliente base no requiere cambio previsto. |
| A | `backend/src/app/americanos/{fixture,standings,qualification,bracket}.py`; `backend/tests/test_americano_{fixture,standings,qualification,bracket,knockout_rules}.py`. Constructor8.1 y reglas8.2 se editan en distinto momento por el mismo dueño. |
| D | `backend/src/app/americanos/models.py`, `backend/src/app/database/session.py`, `backend/migrations/env.py`, la única revisión nueva en `backend/migrations/versions/`; `backend/tests/test_americano_models.py`. Único dueño de la cadena/head de migración. |
| B | `backend/src/app/americanos/{schemas,service,router}.py`, `backend/src/app/main.py`; `backend/tests/test_americano_{schemas,events,rounds,qualification_api,confirmation,knockouts,privacy}.py`. Tests API de clasificación separados de los puros de A. |
| U | `frontend/src/pages/americanos/{AmericanosPage,AmericanoSetupPage,AmericanoQualificationPage,AmericanoPlayoffsPage}.tsx`, `frontend/src/components/americanos/QualificationSlots.tsx`. |
| R | `frontend/src/pages/americanos/AmericanoRoundPage.tsx`, `useRoundDraft.ts`; `frontend/src/components/americanos/{ScoreRow,StandingsDrawer}.tsx`. |
| Revisores DOM / PRIV | Solo lectura: DOM revisa algoritmos/tabla/siembra/atomicidad; PRIV revisa protección API, aislamiento, rutas públicas, teclado/foco y navegación. Emiten hallazgos al integrador; el dueño del archivo aplica la corrección. |

Las filas son reservas de **archivo completo**, no de funciones. No hay dos workers sobre `service.py`, `router.py`, `schemas.py`, tipos/cliente compartido, `App.tsx`, `main.tsx` o `Layout.tsx`, aunque sus funciones sean distintas. Cambios fuera de la reserva se solicitan a I; transferencia solo explícita, con dueño anterior detenido y entrega confirmada. I es el único editor del checklist y registra aceptación real, no progreso supuesto por mocks.

#### Preparación UI, integración y seguridad del workspace

U y R empiezan tras G0 con props/callbacks tipados y fixtures deterministas, sin imports faltantes de implementaciones en curso ni suposiciones nuevas sobre reglas. I conecta el cliente/rutas en su carril; los componentes se conectan después a la API real por sus dueños. Fixtures/adaptadores se usan solo en un harness de desarrollo aislado; no se importan desde rutas públicas ni del entrypoint de producción, no actúan como fallback ante errores de red y no se incluyen en la entrega productiva. GET/PUT reales y revisiones deben verificarse en G2/G3; UI preparada no equivale a tarea aceptada.

- Workspace compartido por defecto: asignaciones disjuntas verificadas antes de cada ola y al entregar. Ante edición inesperada en una reserva, detener ese carril y escalar a I; no sobrescribir ni revertir trabajo ajeno.
- Workers no ejecutan git para administrar trabajo de otros; no stash/reset/clean/commit automáticos ni operaciones de integración sobre cambios ajenos. Worktrees solo si son provistos o aprobados; no asumir aislamiento por usar varios agentes. La integración descrita son entregas coordinadas del workspace, no merges/commits automáticos.
- Un único D prepara la migración y revisa head. Ningún worker la ejecuta, ahora ni durante apply sin la autorización adicional requerida. Paralelismo no autoriza mutaciones protegidas, rediseño auth ni aplicación a datos de usuario.
- TDD backend focalizado por carril cuando exista runner. Para ejecución concurrente futura, cada proceso usa BD descartable propia (incluido `TEST_DATABASE_URL`/esquema), directorio temporal y recursos/puertos de browser/server exclusivos. `conftest` hace drop_all: nunca compartir BD entre procesos de pytest. Si no hay BDs PostgreSQL independientes, serializar los ensayos de integración bajo I; una prueba de carrera puede usar dos sesiones dentro de **un** runner aislado. No confundir ese caso con dos runners que se destruyen el esquema.
- Revisores independientes pueden correr en paralelo sobre una entrega identificada y estable, sin editar ni lanzar suites contra recursos de otro. Un cambio posterior en el área revisada invalida esa aceptación específica. No hay tests en esta planificación y nunca build; el presupuesto extra se aplica a trabajo útil y revisión, no a ampliar alcance.

**Camino crítico cualitativo:** G0 → modelos/DTO compatibles + fixture → API de fixture/rondas → clasificación/confirmación + constructor → integración live de cierre/playoffs → G4. UI de setup/rondas y constructor avanzan en paralelo. Cuellos de botella deliberados: B único para servicio/router/schemas, I único para tipos/cliente/rutas/guards, decisiones deportivas localizadas y disponibilidad de PostgreSQL aislado. Validador8.2 depende de convención de set/corrección, pero no bloquea fixture, grupos ni constructor. No se proponen tiempos ni porcentajes de aceleración.

## Risks / Trade-offs

| Riesgo / nivel | Tratamiento propuesto |
|---|---|
| Filtrar datos por GET o mezclar liga — **CRITICAL** | Dependencia a nivel router, DTO propios, FKs/event scopes y pruebas negativas de todos los métodos; ninguna consulta pública a tablas nuevas. Revisar protección antes de aplicar; ningún rediseño auth. |
| DDL y datos activos — **HIGH** | Migración solo aditiva revisada; no autogenerate ciego ni ejecución actual. Ventana y autorización explícitas antes de aplicar. |
| Carrera score/confirm y escrituras viejas — **MEDIUM** | Lock de evento + revisión, commit único y snapshot recalculado; prueba PostgreSQL descartable. |
| Bootstrap de router para guard — **MEDIUM** | Adaptación mecánica con checkpoint y smoke de cada URL pública/admin; preservar proveedores y evitar auth fetch público. |
| Calendario más largo con >6 cruces lógicos — **MEDIUM** | Split determinista con descansos explícitos; no prometer mínima cantidad de rondas. |
| Dos administradores en distintos partidos — **MEDIUM** | Revisión global puede rechazar ediciones independientes; mensaje y recarga/comparación, aceptable para MVP. |
| Sorteo humano queda obsoleto — **MEDIUM** | Invalida todas las resoluciones al cambiar scores; tarea humana adicional preferible a clasificación silenciosamente errónea. |
| Desalineación entre aprobación deportiva y capacidades disponibles — **MEDIUM** | Backend3.1–4.3 aceptado, API13 y puertos setup10/round4 con loadEvent compartido; consulta real montada. UI editable/guard global5.3 y cinco APIs de clasificación/playoffs pendientes;8.2 pura no acredita campeón persistido. |
| Respuesta de red perdida o sesión vencida | Mantener edición en memoria mientras esté montada, no desbloquear por optimismo; GET autenticado para reconciliar; guard antes de salida voluntaria. |
| Colisiones de archivos, contratos divergentes o teardown de BD entre agentes — **MEDIUM** | G0, dueño único por archivo, pausa/escalamiento de consumidores afectados y recursos descartables por runner; si no hay aislamiento, serializar verificación. Hasta cinco escritores, sin refactor de arquitectura por paralelismo. |

## Migration Plan

Plan solamente; ninguna de estas acciones se ejecuta ahora.

1. Revisar modelos propios, constraints e índices contra D3/D6/D8 aprobados. Inspeccionar cadena existente en `backend/migrations/versions/` para identificar head real al implementar ese slice, sin asumir que el nombre de archivo indica orden. El slice draft ya registra metadata indirectamente por imports, sin DDL; modificaciones de imports en env/session y ejecución de migraciones siguen fuera de esta aceptación.
2. Preparar una revisión Alembic **aditiva**, con `upgrade` que crea solo `americano_*` y `downgrade` que elimina solo esos objetos en orden inverso. Registrar modelos en `migrations/env.py` y `database/session.py`.
3. Evitar autogeneración destructiva: `env.py` hoy no importa todos los módulos que sí importa `create_db_and_tables` (por ejemplo playoffs); un diff automático puede sugerir drops ajenos. Escribir/revisar la migración explícita y rechazar cualquier alter/drop de liga. No corregir el entorno completo como refactor lateral en este cambio.
4. Validar más adelante en una BD PostgreSQL descartable el upgrade desde el esquema vigente, conservación de filas de liga, FK/uniques y downgrade/reupgrade de los objetos nuevos. Esto exige autorización para ejecutar migraciones de prueba; nunca usar la BD activa ni `TEST_DATABASE_URL` apuntando a datos reales.
5. Antes de aplicar a datos de usuario: checkpoint HIGH, respaldo verificado y ventana acordada. Desplegar esquema aditivo, backend protegido y después frontend. No ejecutar push automáticamente: `README.md:26-34` documenta redespliegue automático de `main`.
6. Recuperación operativa preferida: retirar enlace/ruta nueva o volver a versión anterior de aplicación conservando tablas para no perder eventos. Bajar esquema en datos reales destruiría historial de Americano y requiere autorización separada; no es rollback automático. La liga permanece ajena a estos objetos.

## Verification Plan

Durante implementación, TDD focalizado donde ya existe runner: primero casos fallando para conducta nueva del slice, luego implementación y evidencia mínima pertinente. No ejecutar la suite entera por cada tarea; agrupar verificaciones por unidad y ampliar ante fallos o integración compartida. Esta acción de propuesta no ejecuta tests, builds ni migraciones.

| Evidencia futura | Casos esenciales |
|---|---|
| `tests/test_americano_fixture.py` | 8 una zona=28/7, 7+7=42/7, 16 una zona split6+2, impares/desiguales 5+4, zona unipersonal, todos los pares una vez, ausencia de doble participación y límite global6. |
| `tests/test_americano_standings.py`, `test_americano_qualification.py` (puros, A), `test_americano_qualification_api.py` (API, B) | Victoria/empate0-0, unidades exactas, diferencia, sin desempates heredados, 2/3+ empatadas en corte y siembra, empate irrelevante, resolución inválida y obsoleta. Archivos distintos evitan colisiones entre carriles. |
| `tests/test_americano_rounds.py` | Cero vs null/vacío, strict bool/decimal, lista exacta, rollback de ronda completa, desbloqueo secuencial, edición anterior y revisión conflictiva. |
| `tests/test_americano_confirmation.py` | Todo o nada, replay/duplicado, congelación backend y carrera corrección/cierre bajo PostgreSQL real descartable con sesiones distintas. No afirmar lock probado solo con SQLite. |
| `tests/test_americano_bracket.py`, `test_americano_knockout_rules.py` (puros, A), `test_americano_knockouts.py` (API, B) | Cuadros7/3/1 y semillas/destinos verificables antes del validador; set completo según convención aceptada, empate/incompleto, avance atómico, campeón y correcciones/descendientes. |
| `tests/test_americano_privacy.py` + regresión existente | Todos los endpoints sin sesión/inactiva=401, cruce E1/E2, ninguna fuga pública; `test_results.py`, `test_standings.py`, `test_playoffs.py`, `test_public.py` y auth pertinente una vez al integrar. |
| Frontend manual/browser focalizado | Escritorio ancho; flujo borrador→fixture→ronda→cajón→revisión→cuadro; teclado y foco, último campo no guarda, red perdida, Back/Forward/refresh, navegación dirty, sesión y rutas públicas intactas. `frontend/package.json` no ofrece runner: acordar incorporación antes de automatizar, sin inventar suite ni instalar ahora. |

## Open Questions

**No quedan reglas deportivas pendientes en D3/D6/D8** tras la aprobación del2026-10-21. No se reabre la entrevista ni se agregan alternativas.

1. **14/31 aceptadas,17 pendientes:** nuevas4.2/4.3/5.2/6.4; API13, setup diez/round cuatro con `loadEvent` compartido, cinco futuras.4.3 FULL PASS con PostgreSQL independiente;5.1 PARTIAL. Estrategia `auto-chain`/`stacked-to-main` solo planificación, sin GitOps; todo PR requiere pedido explícito.
2. Próximo proponer5.3: adaptación router/guard global dirty/logout voluntario (D7), con **confirmación humana antes de escrituras adyacentes a auth**. UI editable sigue deshabilitada; sin cambios previstos de login/cookies/permisos.
3. **Pendientes:**2.x/5.3/6.1–6.3/9.x/G2/G3/G4; campeón persistido8.3 y activación productiva separados. Notas compactas y evidencia externa, sin artefactos runtime/logs en código productivo; conservar tests significativos. Trabajo nuevo **sin commit** tras `2bc5abf`.
