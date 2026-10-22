# Evidencia acotada: correcciones autorizadas de admin-americanos

## Aceptación vigente y handoff — 2026-10-22

**14/31 aceptadas,17 pendientes:**0.1,1.1,1.2,1.3,3.1,3.2,3.3,4.1,4.2,4.3,5.2,6.4,8.1,8.2. Nuevas exclusivamente4.2/4.3/5.2/6.4; contrato/DTO2.1.0 intacto.
5.1 PARTIAL;2.x/5.3/6.1–6.3/9.x/G2/G3/G4 pendientes. Las notas inferiores son históricas; prevalece este cierre. Evidencia suministrada por coordinación y contrastada con los dos informes externos siguientes, sin reejecutar runtime aquí.

- **4.2/4.3 FULL PASS:** reemplazo completo, rollback, revisiones, invalidación y review editable. P2 PostgreSQL de binding int32 corregido mediante pertenencia de payload por evento y guard de almacenamiento/404, conservando DTO JSON-safe;59 regresiones nuevas. Productor final899=510 API+389 schemas PASS; independiente previo577=451 API+126 puras y probes de guardado/auth son alcances distintos.
- **Retest PostgreSQL17.10 independiente** (`ses_e9b775bfdffe5gm9oYlDVEJ2zQ`):97 límites rechazados+dos positivos (incluido ID int32 MAX persistido),20 carreras/40 llamadas productivas, espera real en todas,20 éxitos/20 revision_conflict. Reintentos idénticos/obsoletos, ocho tablas y ledger independiente de standings/revisiones/invalidation PASS.
- El500 original fue inferido de una excepción real del servicio; tras el fix,422/404 medidos en servicio PostgreSQL y errores HTTP correctos en SQLite live. **No se midió HTTP PostgreSQL.** Contenedor efímero propio eliminado/puerto61425 cerrado; otros cinco contenedores intactos y89 hashes backend estables según informe.
- **Consulta frontend PASS:** P2 de frame diferido al volver de modo resuelto con epoch y recheck post-await; revisión independiente de componentes/probes PASS. P2 de enlace a ronda1 corregido a última canónica (`total_rounds` positivo igual a `max_unlocked_round`).
- Retest live **13 checks/268 HTTP reales**,0×5xx/0 errores JS:3 y7 rondas/review/historial cerrado, cero rondas, consulta sin PUT de UI forjada y foco/tablas. Los25 checks/453 HTTP iniciales **no se repitieron completos**; fixtures App y probes de componente son evidencia separada. Recursos propios cerrados (55058/55059),174 hashes estables y typecheck PASS según informe.
- **5.2 ACCEPT**, auditoría `ses_e9b192280ffektwYF4u5NQDUWL`: listado/CRUD/draft/nombres/parejas variables, zonas manual5+4/random par-impar persistido/cupos, estados/confirmación/congelación sin resorteo, primera ronda de consulta/1+1 review y red/409. PARTIAL antiguo por generación/continuación resuelto; dependencia por entregables5.1, sin exigir su checkbox ni guard global para setup.
- **6.4 ACCEPT**, auditoría `ses_e9b2eda88ffe8fi6Vr6rLPvcXl`: GET guardado/render real App→SQLite, A/B/columnas/empates/puntos, trap/Escape/restauración/URL y aviso de cambios sin guardar. Buffer editable strings0/9 preservado en browser de componente+flujo fuente, **no medido editable live**. Componentes existentes validados, sin RED retrospectivo; `read_only` de dominio ≠ modo consulta UI.

**Pruebas externas:** base `C:/Users/pocho/AppData/Local/Temp/opencode/`: `pg43-retest-20261022-c83f71a9/verify-report.md` y `independent-live-42-k7p9-lrg6g96n/acceptance-summary.json`.
**Disponibilidad:**13 métodos reales; setup10/round4 comparten `loadEvent`, draft7; cinco futuros (GET qualification, PUT resoluciones, POST confirmación, GET/PUT playoffs). App monta rutas adicionales protegidas de consulta; wrappers/setup, RoundPage/hook/ScoreRow y puertos API integrados. Main/Layout/auth conservados; UI editable deshabilitada hasta aprobar5.3.
**Próximo paso:** proponer5.3 router/guard global dirty+logout voluntario, con **confirmación humana antes de escrituras adyacentes a auth**; sin cambios previstos de login/cookies/permisos. Esta pasada no implementa esa propuesta ni solicita aprobación por otro coordinador.
**Preferencia y límites:** notas compactas, evidencia runtime fuera de producción y tests significativos conservados; sin archivos/logs nuevos. Trabajo sin commit tras `2bc5abf`. Integración solo documental, sin source/tests/build/install/BD/servicios/migraciones/commit/push; activación productiva separada.
**Persistencia:** Engram sin herramientas disponibles; este handoff queda en los cinco docs principales y disponibilidad introductoria AE/AK, sin afirmar llamadas de memoria.
**Validación documental:** strict `valid=true,issues=[]`; CLI list14/31 `in-progress`, status4/4 artefactos `done` solo de planificación; checklist31 con las14 IDs exactas. Whitespace de siete docs PASS; specs AE/AK solo introducción. Los13 archivos source/tests previamente modificados y main/Layout conservaron sus hashes; estado Git previo preservado.

## Registro histórico — aceptación4.1 (2026-10-22)

**Estado vigente2026-10-22:10/31 aceptadas (0.1,1.1,1.2,1.3,3.1,3.2,3.3,4.1,8.1 y8.2),21 pendientes.** Solo se acepta4.1 backend reads en esta pasada; siguiente4.2, PUT de resultados ausente.5.1/5.2 PARTIAL;2.x/5.3/6.x/9.x/G2/G3/G4 pendientes; contrato2.1.0 sin cambios.
- DOM4.1 independiente PASS sin hallazgos accionables (`ses_e9f0f6b89ffeGHcMDuVK54npWt`): **421 passed,1 warning de dependencia existente,27.46 s**, runtime SQLite acotado; evidencia suministrada por coordinación, no reejecutada aquí.
- Probes sin archivos: ocho patrones de prefijo/24 lecturas y cuatro lecturas de17+4; solo ronda solicitada/desbloqueada, bloqueada sin consultar scores y descansos `bye`/`capacity`/`zone_finished` reales. Tablas solo con scores completos/guardados; revisiones y bloques empatados coherentes.
- PRIV estática PASS:12 operaciones con guard existente, paths/errores planos/aislamiento por evento y ronda; scores bloqueados sin fetch, público/auth preservados. Sin duplicar ejecución DB.
- Productor4.1 informó TDD focalizado, refactor350 API PASS y66 tests de rondas finales; corrección `populate_existing` en consultas hijas para revisión/scores/saved/nombres frescos. Slice: service/router, nuevo test_rounds y privacy; test_events pertenece al cambio previo3.3.
- API12 operaciones; cliente setup diez/draft siete, sin wiring de nuevos GET. Seis futuras: guardar ronda, GET qualification, PUT resoluciones, POST confirmación y GET/PUT playoffs. Frontend/routing/5.3/modelos/schemas/auth/session/metadata/migración sin cambios en4.1; nombres/configuración siguen congelados.
- **3.3 ya aceptada:** contención PostgreSQL previa con20 carreras, registrada en `tasks.md`; no es prueba PostgreSQL nueva de4.1. Los cierres inferiores son históricos, con su procedencia y límites originales.

## Registro histórico — correcciones v2.0.0

El registro siguiente conserva sus conteos y límites originales. El checklist vigente figura al inicio; no se atribuye evidencia nueva al lote histórico.

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

Este cierre precede a3.2/8.1. Sus menciones de «actual»,2/31 y zonas no disponibles describen ese momento, no el estado vigente. Se conserva el ancla anterior para referencias externas; el cierre vigente está al inicio.

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

<a id="cierre-actual--reglas-puras82"></a>

## Registro histórico — reglas puras8.2 (2026-10-21)

Checkpoint5/31 anterior a la auditoría dedicada1.1/1.2/1.3. Sus menciones de «actual», generación deshabilitada y1.x sin aceptación describen ese momento; las secciones posteriores registran aceptación pura8/31 y entrega3.3 funcional/PARTIAL. Se conserva el ancla anterior para enlaces existentes.

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

<a id="cierre-actual--nucleo-puro11-12-13"></a>

## Registro histórico — núcleo puro1.1/1.2/1.3 (2026-10-21)

Checkpoint8/31 anterior a la entrega/revisión estable3.3. Sus referencias a escritores en curso, generación deshabilitada y resúmenes5/31 pendientes de consolidación describen ese momento. El cierre actual inferior integra esa documentación y la nueva evidencia3.3 sin modificar esta aceptación pura ni marcar otra casilla; ancla preservada.

**I acepta exclusivamente1.1/1.2/1.3 puras:8/31 aceptadas (0.1,1.1,1.2,1.3,3.1,3.2,8.1,8.2),23 pendientes.** Auditoría dedicada independiente **PASS, sin defectos accionables**. Es validación de implementación existente, no desarrollo nuevo ni evidencia RED/TDD retrospectiva.3.3 sigue pendiente con escritores backend/frontend en curso;2.1/2.2/2.3 también pendientes.5.1/5.2 PARTIAL y9.x/G2/G3/G4 incompletos.

### Procedencia y snapshot

Fuente: **informe del revisor independiente `ses_e9edbb217ffeRSPAYeYjyF6Bti`, suministrado por coordinación**. Sus suites/probes fueron de solo lectura y no se repitieron en esta pasada documental. El revisor auditó `backend/src/app/americanos/{fixture,standings,qualification}.py` y sus tres tests dedicados, sin cambios respecto de `2bc5abf`. I confirmó por `git diff 2bc5abf -- <seis archivos>` que siguen idénticos y contrastó por lectura fuentes, D4, criterios AE/AQ y contrato §4.2.

La CLI inicial informó5/31 y cuatro artefactos de planificación completos; HEAD=`2bc5abf`. El workspace ya contenía cambios de otros escritores en `router.py`, `service.py`, `test_americano_events.py` y `test_americano_privacy.py`. Esta aceptación cubre los seis archivos puros estables, sin atribuir evidencia a la implementación3.3 en curso. Solo se editan `tasks.md` y este registro; no se crea commit ni se hace push.

### Matriz de aceptación pura

| Tarea / criterio | Decisión y evidencia dedicada del revisor |
|---|---|
|1.1 / AE-06/07, D4 | **PASS puro,39 tests**. Berger8→28 partidos/7 rondas;7+7→42/7;16→120 partidos/30 rondas reales,15 bloques lógicos6+2;5+4→16/5. Impares, vacíos y unipersonales; cada cruce una vez, ninguna doble participación, máximo6 global, sin empaquetar bloques lógicos distintos. Descansos `bye`/`capacity`/`zone_finished` correctos. Persistencia única/concurrencia y transición de estado siguen en3.3. |
|1.2 / AQ-01, D4 | **PASS puro,32 tests**. Unidades enteras2/1/0,0-0 válido, recálculo por reemplazo sin acumular, solo puntos y diferencia de games; sin sets/enfrentamiento/ID. Bloques de igual métrica; registration_order solo visual. Rechaza autorivales, referencias ajenas y partidos/cruces duplicados. Filtrado de resultados guardados e integración API no aceptados aquí. |
|1.3 / AE-05 y AQ-03/04, D4/D6 | **PASS puro,55 tests**. Seis configuraciones etapa/zonas y cupos1/2/4/8; empates2 y3+ relevantes de entrada/siembra, candidatos completos y sin fallback por orden visual. Rechaza selección ajena/fuera de bloque/duplicada/irrelevante; no exige resolver empates de no clasificadas sin efecto. Preview parcial válido con `missing_slots`; PUT completo, revisiones, invalidación y confirmación siguen en B/API. |

**Suite dedicada informada:126 passed,0.22 s,exit0 =39 fixture+32 standings+55 qualification.** Los probes siguientes son exploraciones independientes en memoria, sin archivos, y no se suman a esos126 tests ni a suites históricas.

| Probes independientes | Alcance y resultado informado |
|---|---|
| Fixture |65 tamaños0..64;2844 configuraciones: una zona0..32, dos zonas0..20 y capacidad1..6. Verificadas161319 rondas,367896 partidos y3333222 registros de descanso. |
| Standings |4913 combinaciones guardadas/omitidas de tres partidos;4913 en orden inverso;4912 reemplazos. Todos los100 scores0..9 y14 rechazos de entradas inválidas/incompletas. |
| Qualification |885 particiones de empates/cupos con n1..8;5671 selecciones individuales válidas;885 resoluciones completas en orden inverso;1420 asignaciones inyectivas exhaustivas con n<=6;6099 rechazos inválidos. |
| Compatibilidad |16 contratos de shapes congelados y los inventarios de seeds de las seis plantillas: PASS. No acredita cierre/API ni persistencia. |

### Comando del revisor — registrado, no ejecutado aquí

Desde `backend/`, venv existente y entorno aislado explícito; bytecode, autoload de plugins y cacheprovider desactivados; `--noconftest` evita el teardown global. Las URLs en memoria no constituyen evidencia PostgreSQL:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src DATABASE_URL=sqlite:///:memory: TEST_DATABASE_URL=sqlite:///:memory: PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/Scripts/python.exe -B -m pytest --noconftest -p no:cacheprovider tests/test_americano_fixture.py tests/test_americano_standings.py tests/test_americano_qualification.py -q
```

### Límites de integración y contrato vigente

- **1.2:** un `SavedScore` con null provoca `invalid_configuration`, no se ignora silenciosamente. Conforme a `contracts.md` §4.2 (línea327 del snapshot), **B debe filtrar entradas completas y guardadas antes de llamar**; los partidos omitidos no cuentan. Esta aceptación no prueba el filtrado API ni la visualización AQ-01.
- **1.3:** el cálculo puro admite selecciones parciales y expone faltantes; la exigencia de PUT completo, `source_groups_revision`, rechazo de revisión obsoleta e invalidación efectiva siguen pendientes de B/API. No se relajan AQ-03/04 ni los criterios normativos.
- **3.3:** en curso backend/frontend, sin aceptación live. El contrato sigue siendo **POST `/{e}/fixture` → `{event,first_round}`**, con `first_round=null` solo cuando no hay partidos. Coordinación informó que corrigió la instrucción parental errónea `/generate` a ambos escritores antes de integrar; no es un cambio de contrato ni una capacidad aceptada. El último live aceptado tenía generación deshabilitada incluso con `can_generate=true`; no se extrapola ese snapshot al código que aún se está escribiendo.
- **Fronteras restantes:** no se acredita atomicidad/rollback/congelación3.3, locks/concurrencia PostgreSQL, confirmación/API playoffs ni campeón persistido8.3. Sin cambios auth en esta pasada ni aceptación5.3. Migración/activación productiva requieren autorización separada. Los criterios normativos y las otras23 casillas pendientes conservan su alcance.

**Consolidación documental posterior:** `contracts.md` (introducción/cierre), `design.md` (introducción/notas finales), `proposal.md` e introducciones de specs AE/AK todavía muestran5/31 o1.x sin aceptación. Quedan señalados para consolidación final por su dueño; este cierre solo tiene propiedad de `tasks.md` y `verification.md`. El conteo vigente es8/31 y la evidencia5/31 anterior se conserva como historia fechada.

### Validación documental de esta pasada

Comprobaciones ejecutadas desde la raíz, después de actualizar la aceptación:

| Comando | Resultado |
|---|---|
| `openspec list --json` | **completedTasks=8,totalTasks=31,status=in-progress**;23 pendientes. |
| `openspec status --change admin-americanos --json` | spec-driven, cuatro artefactos `done`; `isComplete=true` corresponde a planificación, no a implementación ni G2/G3/G4. |
| `openspec validate admin-americanos --strict --type change --no-interactive --json` | **valid=true,issues=[],exit0**. |
| `git diff --check -- openspec/changes/admin-americanos/tasks.md openspec/changes/admin-americanos/verification.md` | **exit0, sin errores de whitespace**; solo avisos de normalización LF→CRLF. |

El repaso del checklist confirma las ocho casillas0.1/1.1/1.2/1.3/3.1/3.2/8.1/8.2;2.1/2.2/2.3 y3.3 permanecen sin marcar, sin crear tareas. `git status --short` distingue los dos docs de esta pasada de los cuatro archivos backend ya modificados por otros escritores; el diff de las seis fuentes/tests puros frente a `2bc5abf` sigue vacío. No se ejecutaron pruebas de aplicación, builds, instalaciones, migraciones ni commits. Se repiten strict y whitespace después de completar este registro.

### Session handoff histórico — auditoría pura, Engram no disponible

#### Goal
Aceptar1.1/1.2/1.3 puras tras auditoría independiente dedicada y actualizar el checklist5→8/31 después de `2bc5abf`.

#### Instructions
Reserva exclusiva de I: `tasks.md` y `verification.md`. Solo documentación y CLI OpenSpec/whitespace; sin tests, builds, instalaciones, migraciones, commits ni push.3.3 continúa en carriles backend/frontend y no se acepta aquí. Procedencia del informe: revisor independiente vía coordinación.

#### Discoveries
Las tres fuentes/tests puros siguen idénticos a `2bc5abf`. `SavedScore` null es inválido; B filtra entradas completas/guardadas por contrato. Preview parcial con faltantes es válido, pero PUT completo/revisiones/invalidation pertenecen a API. Otros resúmenes documentales todavía tienen5/31 y requieren consolidación posterior fuera de esta reserva.

#### Accomplished
Aceptadas1.1/1.2/1.3 puras sobre código existente con auditoría dedicada PASS; registrados126 tests y probes independientes, sin inventar RED retrospectivo ni repetirlos. Conteo vigente8/31,23 pendientes; historia5/31 fechada y ancla8.2 preservadas. Contrato POST `/fixture` y respuesta `{event,first_round}` reiterados para3.3, pendiente. Evidencia de validación documental en la sección precedente.

#### Next Steps
Esperar entrega estable de los dueños backend/frontend3.3 y su revisión/integración live antes de aceptar. Verificar filtrado de scores y obligaciones transaccionales/revisiones de API en sus tareas. Consolidar después los resúmenes fuera de esta reserva; mantener2.x/5.1/5.2/9.x y G2/G3/G4 pendientes según checklist, sin atribuir prueba PostgreSQL ni cambiar auth.

#### Relevant Files
`tasks.md` — ocho casillas aceptadas y límites actuales; `verification.md` — procedencia del revisor, matriz, comandos, historia y handoff vigente. Lectura: `backend/src/app/americanos/{fixture,standings,qualification}.py`, sus tres tests dedicados y `contracts.md` §4.2; código puro sin cambios frente a `2bc5abf`. Herramientas Engram ausentes: este handoff persiste en el repositorio, sin afirmar guardado en memoria.

<a id="cierre-actual--fixture33-parcial"></a>

## Registro histórico — fixture3.3 funcional PASS, aceptación entonces PARTIAL (2026-10-22)

**Se mantienen8/31 aceptadas y23 pendientes.3.3 permanece sin marcar.** Backend y frontend de generación están implementados y revisados con PASS funcional; falta **prueba de contención con dos sesiones reales en PostgreSQL descartable** para cumplir AE-07 «Generación concurrente» y la aceptación de3.3. Compilar `FOR UPDATE`, refrescar identidad cacheada, ejecutar dos sesiones ordenadas o recibir409 secuenciales en SQLite no demuestra esa garantía. Hallazgo de evidencia **MEDIUM**, no defecto de implementación identificado.5.1/5.2 siguen PARTIAL por continuación operativa4.1/routing, sin aceptación de9.x/G2/G3/G4.

### Procedencia y alcance de esta integración

**Evidencia suministrada por coordinación desde productores y revisores independientes**, no atribuida al usuario como ejecutor ni reejecutada por el integrador documental. Productores: backend3.3 y frontend3.3. Revisiones de solo lectura: DOM `ses_e9f0f6b89ffeGHcMDuVK54npWt` y LIVE `ses_e9f0f6b6bffeyTn2gfI0iwniOH`. I leyó fuentes de generación/cliente/setup/tests pertinentes y los cuatro artefactos live indicados abajo; los conteos DOM/productor proceden de sus handoffs suministrados por coordinación.

La implementación backend de este slice está limitada a `backend/src/app/americanos/{service,router}.py` y `backend/tests/test_americano_{events,privacy}.py`; frontend solo `frontend/src/api/americanos.ts` y `frontend/src/pages/americanos/AmericanoSetupPage.tsx`. Tipos y rutas no cambiaron. Las ediciones backend parciales previas a un error de uso de herramienta fueron confirmadas como trabajo del dueño; se recuperó/retesteó su estado antes de seguir editando, sin revertir trabajo ajeno. El último checkpoint commiteado sigue siendo **`2bc5abf`**; implementación nueva y documentación están **sin commit**.

I consolida exclusivamente `tasks.md`, `verification.md`, `contracts.md`, `design.md`, `proposal.md` y las introducciones de disponibilidad AE/AK. No cambia comportamiento normativo, versión contractual, fuentes ni tests. Engram no expone herramientas; recursos/templates MCP vacíos: este registro es el handoff persistente, sin simular llamadas de memoria.

### Contrato y disponibilidad actuales

| Aspecto | Estado contrastado |
|---|---|
| Transporte2.1.0 | **POST `/{e}/fixture`**, body **`RevisionRequest={expected_revision}`**,200 **`GenerateFixtureResponse={event,first_round}`**. Zonas/random conservan `EventDetail` directo. Sin bump de versión. `/generate` fue error de instrucción corregido por coordinación antes de integrar, no endpoint nuevo. |
| Cliente setup | **Diez métodos HTTP reales**: siete draft+zonas+random+fixture; `americanoDraftOperations` mantiene siete. Las otras ocho operaciones contractuales (ronda GET/PUT, standings, qualification, resoluciones, confirmación y playoffs GET/PUT) siguen ausentes. |
| UI de generación | Confirmación nativa irreversible; cancelar no envía POST. Requiere elegibilidad canónica, ningún dirty config/pareja/zonas, pending ni reconciliación sin resolver. Consume `response.event`; no trata envelope como `EventDetail`. |
| Resultado y navegación | Resumen/configuración read-only con aviso honesto de continuación pendiente; no monta `first_round` como puesto operativo ni llama4.1. Cero partidos: review,0 rondas, `first_round=null`, sin ronda0 ni confirmación automática. |
| Recuperación incierta | GET canónico puede adoptar generado; GET fallido mantiene bloqueo. Draft verificado exige adopción explícita y nueva confirmación para otra intención. Nunca POST automático/ciego ni duplicado por nombres repetidos. |
| Metadata y activación | Mismo registro indirecto de ocho tablas por import, sin DDL de arranque ni cambios session/env. SQLite descartable no prueba locks PostgreSQL; migración/activación productiva requieren aprobación separada. Auth/nav/logout/data-router/5.3 sin cambios. |

### TDD Cycle Evidence — entrega3.3

Fuente: handoffs de productores suministrados por coordinación. Los totales son snapshots de alcances distintos, no se suman entre filas ni se inventa RED retrospectivo para código puro existente.

| Task | TestFile / harness | Layer | SafetyNet | RED | GREEN | TRIANGULATE | REFACTOR / recuperación |
|---|---|---|---|---|---|---|---|
|3.3 backend: endpoint | `test_americano_events.py` | API aislada | Baseline **211** antes de editar | **1** por endpoint fixture ausente | **1** focalizado | Entrada/salida contractual real | Sin refactor adicional atribuido a este paso |
|3.3 backend: cero/cupos/referencias | `test_americano_events.py` | API aislada | Endpoint verde | Cero: **1 fallo/1 passed**; cupos/referencias: **11** | Cero **2 PASS**; cupos/referencias **13 PASS** | Suite pertinente **268**, luego **63** casos de generación | Refactor pertinente **278 PASS** |
|3.3 backend: cierre | events+privacy | API aislada | Estado del dueño confirmado/recuperado | Sin RED adicional informado | **278 PASS,19.09 s** final de recuperación | NULL,congelación,no shuffle,revisión,rollback; compilación PG y sesiones ordenadas | Retesteado antes de continuar; no se atribuye concurrencia PostgreSQL |
|3.3 frontend: cliente/setup | `slice33-run.py` y archivos temporales asociados | Browser con fixtures | **40 PASS,65.467 s** + lint antes de editar | **12 métodos:**2 fallos de assertion y16 errores de subcasos;2 casos de guards ya verdes. Cliente: **2 RED** por generate ausente | **53 PASS,86.489 s** + lint | Recuperación/eligibilidad/confirmación/resumen; live independiente23/23 separado | Sin refactor adicional; recursos53362/53373 cerrados según entrega |

### Revisión DOM independiente — PASS funcional, evidencia concurrente pendiente

Informe `ses_e9f0f6b89ffeGHcMDuVK54npWt`: **sin defectos de implementación**, PASS backend acotado; **MEDIUM** por falta de evidencia concurrente3.3, recomendación mantener unchecked.

| Archivo / alcance | Resultado informado |
|---|---|
| `test_americano_events.py` |239 PASS |
| `test_americano_privacy.py` |39 PASS; **278 API** con events |
| fixture / standings / qualification |39 /32 /55 PASS |
| bracket / knockout / schemas |45 /284 /389 PASS |
| Total actual, ocho archivos | **1122 passed,1 warning de dependencia existente,24.35 s**. No incluye `test_americano_models.py` ni prueba fresca de metadata. |

**Los1195 PASS históricos de la revisión8.2 se conservan como otra ejecución** (incluía models y metadata en proceso separado). No se afirma rerun de modelos ni se presenta1122 como el mismo conjunto reducido por fallos; tampoco es regresión global de liga9.2.

El revisor también informó exploración independiente **sin archivos**, nueve configuraciones:8,7+7,16,5+4,1+1,17,1+4,4+1,9+8; IDs no monótonos y nombres repetidos.17→136 partidos/34 rondas, primera ronda con1 bye y4 descansos por capacidad. Todos los cruces intrazona una vez, máximo6, orden/rondas reales y descanso de primera ronda correctos; scores NULL, `revision+1`, `groups_revision` preservada (no asumir cero como única entrada). Manual y random conservan membresía/nombres/orden sin resorteo; congelación de todos los mutadores incluso review cero partidos.

Rollback probado para inserción parcial y commit en tests del productor/revisor. El probe independiente de fallo de construcción de respuesta **después de flush** comprobó rollback atómico y posterior reintento con la revisión original exitoso. La prueba de dos sesiones existente dice explícitamente **ordered transactions** (`test_americano_events.py`, prueba de refresco de draft cacheado); no hay contención simultánea real PostgreSQL.

Comando seguro informado por el revisor DOM, **registrado, no ejecutado en esta integración**, desde `backend/`:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src DATABASE_URL=sqlite:///:memory: TEST_DATABASE_URL=sqlite:///:memory: PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/Scripts/python.exe -B -m pytest --noconftest -p no:cacheprovider tests/test_americano_events.py tests/test_americano_privacy.py tests/test_americano_fixture.py tests/test_americano_standings.py tests/test_americano_qualification.py tests/test_americano_bracket.py tests/test_americano_knockout_rules.py tests/test_americano_schemas.py -q
```

Venv existente, bytecode/plugins/cache desactivados, ambas URLs en memoria; `--noconftest` evita el conftest raíz que crea/borra tablas. Estas pruebas no autorizan usar una BD activa ni prueban PostgreSQL.

### Revisión LIVE independiente — integración funcional PASS

Informe `ses_e9f0f6b6bffeyTn2gfI0iwniOH`: **sin hallazgos accionables P0–P3 de fuente**, **23/23 checks agrupados PASS** App real→Vite→FastAPI→SQLite NUEVO. Primera ejecución del nuevo harness. **375 respuestas reales** =246×200+93×201+12×401+18×409+3×422+3×404; **0 backend5xx,0 errores JS**.373 observadas por browser/contexto y2 respuestas200 realmente comprometidas luego descartadas deliberadamente. Fixture:10×200,5×409,2×422,1×401,1×404. **17 diálogos nativos:13 aceptar/4 cancelar**. `npm --ignore-scripts run lint` (`tsc --noEmit`) **exit0**. Los53 browser con fixtures del productor no se reclasifican ni se suman al live.

| Caso live | Evidencia real y límite |
|---|---|
|8 una zona |28 partidos/7 rondas, primera4 partidos NULL sin descansos; respuesta canónica y reload read-only. |
|7+7 random persistido |42/7, primera6 partidos y1 bye real por zona; membresía/IDs/nombres/orden/zonas antes/después idénticos. |
|16 una zona |120/30, distribución `[6,2] * 15`, primera6 partidos y4 descansos capacity. |
|5+4 manual |16/5, distribución4,4,4,2,2 y bye real; sin equilibrar manual. |
|1+1 final |review,0 rondas/partidos, `first_round=null`, max_unlocked0/continuation qualification; UI no abre ronda0 ni ruta futura. |
| Persistencia/freeze/repeat |Oráculo independiente de combinaciones, <=6 y ninguna doble participación; NULL en respuesta/DB, revisión+1 y groups_revision0 en estos casos. Todos los mutadores rechazados409 tras generar con snapshot DB intacto por rechazo; stale409. |
| Invalidación/identidad |Sin asignar y cupos3+5 para cuartos:422 sin filas parciales/revisión alterada. Evento ajeno intacto, referencia422/anidado404; diez métodos anónimos401. |
| Dirty/conflicto/red |Cancelar confirmación no escribe; dirty/pending bloquean.409 real, GET abortado y adopción explícita sin escritura. Dos respuestas fixture comprometidas luego perdidas, GET exitoso/fallido y peticiones abortadas antes de backend: recuperación canónica sin auto-POST ni duplicación. |
| Público/historial |Cinco rutas públicas antes/después sin auth/private fetch/enlaces Americanos; filas de liga no vacías y snapshots HTTP idénticos. Historial generado real abre configuración read-only, aviso de continuación pendiente y cero llamadas a APIs futuras. |

### Artefactos live y cierre de recursos

Directorio **`C:\Users\pocho\AppData\Local\Temp\opencode\independent-live-gekh3hyv\`**:

| Artefacto | Uso / contraste documental |
|---|---|
| `independent-review.md` |Matriz, fuentes, comandos efectivamente ejecutados por LIVE y límites; leído por I. |
| `audit-summary.json` |Conteos HTTP/fixture/diálogos,13 hashes estables y auditoría de recursos; leído por I. |
| `result.json` |23 checks/cleanup/DB guard; leído por I. |
| `session-summary.md` |Handoff del revisor; leído por I. |
| `browser-evidence.json`, `backend-http.jsonl`, `db-guard.json`, `db-final-rows.json`, `league-before.json`/`league-after.json`, logs/PNG |Evidencia detallada indexada por LIVE; no se afirma haber releído todo este material en la pasada documental. |

Según auditoría: ambas URLs globales `sqlite:///:memory:`, **0 conexiones al engine global**, override exclusivo `get_session`, login/guard reales. SQLite descartable nuevo, schema por metadata solo allí, FK ON y `foreign_key_check=[]`. **13 fuentes productivas/tests hash-stable** durante run/auditoría. Puertos **54804/54806 cerrados**, PIDs **18440/24304/15228 ausentes**; frontend/cache y temporales propios, sin build/instalación/migración. No se relanzan ni se reauditan procesos desde esta integración documental.

Límites: SQLite y requests ordenados no prueban contención PostgreSQL; LIVE no inyectó fallos SQL de insert/commit (los cubre DOM/API). No matriz live completa de sesión inactiva/vencida, guard global/nav/logout, accesibilidad completa/mobile ni regresión pytest de liga.5.3/9.x y G2/G3/G4 conservan sus criterios.

### Pendientes y continuidad

1. **3.3 permanece PARTIAL/unchecked:** obtener autorización separada para PostgreSQL descartable y probar **dos sesiones reales que compitan** por el mismo borrador/revisión; exactamente un fixture y conflicto/estado canónico para el otro, sin duplicados ni revisión extra. No usar BD activa ni convertir compilación SQL o sesiones ordenadas en esa prueba. La autorización de migraciones/activación productiva sigue separada.
2. **4.1 puede progresar** cuando el usuario solicite el próximo slice: entrega funcional3.3 y tabla pura1.2 ya presentes. Las dependencias son por entregable, sin gate rígido de fase; avanzar no acepta3.3 completa ni elimina su TODO concurrente. Conectar continuación real/routing después;5.1/5.2 siguen PARTIAL.
3. **2.x y9.x/G2/G3/G4 siguen pendientes**; APIs de rondas/tablas/clasificación/playoffs y campeón atómico8.3 no se atribuyen a esta entrega. B debe filtrar scores completos/guardados para1.2; PUT completo/revisiones/invalidation de resoluciones siguen en API futura. Transporte2.1.0/D3/D6/D8 intactos.

### Validación documental final

Comprobaciones ejecutadas desde la raíz, exclusivamente documentales:

| Comprobación | Resultado |
|---|---|
| `openspec validate admin-americanos --strict --type change --no-interactive --json` | **valid=true,issues=[],exit0**;1 cambio válido. |
| `openspec list --json` | **completedTasks=8,totalTasks=31,status=in-progress**;23 pendientes. |
| `openspec status --change admin-americanos --json` | spec-driven, cuatro artefactos `done`; `isComplete=true` solo de planificación, no aceptación de implementación. |
| Lectura del checklist mediante búsqueda `^- \[[x ]\]` en `tasks.md` |31 casillas,8 marcadas:0.1/1.1/1.2/1.3/3.1/3.2/8.1/8.2;3.3 y5.1/5.2 sin marcar. |
| `git diff --check -- <siete docs autorizados>` | **exit0**, sin errores de whitespace; avisos de normalización LF→CRLF. |
| Revisión de diff de los siete docs y `git status --short` | Specs AE/AK cambian solo su introducción de disponibilidad; requisitos intactos. Estado conserva los seis archivos backend/frontend previos, junto a siete docs. `git log -1 --oneline` confirma checkpoint `2bc5abf`. |

Se repiten strict y whitespace después de registrar estos resultados. No se ejecutaron suites de aplicación, lint/typecheck, servidores, builds, instalaciones, migraciones ni commits. Las cifras de runtime de las secciones anteriores provienen de coordinación/productores/revisores, no de esta pasada. Checklist sin nuevas casillas y3.3 abierta.

### Session handoff histórico — fixture3.3 parcial, Engram no disponible

#### Goal
Continuar el trabajo3.3 de admin-americanos tras «continuamos», consolidando la entrega backend/frontend y dos revisiones independientes en documentación, sin aceptar la garantía concurrente aún no demostrada.

#### Instructions
Integrador final solo documentación: cinco archivos principales del cambio e introducciones AE/AK para disponibilidad, sin modificar requisitos. Mantener8/31/23 pendientes,3.3 unchecked y5.1/5.2 PARTIAL. Sin pruebas/servidores/builds/migraciones/commits en esta pasada. El usuario pidió el commit previo y luego continuar: `2bc5abf` ya existe; trabajo nuevo sin commit y sin autocommit autorizado para el siguiente slice.

#### Discoveries
Diez operaciones setup reales/siete draft, ocho APIs futuras ausentes. `/fixture` y envelope2.1.0 ya eran el contrato; `/generate` fue error de instrucción corregido antes de integrar. PASS funcional no demuestra contención real PostgreSQL; sesiones ordenadas y caché fresca no bastan para AE-07. Metadata conserva mismo registro por import sin DDL de inicio.1195 PASS es historia con models;1122 actuales no los ejecutan.

#### Accomplished
Productor backend278 API PASS y frontend53 browser de fixtures+lint; DOM1122 PASS con rollback/sondeos independientes, LIVE23/23 PASS con375 respuestas reales,0×5xx/0 errores JS y typecheck PASS, todos suministrados por coordinación y sin reejecución aquí. Generación/congelación/no shuffle, confirmación y recuperación canónica verificados funcionalmente. Siete docs alineados a8/31 sin bump de contrato ni cambios normativos; TDD/procedencia/historia y límites conservados. Validación documental en la sección precedente.

#### Next Steps
Solicitar autorización separada antes de prueba de dos sesiones reales concurrentes PostgreSQL descartable; nunca BD activa. Cuando se solicite continuar funcionalmente,4.1 puede consumir la entrega3.3 y1.2 sin gate rígido, conservando3.3 abierta hasta completar su prueba. Conectar routing/continuación y luego evaluar5.1/5.2;2.x/9.x/G2/G3/G4 y migración/activación productiva siguen sus gates. No autocommit.

Preflight posterior de solo lectura: Docker CLI29.5.3/contexto `desktop-linux` disponibles, pero daemon Linux de Docker Desktop inaccesible (named pipe ausente). `psql`/`pg_isready` en PATH; el venv permite localizar psycopg/SQLAlchemy/SQLModel/pytest. No se conectó a PostgreSQL ni se arrancaron servicios. El compose existente usa PostgreSQL de desarrollo persistente y no se utilizará; el conftest raíz elimina metadata y tampoco se utilizará. Plan pendiente de aprobación: usuario inicia Docker Desktop, contenedor PostgreSQL17 de nombre único con puerto asignado solo en127.0.0.1, almacenamiento efímero y sin mounts de proyecto; descarga de imagen solo si se autoriza. Crear únicamente las ocho tablas Americanos mediante allowlist, sembrar datos sintéticos, competir con dos sesiones y eliminar exclusivamente el contenedor propio al terminar. Sin Alembic, migraciones ni BD activa. Engram no disponible; descubrimiento conservado aquí.

#### Relevant Files
`backend/src/app/americanos/service.py`/`router.py` — fixture atómico funcional; tests events/privacy —278 API. `frontend/src/api/americanos.ts`/`pages/americanos/AmericanoSetupPage.tsx` — operación real, confirmación, read-only/recuperación. `openspec/changes/admin-americanos/{tasks,verification,contracts,design,proposal}.md` — conteos, contrato y evidencia; specs AE/AK — disponibilidad introductoria únicamente. Directorio `independent-live-gekh3hyv` — evidencia live/cleanup. Engram ausente; este handoff persiste en el repositorio sin afirmar llamadas de memoria.

### Session handoff histórico — 4.1 aceptada, Engram no disponible
**Objetivo/resultado:** integración documental9→10/31,21 pendientes; solo4.1 backend reads aceptada tras DOM/PRIV PASS. Requisitos y contrato2.1.0 intactos; historia3.3 parcial preservada, aceptación PostgreSQL previa vigente.
**Instrucciones:** sin archivos nuevos/logs/apéndices de evidencia en código productivo; notas existentes breves y tests significativos conservados. Esta pasada no ejecuta tests/build/install/migraciones ni commit/push; trabajo sin commit.
**Continuación:**4.2, guardado completo de ronda aún ausente; cliente setup diez/API12, sin wiring frontend nuevo.5.1/5.2/5.3/6.x/9.x/G2/G3/G4 siguen pendientes según checklist. Archivos: cinco docs principales e introducciones AE/AK; Engram sin herramientas, sin afirmar guardado en memoria.
**Validación documental:** OpenSpec strict válido sin issues; list10/31 `in-progress`,21 pendientes; status cuatro artefactos `done` solo de planificación. Checklist31 casillas con las diez aceptadas indicadas arriba; `git diff --check` de los siete docs sin errores de whitespace. Specs AE/AK: solo disponibilidad introductoria.
