## Why

La organización necesita operar Americanos de parejas fijas desde el panel existente: configurar zonas, cargar una ronda completa y cerrar clasificados antes de jugar eliminatorias. La liga está en actividad; este flujo debe tener datos y reglas propios para preservar sus resultados y todas las páginas públicas.

## What Changes

- Agregar **Americanos** dentro de `/admin`, con listado simple de eventos independientes e historial, creación de borradores y recuperación del evento/ronda en curso.
- Configurar cantidad variable de parejas, una o dos zonas, asignación manual o aleatoria y comienzo de eliminatorias en cuartos, semifinal o final (8/4/2 clasificados).
- Generar todos los cruces intrazona una sola vez, distribuidos en rondas globales jugables de hasta seis partidos, con descansos y sin superposición de parejas.
- Operar una única ronda visible, marcadores de grupos de 0 a 9 (incluido 0-0), teclado ágil y guardado explícito y atómico de toda la ronda. Mostrar tablas en un cajón lateral, con victoria 1, empate 0,5 y derrota 0; ordenar exclusivamente por puntos y diferencia de games.
- Revisar clasificados, resolver mediante selección de parejas los empates relevantes decididos por sorteo humano y confirmar el pase a playoffs en una transacción que congela grupos y crea el cuadro.
- Jugar eliminatorias a un set completo, avanzar ganadores hasta campeón y consultar grupos bloqueados e historial.
- Proteger **todas** las lecturas y escrituras con la sesión administrativa existente. No incorporar datos, enlaces ni endpoints públicos de Americanos.

### Aprobación humana y disponibilidad actual — 2026-10-21

El usuario confirmó **«confirma todas ls decisiones que tenes ahi.»**: D3/D6/D8 aprobados, no sus alternativas. Autorizó después continuar/trabajo paralelo3.2 y8.1/8.2 puro. Contrato **[2.1.0](contracts.md)**, transporte sin cambios. **Estado actual:5/31 aceptadas (0.1,3.1,3.2,8.1 y8.2),26 pendientes**;8.2 exclusivamente pura tras P2 resuelto/revisión independiente PASS. [Evidencia actual e historia](verification.md#cierre-actual--reglas-puras82).1.x/2.x sin aceptación dedicada;5.1/5.2 PARTIAL,9.x/G2/G3/G4 incompletos. Esta nota actualiza disponibilidad/procedencia, no requisitos.

- **D3:** random equilibrado, diferencia <=1, manual desigual permitido; reparto persistido y visible antes de generar, sin resorteo al generar. Congelar composición/nombres/configuración desde generación, sin regeneración.
- **D6:** cuartos una zona Q1=1-8,Q2=4-5,Q3=2-7,Q4=3-6; dos Q1=A1-B4,Q2=B2-A3,Q3=B1-A4,Q4=A2-B3. Q1/Q2→S1 lados a/b, Q3/Q4→S2 lados a/b, S1/S2→final lados a/b. Final directa1-2/A1-B1; semifinales1-4/2-3 y A1-B2/B1-A2 sin cambios. Las seis plantillas actuales son approved.
- **D8:** solo6-0..6-4,7-5,7-6 y simétricos; rechazar5-3,6-5,empates, sin set largo por ventaja. Corregir solo si ningún descendiente jugó, aun con mismo ganador; si cambia ganador actualizar únicamente su lado del siguiente pendiente. Final corregible tras completed con campeón atómico y grupos cerrados; sin borrar ni reabrir.

**Slice entregado draft+zonas:** nueve operaciones privadas, siete de3.1 más PUT `/{e}/zones` y POST `/{e}/zones/randomize`; auth existente intacta, revisión/identidad por evento y cero mutaciones de liga. `americanoSetupOperations` publica nueve métodos reales; manual desigual y random equilibrado persistido/visible, una zona todas, cupos orientativos y recuperación explícita verificados live20/20+typecheck PASS. Sin cambios frontend posteriores al live informado.5.1/5.2 siguen PARTIAL.8.1/8.2 aceptadas solo puras: constructor, set y propagación/corrección copysafe, P2 de fuentes resuelto; no API playoffs ni manejo de estado DB/persistencia atómica de campeón (8.3). Seis plantillas approved y propuestas futuras preservadas.

**Generación3.3 deshabilitada**, aun con `can_generate=true`; rondas/clasificación/playoffs sin integración operativa. Próximo corte3.3: fixture atómico/congelación sin resorteo/regeneración; persistencia previa3.2 no prueba no resorteo DURANTE generar. Import `main→router→service→models` registra ocho tablas, sin DDL de inicio ni cambios en imports env/session. Pruebas solo en SQLite descartable, sin locks PostgreSQL acreditados. Migración/activación productiva requieren aprobación separada;5.3/guard global/nav/logout futuros, sin cambios auth. Esta pasada solo documentación/OpenSpec/whitespace, sin tests, servidores, builds, migraciones ni commits.

Fuera de alcance: regeneración de fixture generado, inscripciones tardías, reapertura de grupos confirmados, publicación/exportación, cuentas de jugadores, pagos, relojes/duraciones, reservas de canchas, multi-club, analítica y rediseño móvil.

## Capabilities

### New Capabilities

- `americano-admin-events`: acceso administrativo, aislamiento por evento, configuración de parejas/zonas y generación del fixture limitado a seis partidos globales por ronda.
- `americano-round-workstation`: ronda visible, navegación progresiva, carga por teclado, guardado atómico, recuperación y tablas en cajón lateral.
- `americano-qualification`: puntuación exacta, clasificación, empates relevantes, revisión y confirmación transaccional con bloqueo definitivo de grupos.
- `americano-knockouts`: cuadro flexible 8/4/2, set único, avance, correcciones protegidas y campeón.

### Modified Capabilities

Ninguna. `openspec/specs/` está vacío al iniciar el cambio. Las reglas vigentes de liga no se modifican.

## Impact

| Área | Alcance propuesto |
|---|---|
| Backend | Nuevo dominio `backend/src/app/americanos/` con modelos, DTO, funciones puras, servicios con `Session` y router `/admin/americanos`; registro aditivo en `app/main.py`. Reutilizar `auth/deps.py:get_current_admin` sin rediseñar autenticación. |
| Persistencia | Tablas `americano_*` y una migración Alembic aditiva en `backend/migrations/versions/`; registro de metadata explícito. Sin relaciones a parejas/partidos/zonas de liga ni traslado de datos existentes. |
| Frontend | Rutas hijas protegidas en `frontend/src/App.tsx`, entrada en `components/Layout.tsx`, cliente tipado en `src/api/` y pantallas/componentes propios. Reutilizar sesión, tema y primitivas visuales. |
| Verificación futura | Pytest focalizado de algoritmos, transacciones, permisos y regresión de liga/público. Frontend sin runner declarado: aceptación manual/browser y decisión explícita antes de agregar herramientas. |
| Dependencias | Ningún servicio ni paquete nuevo previsto. SQLModel, Alembic, FastAPI, React y cliente actuales. |

La ejecución propuesta será **multiagente en paralelo**, por pedido explícito del usuario y con mayor presupuesto de tokens autorizado: checkpoint inicial de contratos, hasta cinco escritores sobre archivos disjuntos y revisiones independientes de solo lectura. `design.md` D9 y `tasks.md` asignan carriles, propiedad de archivos, dependencias y gates de integración; frontend puede prepararse con fixtures tipados sin esperar la API completa, pero su aceptación exige conexión real. Esto cambia la organización del trabajo, no el alcance del producto ni las autorizaciones de implementación.

Gobernanza: reglas/UX **MEDIUM**, privacidad **CRITICAL**, migración/datos **HIGH**. Aceptadas0.1/3.1/3.2/8.1/8.2 pura; este cierre agrega solo8.2 tras P2 resuelto, no otras casillas/gates por suites verdes. `verification.md` preserva historia y evidencia suministrada. Sin autorización de rediseño auth, migraciones, build, commit, push ni archivo del cambio.
