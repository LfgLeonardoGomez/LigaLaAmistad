# Evidencia acotada: correcciones autorizadas de admin-americanos

**Estado vigente:5/31 aceptadas (0.1,3.1,3.2,8.1 y8.2),26 pendientes.** [Cierre actual: reglas puras8.2](#cierre-actual--reglas-puras82). P2 resuelto y revisión independiente PASS;8.2 solo pura, no estado DB/campeón persistido ni API playoffs.1.x/2.x sin aceptación dedicada;5.1/5.2 PARTIAL;9.x/G2/G3/G4 incompletos. Los tres cierres inferiores son históricos: conteos y P2 abierto conservan su procedencia temporal.

## Registro histórico — correcciones v2.0.0

El registro siguiente conserva sus conteos y límites originales. El cierre posterior del slice2.1.0 y el checklist actual figuran en la sección nueva al final; no se atribuye evidencia nueva al lote histórico.

**Resultado del lote: PASS sin bloqueantes en la revisión estática independiente informada por coordinación.** Este registro documenta únicamente las correcciones aprobadas por el usuario: UUID canónica, reconciliación de ronda, descriptor de navegación, foco del cajón y nombres accesibles. No acepta el cambio completo ni su integración productiva. Checklist conservado en **1/31**; todo el trabajo sin integrar sigue pendiente.

## Alcance y archivos del lote aprobado

Los ocho archivos corregidos ya eran **untracked** antes de esta finalización; ese estado no significa que hayan sido creados aquí.

| Archivo | Corrección documentada |
|---|---|
| `backend/src/app/americanos/schemas.py` | Normalizar UUID con `str(UUID(value))`; identidad textual canónica. |
| `backend/tests/test_americano_schemas.py` | RED/GREEN y triangulación de representaciones UUID. |
| `frontend/src/api/americano-types.ts` | Contrato compartido v2: `pending`, descarte booleano, `zoneLabel`, `rebase`. |
| `frontend/src/pages/americanos/AmericanoRoundPage.tsx` | Comparación canónica, conservar edición, revisión y navegación local seguras. |
| `frontend/src/pages/americanos/useRoundDraft.ts` | Rebase de baseline/revisión conservando strings por identidad de partido. |
| `frontend/src/components/americanos/ScoreRow.tsx` | Nombre accesible con zona A/B real, pareja, rival y partido. |
| `frontend/src/components/americanos/StandingsDrawer.tsx` | Trap excluye tabIndex negativo; teclado y restauración de foco. |
| `openspec/changes/admin-americanos/contracts.md` | Publicar v2.0.0 y obligaciones de consumidores, sin cambiar shapes HTTP. |

Esta finalización modifica únicamente el docstring de `schemas.py` (versión compartida v2.0.0, transporte sin cambios), la referencia final obsoleta a contratos v1 en `contracts.md` y este registro nuevo. No modifica lógica, tests, modelos, rutas/auth, migraciones, configuración, paquetes ni casillas.

## Evidencia y procedencia

Los resultados históricos siguientes fueron suministrados por coordinación; esta pasada inspeccionó los artefactos existentes y repitió solamente schemas tras el cambio mecánico de docstring, además de validar OpenSpec y whitespace.

| Evidencia | Resultado y alcance |
|---|---|
| UUID: baseline → RED → GREEN → triangulación | **370 passed → 1 failed / 370 passed → 371 passed → 389 passed**. |
| Backend final del lote, seis archivos Americano | **694 passed en 11.38 s**; fixture, standings, qualification, bracket, models y schemas. No equivale a suite global/API. |
| Frontend final del lote | `npm --ignore-scripts run lint` → **exit 0**; script existente `tsc --noEmit`. |
| Browser final del lote | **14 tests Chromium, 35.621 s, OK**, componentes reales con operaciones in-memory. |
| Revisión estática independiente | **PASS, sin bloqueantes**, según handoff de coordinación. |
| Regresión histórica de liga/auth | **182 passed: SOLO REVISIÓN PREVIA**, no repetida tras estas correcciones acotadas. |
| Revalidación de esta finalización | Schemas **389 passed en 0.75 s** después del docstring; OpenSpec strict y whitespace: ver cierre inferior. |

Antes de corregir se observaron en la ejecución previa: botón «Conservar mi edición» ausente, descriptor `pending` undefined, trap hacia el destino incorrecto y nombre accesible con «zona 201» en vez de A/B. Se conserva esa procedencia: no se volvieron a ejecutar versiones anteriores aquí.

## Los 14 casos browser, agrupados

| Grupo | Comportamientos comprobados en el harness |
|---|---|
| Recuperación y persistencia (4) | **1.** Fallo de red → conservar ceros y reintentar explícitamente con revisión canónica. **2.** 409 repetido → rebase de revisiones 7/8, conservando edición por match_id pese a reordenar filas. **3.** Respuesta perdida con igualdad canónica → éxito incluso tras cierre de grupos/read-only, sin segundo PUT. **4.** Usar servidor tras fallo de primera escritura → restaurar blancos y no desbloquear siguiente ronda. |
| Comparación y baseline (5) | **5.** GET fallido y nueva edición → reconciliación pendiente aunque dirty=false, descarte/salida bloqueados hasta comprobar. **6.** read_only, locked, playoffs, cambio de participante o match_id → conservar bloqueado, usar servidor permitido. **7.** Blanco tras rebase → foco de faltante, ningún PUT parcial/automático, guardado completo explícito. **8.** Scores concurrentes → baseline actual distinto del original/local, descarte restaura servidor. **9.** Recheck fallido → no reutilizar comparación canónica anterior ni permitir descarte. |
| Descriptor y salida local (3) | **10.** PUT retenido → pending=true, descarte=false y beforeunload cancelable protegido; al terminar pending=false/descarte=true. **11.** Getter pending síncrono antes del render React, save resuelve true con dirty/pending=false. **12.** Navegación local durante comparación → guardar bloqueado; continuar solo tras descarte exitoso y baseline restaurado. |
| Accesibilidad y foco (2) | **13.** Cajón: Tab/Shift+Tab omiten tabIndex=-1, flechas cambian A/B, Escape restaura input previo y conserva strings. **14.** Labels incluyen pareja/rival, zona A/B y número de partido; no exponen IDs 201/202 como zona. |

Frontend no tiene runner de tests instalado/declarado en su paquete. Esta es aceptación browser con el harness de desarrollo Playwright existente y componentes reales; no una nueva suite de unit tests del repositorio. Los archivos temporales son:

```text
C:\Users\pocho\AppData\Local\Temp\opencode\corrections-browser.py
C:\Users\pocho\AppData\Local\Temp\opencode\corrections-harness.tsx
C:\Users\pocho\AppData\Local\Temp\opencode\corrections-server.mjs
C:\Users\pocho\AppData\Local\Temp\opencode\corrections.html
```

El driver temporal usa `unittest` para organizar la aceptación Playwright; no instala ni integra un runner frontend. Inyecta `AmericanoOperations` en memoria y aborta solicitudes `/admin/`; no verifica HTTP real.

## Comandos mínimos de reproducción (Bash, desde cada directorio indicado)

Backend completo del lote, desde `backend/` (registrado arriba; no repetido en esta finalización):

```bash
PYTHONPATH=src DATABASE_URL=sqlite:///:memory: TEST_DATABASE_URL=sqlite:///:memory: PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/Scripts/python.exe -m pytest --noconftest -p no:cacheprovider tests/test_americano_fixture.py tests/test_americano_standings.py tests/test_americano_qualification.py tests/test_americano_bracket.py tests/test_americano_models.py tests/test_americano_schemas.py -q
```

Se usa el venv existente. Ambas URLs SQLite en memoria y `--noconftest` evitan heredar una BD de usuario y cargar el conftest raíz con creación/borrado de tablas. Autoload de plugins y cacheprovider desactivados; models posee conexiones SQLite privadas, no prueba locks PostgreSQL. Revalidación ejecutada aquí, desde `backend/`:

```bash
PYTHONPATH=src DATABASE_URL=sqlite:///:memory: TEST_DATABASE_URL=sqlite:///:memory: PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/Scripts/python.exe -m pytest --noconftest -p no:cacheprovider tests/test_americano_schemas.py -q
```

Frontend desde `frontend/`; OpenSpec desde la raíz (solo OpenSpec se repite aquí):

```bash
npm --ignore-scripts run lint
openspec validate admin-americanos --strict --type change --no-interactive --json
```

## Límites y cierre

Contrato **v2.0.0**: `pending` es getter vivo de operación/reconciliación, no snapshot; el futuro guard debe bloquear con `dirty || pending`, esperar guardado exitoso y respetar `discard():boolean` (**false cancela salida**). No hay guard global implementado por este lote. Shapes de transporte preservados; D3/D6/D8 siguen pendientes en sus puntos abiertos, sin alterar las semifinales ya aprobadas.

No hay aceptación PostgreSQL/locks, HTTP real, rutas globales del browser, logout, cookies ni cierre real de pestañas; despachar un evento cancelable beforeunload solo verifica el handler local. No se ejecutaron migraciones, builds, instalaciones ni commits en esta finalización. La integración y el resto de tareas permanecen abiertos; este PASS acotado no los completa.

Cierre de esta pasada: **schemas 389/389**, **OpenSpec strict valid=true, 0 issues, exit 0** y **whitespace sin errores** en los tres archivos mediante `git diff --no-index --check -- /dev/null <archivo>` (solo aviso de normalización LF→CRLF). `tasks.md` permanece intacto, con 1/31 casillas marcadas.

<a id="cierre-actual--slice-draft-v210-2026-10-21"></a>

## Registro histórico — cierre slice draft v2.1.0 (2026-10-21)

Este cierre precede a3.2/8.1. Sus menciones de «actual»,2/31 y zonas no disponibles describen ese momento, no el estado vigente. Se conserva el ancla anterior para referencias externas; el cierre vigente está al final.

**Coordinación acepta exclusivamente3.1 tras revisión independiente backend/frontend PASS y runtime real PASS.** Checklist actual: **2/31 aceptadas (0.1 y3.1),29 pendientes**;5.1/5.2 siguen PARTIAL, sin aceptar. G2/G3/G4 no están completos. Este cierre registra evidencia del slice actual, distinta de la revisión histórica anterior; esta pasada documental no repite suites ni servidores.

### Evidencia y procedencia del slice

| Evidencia | Resultado y alcance |
|---|---|
| Backend3.1-A/B/C | `service.py`, `router.py`, registro en `main.py`; fixtures/tests `backend/tests/{americano_fixtures,test_americano_events,test_americano_privacy}.py`. Exactamente siete operaciones privadas; reusa `get_current_admin` sin cambios. |
| API independiente | **131 passed,15.69 s**. Errores planos locales, IDs estrictos, historial consultable, mutaciones solo draft con revisión, intención de lock y commit único/rollback, cambio2→1 seguro y recurso anidado ajeno404 antes de revisar fase/revisión. Sin mutaciones de liga. |
| Base backend, proceso separado del productor | **694 passed** en seis archivos fixture/standings/qualification/bracket/models/schemas; no son131 pruebas API ni evidencia PostgreSQL. |
| Regresión legacy del productor, en este slice | **182 passed,169.93 s**, con **3 casos externos Cloudinary excluidos**. No confundir con los182 de la revisión histórica. |
| Frontend inicial del slice | Productor: **17 casos browser con HTTP mock** y **14 de ronda**; no prueban API real. |
| Correcciones frontend del slice | Revisión independiente detectó P2 recarga que perdía propuesta y P2 merge parcial de configuración. Dueño corrigió solo `AmericanoSetupPage.tsx`; revisión estática final **PASS**, ambos resueltos. Backend estático **PASS**, sin bloqueantes. |
| Frontend final independiente | **29 casos browser mock PASS,59.40 s**, tipos PASS. Los14 de ronda pasaron antes del último merge parcial, que solo modificó SetupPage; no se presentan como repetidos después de ese cambio. |
| App real→proxy Vite→FastAPI→SQLite nuevo | Independiente: **20/20 checks PASS**, **151 respuestas HTTP reales**,0 errores JS y0 excepciones backend. Login administrativo real y guard real; únicamente `get_session` reemplazado por sesiones aisladas. |
| Privacidad y persistencia live | Siete operaciones anónimas401; referencias ajenas404; historial solo lectura y escritura409; CRUD con revisiones/persistencia; públicos sin llamadas auth/Americanos y snapshots HTTP/filas de liga idénticos antes/después. |
| Conflictos y red live |409 reales, un GET abortado como fallo de red (sin HTTP200 simulado), propuesta conservada durante/después de recargar, keep/discard explícitos y merge canónico por campo para cambios aislados de nombre/zona/etapa. Ninguna adopción reenvía escritura. |

### TDD acotado, según entregas de los dueños

No se afirma que cada test actual haya sido escrito en una única fase RED ni que todo fallo fuera de producto.

| Entrega | Secuencia informada |
|---|---|
|3.1-A | Baseline174 antes de editar main; RED25 por rutas ausentes → GREEN25. |
|3.1-B | RED19 fallos/27 passed → GREEN46. |
|3.1-C, alta | RED13 fallos/46 passed → GREEN59. |
|3.1-C, edición/baja | RED38 fallos/63 passed;3 fallos correspondían a precondiciones de fixtures y se corrigieron como tales → GREEN101 →116 →131. |
| IDs de path y refactor | RED5 casos focalizados → corrección; refactor con131 verdes. |
| Setup, recuperación | Browser RED previo al primer fix:10 fallos conductuales +1 timeout de infraestructura →25 verdes; luego4 fallos de campos parciales →29 verdes. |

### Evidencia live recuperable y límites

Directorio: `C:\Users\pocho\AppData\Local\Temp\opencode\independent-live-dmryrqud\`:

| Artefacto | Uso |
|---|---|
| `result.json`, `browser-evidence.json` |20 checks, respuestas/navegador y cierre de procesos. |
| `backend-http.jsonl`, logs del directorio | Tráfico real y diagnóstico backend/frontend; no respuestas exitosas fabricadas. |
| `db-guard.json` | SQLite nuevo descartable, URL global en memoria, FK activas, chequeo FK vacío y override exclusivo de `get_session`. |

Puertos53221/53222 cerrados según `result.json`;5197 cerrado según cierre de coordinación. Los resultados de suites/revisiones son suministrados por coordinación; esta pasada inspeccionó código y evidencia live, sin volver a ejecutarlos.

- `main→router→service→models` registra las ocho tablas `americano_*` en metadata compartida por import, **sin DDL al iniciar**. No se editaron los imports de `migrations/env.py` ni `database/session.py`. No afirmar ausencia de efecto en metadata.
- Las tablas/filas de fixtures se crearon únicamente en SQLite nuevo y descartable. Sin BD de usuario, seeds operativos, cambios de auth/login, aplicación de migraciones, build, instalación, commit ni PR. **Activación del esquema productivo pendiente de autorización separada.** SQLite no acredita locks PostgreSQL.
- Cliente draft, puertos/rutas/menú y setup están conectados para ese subconjunto. Zonas/random/fixture conservan gate runtime; historial es setup persistido de solo lectura. Guard global/logout y rutas operativas de ronda/clasificación/playoffs siguen ausentes intencionalmente.
- D3/D6/D8 y las seis plantillas/etiquetas actuales de fixtures están aprobados y alineados; `DecisionStatus.proposed` se conserva solo para futuras plantillas. No quedan decisiones deportivas abiertas;3.2/3.3 y las demás capacidades siguen por implementar/aceptar.
- Siguiente corte funcional:3.2, reparto manual/random persistido y visible con revisión;3.3 será otro gate de generación/congelación.5.1/5.2 no se aceptan hasta completar sus criterios; esta aceptación no cierra el cambio completo.

Validación documental ejecutada tras estas ediciones: `openspec validate admin-americanos --strict --type change --no-interactive --json` → **valid=true,0 issues,exit0**; `openspec list --json` → **completedTasks=2,totalTasks=31,status=in-progress**; `openspec status --change admin-americanos --json` → **spec-driven, cuatro artefactos done**. El `isComplete=true` de status describe solo artefactos de planificación, no implementación ni G2/G3/G4. Se repite strict tras añadir este registro, sin suites de aplicación.

<a id="cierre-actual--zonas32-y-constructor81-2026-10-21"></a>

## Registro histórico — zonas3.2 y constructor8.1 (2026-10-21)

Cierre intermedio4/31 anterior al fix/re-review8.2. Sus menciones de P2 abierto y aceptación pendiente son históricas; el cierre actual inferior registra su resolución. Se conserva el ancla anterior y no se reatribuye evidencia posterior.

**I acepta exclusivamente3.2 y8.1 en esta pasada:4/31 aceptadas (0.1,3.1,3.2,8.1),27 pendientes.8.2 NO aceptada.** El usuario autorizó continuar y trabajo paralelo de backend/frontend3.2 y puros8.1/8.2; I integra solo `tasks.md`, `contracts.md`, `design.md` y este registro. Transporte **2.1.0 sin cambios**: se actualiza estado de implementación, no versión API.5.1/5.2 siguen PARTIAL; los checks acotados no completan9.1/9.2/9.3 ni G2/G3/G4.

### Decisión y procedencia de evidencia

Suites y secuencias RED/GREEN suministradas por coordinación/los dueños; no se ejecutaron de nuevo aquí. I leyó `independent-review.md`, `audit-summary.json`, `result.json` y `session-summary.md` del directorio live inferior y contrastó cliente/rutas/gate de generación. Los totales de distintos momentos/alcances no se suman como una suite final.

| Entrega | Evidencia y decisión |
|---|---|
| Backend3.2 | Productor: cambios `service.py`, `router.py`, tests events/privacy; baseline131; RED manual1 y luego3 fallos/1 passed, random1, una zona2; GREEN211 API pertinentes. PUT `/{e}/zones` recibe `{expected_revision,zone_count,zone_a_registration_ids}`; POST `/{e}/zones/randomize` recibe `{expected_revision}`; ambos devuelven200 `EventDetail` directo. |
| Revisión dominio/API independiente | **481 passed en13.06 s** en events/privacy/bracket/knockout de esa revisión.3.2 PASS: pertenencia, revisión, intención de lock, commit único/rollback y persistencia; no prueba locks PostgreSQL. El total incluye reglas8.2 que luego tuvieron hallazgo P2, no acredita8.2. |
| Frontend3.2 productor | Solo `api/americanos.ts`, `pages/americanos/AmericanoRoutes.tsx`, `AmericanoSetupPage.tsx`. Baseline29 browser de fixtures + lint; RED conductual→37 GREEN; borde deseleccionar todas RED explícito→**40 PASS,106.679 s**; lint final PASS. Harness temporal `slice32-run.py` y asociados, no live ni runner instalado en repo. |
| Revisión live independiente | **PASS, sin hallazgos P0/P1/P2 de código3.2;20/20 checks** App real→Vite→FastAPI→SQLite NUEVO. **233 respuestas FastAPI:167×200,45×201,12×401,5×409,2×422,2×404;0 backend5xx y0 errores JS**.231 observadas por browser/contexto; otras dos confirmadas por servidor y luego descartadas deliberadamente. Lint/`tsc --noEmit` exit0. P3 documental sobre zonas resuelto en las cuatro reservas de este cierre. |
| Constructor puro8.1 | Validación de implementación existente, **sin cambios productivos ni RED retrospectivo**: baseline39→**45 PASS**, seis tests alineados a approved y casos proposed futuros agregados. D6 seis plantillas:7/3/1 nodos estables, IDs únicos, sin byes, destinos acíclicos. Revisión independiente acepta8.1 separada de8.2; no acredita snapshot/confirmación/API. |
| Reglas puras8.2 | Productor225 casos nuevos/270 combinados. **P2 independiente abierto:** falta consistencia del lado fuente; no ganador999 puede llegar a campeón y se acepta fuente winner ausente. Corrección en curso al integrar; no verificada/aceptada en esta pasada. Requiere entrega corregida y nueva revisión específica. |

### Cobertura live3.2 y límites de aceptación

| Comportamiento | Evidencia acotada |
|---|---|
| AE-04 manual/random/una zona |5+4 manual desigual;15→8+7 y14→7+7 aleatorios con membresía exacta estable al hard reload; A selección/B complemento; una zona exige todas, payload incompleto422 sin mutar. Sin asignar no se presenta falsamente como B antes de propuesta. |
| AE-05 en draft | Cupos4/2/1 por zona según etapa;1+8 guardable aun insuficiente. `can_generate` refleja elegibilidad; **generación no inyectada y deshabilitada incluso si true**, sin tráfico fixture. No resorteo DURANTE generar/congelación siguen pendientes3.3. |
| Conflictos/red | Guards locales entre edición de config/pareja/zona;409 real de escritor concurrente, GET abortado y propuesta retenida durante/después de recarga. Keep explícito fusiona campos intactos; zonas obsoletas requieren adoptar canónico, no trasplantar IDs. PUT200/POST201 realmente confirmados y luego respuesta perdida: GET/reconciliación explícita, sin reintento/duplicado automático. |
| Privacidad/historial |9 operaciones anónimas401, payload ajeno422, anidado ajeno404. Historial sembrado en BD aislada read-only y escrituras409, no generado por3.3.5 rutas públicas sin auth/Americanos; filas de liga y snapshots públicos idénticos antes/después. No repite matriz completa de sesión vencida/inactiva ni regresión pytest global. |

### Evidencia recuperable y aislamiento

Directorio: `C:\Users\pocho\AppData\Local\Temp\opencode\independent-live-xsjn2t31\`. `independent-review.md` contiene matriz/comandos/límites; `audit-summary.json` conteos/hash de seis fuentes estables durante el run y auditoría de procesos; `result.json` checks/cleanup; `session-summary.md` handoff. Tráfico detallado en `backend-http.jsonl`/`browser-evidence.json`, identidad en `db-guard.json` y comparación liga en `league-before.json`/`league-after.json`.

- URLs globales `DATABASE_URL`/`TEST_DATABASE_URL` en memoria, **0 conexiones al engine global**; override exclusivo `get_session`, login/guard reales, SQLite nuevo descartable, FK activas y `foreign_key_check=[]`. Sin BD de usuario, migraciones, build, instalación ni commits.
- Puertos57714/57715 y diagnósticos57674/57675 cerrados según auditoría; procesos propios ausentes. Intento inicial `independent-live-ngeyuesa` falló por expectativa del harness (consulta pública por defecto played frente a sentinel pending); se corrigió la consulta y pasó otro run con BD/puertos nuevos, sin corrección de producto ni ocultar el intento inicial.
- Metadata registra ocho tablas por import `main→router→service→models`, sin DDL de inicio; no se acredita PostgreSQL row-lock/concurrencia. Migración/activación productiva exige aprobación separada. Sin cambios auth ni5.3/guard global/nav/logout; guards locales no completan ese gate.

**Handoff:** siguiente slice funcional3.3, fixture atómico/congelación sin resorteo/regeneración, manteniendo generación deshabilitada hasta su entrega.8.2 continúa con corrección P2 y revisión independiente posterior; no aceptarla por conteos verdes previos. Hay resúmenes draft obsoletos en `proposal.md` y las introducciones de specs AE/AK, fuera de esta reserva; este cierre no los reescribe. Los requisitos normativos futuros siguen vigentes.

Validación documental ejecutada: `openspec validate admin-americanos --strict --type change --no-interactive --json` → **valid=true,0 issues,exit0**; `openspec list --json` → **completedTasks=4,totalTasks=31,status=in-progress**. Recuento directo del checklist:31 casillas,4 marcadas (0.1,3.1,3.2,8.1) y27 pendientes, sin nuevas tareas. `openspec status --change admin-americanos --json` → spec-driven/cuatro artefactos done; `isComplete=true` sigue describiendo planificación, no implementación. `git diff --no-index --check -- /dev/null <archivo>` en las cuatro reservas: sin errores de whitespace (solo aviso LF→CRLF); el primer control detectó un salto Markdown con dos espacios preexistente en tasks, normalizado antes del control final. Engram no expone herramientas ni recursos/templates MCP; se conserva este registro como handoff, sin simular guardado en memoria.

## Cierre actual — reglas puras8.2

**I acepta8.2 exclusivamente pura tras P2 corregido y revisión independiente PASS:5/31 aceptadas (0.1,3.1,3.2,8.1,8.2),26 pendientes.** Transporte2.1.0 sin cambios. La evidencia runtime siguiente fue suministrada por coordinación a partir de los informes del productor y del revisor independiente; esta pasada documental no la ejecuta de nuevo. I contrastó fuentes en `_index_bracket` y `_validate_participants` por lectura. No se aceptan1.1/1.2/1.3 ni2.x por suites verdes sin revisión dedicada;5.1/5.2 PARTIAL,9.x/G2/G3/G4 incompletos.

### Resolución P2 y revisión independiente final

| Evidencia suministrada | Resultado y alcance |
|---|---|
| Consistencia de fuentes | `_index_bracket`: tipo/stage/slot/existencia y reciprocidad de fuentes/destinos; `_validate_participants`: participantes derivados del ganador. Repro original de campeón999 no ganador rechazado con `invalid_configuration`, path `('nodes',2,'registration_a_id')`; fuente winner ausente y final truncada rechazadas.999 seed legítima aceptada, sin blacklist. |
| Exploración pura independiente sin archivos | Seis plantillas approved, **874 estados alcanzables**, **4980 guardados/correcciones legales aceptados**, **5312 intentos con descendiente jugado rechazados**; copysafe, otra rama preservada. No es una suite HTTP ni persistencia DB. |
| Productor final | **329 PASS =45 bracket+284 knockout**; los225 casos knockout originales llegaron a284 tras corrección/triangulación. Baseline histórico constructor39→45 por alineación de fixtures de plantillas, sin RED retrospectivo8.1. |
| Suite independiente final, nueve archivos Americano | **1194 passed,1 deselected,1 warning de dependencia existente,15.41 s**. Test de metadata separado por necesitar proceso fresco/imports app limpios: **1 passed,0.72 s**; total **1195 passed**, no fallo de test ni regresión global de liga. |
| Frontend sin cambios posteriores al live informado | Se conserva evidencia3.2: nueve métodos setup reales,20/20 live y typecheck PASS,233 respuestas FastAPI reales.40 browser del productor usan fixtures; no se reclasifican como HTTP real ni se presentan como repetidos aquí. |

### TDD Cycle Evidence

Fuente: secuencias del productor/coordination; números tras flecha son totales GREEN de ese momento, no suma de suites. No se inventa RED para validación existente ni se atribuye el fallo del harness público al producto.

| Task | TestFile | Layer | SafetyNet | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
|3.2 backend | `test_americano_events.py`, `test_americano_privacy.py` | API | Baseline131; sesiones/SQLite descartables | Manual1, luego3 fallos/1 passed; random1; una zona2 |211 API | Revisión independiente481 PASS y live20/20, distintos alcances | No secuencia adicional informada; no inventada |
|3.2 frontend | `slice32-run.py` y harness temporal asociado | Browser con fixtures | Baseline29 + lint | Conductual antes de37; deseleccionar todas RED explícito |37→40 PASS,106.679 s; lint PASS | Live independiente20/20 real separado | Sin cambio frontend posterior al live informado |
|8.1 validación | `test_americano_bracket.py` | Puro | Constructor existente39 PASS | **No aplicable; sin RED retrospectivo** |45 PASS tras alineación seis plantillas | Proposed futuro preservado; destinos/7-3-1/sin byes | Sin cambio productivo en entrega8.1 |
|8.2 inicial | `test_americano_knockout_rules.py` (+bracket) | Puro |45 bracket PASS |2;35;8 convención;2 propagación;5 participantes/final;10 descendientes;20 strict;6 malformed |47→82→211 (matriz121)→213→218→232→252→270 |264 antes de6 malformed |270 PASS antes del P2 independiente |
|8.2 fix P2 | `test_americano_knockout_rules.py` (+bracket) | Puro |270 PASS; repro independiente P2 |2→272;28→300;6→316;2→329 |329 =45+284 PASS |10 adicionales en316;327 antes del RED final; revisor874 estados/4980 legales/5312 rechazos |329 PASS tras refactor; revisión final PASS |

### Comandos del revisor, no ejecutados en esta pasada

Desde `backend/`, venv existente, bytecode/plugins/cache desactivados, ambas URLs en memoria y `--noconftest` para evitar teardown global. El test de metadata exige proceso nuevo sin imports app previos; se excluye de la primera invocación y se ejecuta solo en la segunda, **no por fallo**:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src DATABASE_URL=sqlite:///:memory: TEST_DATABASE_URL=sqlite:///:memory: PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/Scripts/python.exe -B -m pytest --noconftest -p no:cacheprovider tests/test_americano_events.py tests/test_americano_privacy.py tests/test_americano_bracket.py tests/test_americano_knockout_rules.py tests/test_americano_fixture.py tests/test_americano_standings.py tests/test_americano_qualification.py tests/test_americano_schemas.py tests/test_americano_models.py -k 'not test_only_eight_isolated_tables_and_no_league_foreign_keys' -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src DATABASE_URL=sqlite:///:memory: TEST_DATABASE_URL=sqlite:///:memory: PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/Scripts/python.exe -B -m pytest --noconftest -p no:cacheprovider tests/test_americano_models.py::test_only_eight_isolated_tables_and_no_league_foreign_keys -q
```

**Límites:**8.2 devuelve nodos/campeón calculados sin mutar entradas; estado completed/grupos cerrados y persistencia atómica de resultado+campeón pertenecen a8.3, sin API playoffs implementada. Generación3.3 no inyectada/deshabilitada incluso con `can_generate=true`; no hay prueba de no resorteo DURANTE generar ni congelación desde esa acción. Sin5.3/guard global/nav/logout ni cambios auth. PostgreSQL row locks, migración/activación productiva requieren evidencia/aprobación separadas. Las suites Americano no completan regresión de liga9.2 ni demás gates.

Validación documental final ejecutada: `openspec validate admin-americanos --strict --type change --no-interactive --json` → **valid=true,0 issues,exit0**; `openspec list --json` → **completedTasks=5,totalTasks=31,status=in-progress**. Recuento real:31 casillas,5 marcadas (0.1,3.1,3.2,8.1,8.2),26 pendientes, sin tareas nuevas. `openspec status --change admin-americanos --json` → spec-driven/cuatro artefactos done; `isComplete=true` describe planificación, no implementación ni G2/G3/G4. Whitespace de los siete docs mediante `git diff --no-index --check -- /dev/null <archivo>`: sin errores, solo aviso LF→CRLF. En esta pasada no se ejecutaron tests, servidores, builds, migraciones ni commits.

### Session handoff (Engram no disponible)

#### Goal
Continuar Americanos con trabajo paralelo: conectar zonas manuales/random de punta a punta, validar constructor8.1 e implementar reglas puras8.2; consolidar aceptación y evidencia en5/31.

#### Instructions
El usuario pidió continuar y avanzar tareas independientes en paralelo. Se separaron dueños backend, frontend y dominio puro, con TDD y revisión independiente. No construir, instalar dependencias, modificar auth, aplicar migraciones ni tocar BD de usuario. Los límites de solo Markdown y de no ejecutar pruebas/servidores corresponden exclusivamente a las pasadas documentales finales, no a los carriles de implementación y aceptación.

#### Discoveries
P2 de fuentes resuelto y re-review PASS; test de metadata necesita proceso fresco, no fue un fallo.8.2 no maneja estado DB/atomicidad de campeón.

#### Accomplished
Zonas3.2 backend/frontend conectadas y aceptadas tras20/20 controles live en BD descartable; constructor8.1 validado; reglas8.2 implementadas y P2 de fuentes corregido con RED/GREEN y re-review PASS. Verificación independiente1195 pruebas Americano aprobadas y typecheck PASS. Conteos/procedencia/TDD documentados; historia4/31/P2 abierto preservada; notas de disponibilidad proposal/specs actualizadas. CLI5/31/26 y strict0 issues; whitespace limpio.1.x/2.x sin aceptación dedicada,5.1/5.2 PARTIAL y9.x/G2/G3/G4 incompletos. Trabajo sin commit; generación sigue deshabilitada.

#### Next Steps
Slice futuro3.3: fixture atómico/congelación sin resorteo/regeneración, manteniendo generación deshabilitada hasta su entrega.8.3/confirmación/API playoffs y activación productiva con sus gates posteriores.

#### Relevant Files
`backend/src/app/americanos/service.py`/`router.py` — zonas persistidas; `bracket.py` — validación y propagación puras; `backend/tests/test_americano_events.py`/`test_americano_privacy.py`/`test_americano_bracket.py`/`test_americano_knockout_rules.py` — cobertura. `frontend/src/api/americanos.ts` y `frontend/src/pages/americanos/AmericanoRoutes.tsx`/`AmericanoSetupPage.tsx` — capacidades y setup real. `tasks.md` — aceptación/checklist; `contracts.md`/`design.md` — estado/límites; `proposal.md`/specs AE/AK — disponibilidad; `verification.md` — historia, evidencia y handoff persistido. No se afirma `mem_save` ni resumen Engram: herramientas de memoria ausentes.
