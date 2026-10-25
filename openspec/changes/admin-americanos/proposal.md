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

### Aprobación humana y disponibilidad actual — actualizado2026-10-22

El usuario confirmó D3/D6/D8 y autorizó continuar con multiagentes en etapas anteriores. **31/31 tareas aceptadas; G3/G4 verificados.** Contrato de componentes **3.0.0**; HTTP/DTO conserva shapes **2.1.0**. [Checklist](tasks.md) y[evidencia](verification.md) distinguen disponibilidad de autorización de producción; requisitos intactos.

- **D3:** random equilibrado, diferencia <=1, manual desigual permitido; reparto persistido y visible antes de generar, sin resorteo al generar. Congelar composición/nombres/configuración desde generación, sin regeneración.
- **D6:** cuartos una zona Q1=1-8,Q2=4-5,Q3=2-7,Q4=3-6; dos Q1=A1-B4,Q2=B2-A3,Q3=B1-A4,Q4=A2-B3. Q1/Q2→S1 lados a/b, Q3/Q4→S2 lados a/b, S1/S2→final lados a/b. Final directa1-2/A1-B1; semifinales1-4/2-3 y A1-B2/B1-A2 sin cambios. Las seis plantillas actuales son approved.
- **D8:** solo6-0..6-4,7-5,7-6 y simétricos; rechazar5-3,6-5,empates, sin set largo por ventaja. Corregir solo si ningún descendiente jugó, aun con mismo ganador; si cambia ganador actualizar únicamente su lado del siguiente pendiente. Final corregible tras completed con campeón atómico y grupos cerrados; sin borrar ni reabrir.

**Slice entregado:** API/cliente **18 operaciones privadas reales**; puertos setup10/draft7,round4,qualification4 yplayoffs3 comparten `loadEvent`, no son conteos sumables. Fixture mantiene RevisionRequest→{event,first_round}. Confirmación atómica con snapshots/cuadro, editor Set completo, avance/campeón y corrección final completed con grupos cerrados. Ningún endpoint futuro pendiente de implementación.

**Flujo privado completo disponible en App:** borrador→fixture→rondas→resoluciones por ID→confirmación→cuadro→campeón. Guard protege edición/pending;409/red se recuperan con GET y decisión explícita, sin auto-reenvío. Liga/auth/público conservados. Imports metadata explícitos y revisión f1a62d9c4b83 preparados; NO migración ejecutada ni activación productiva. Restan ensayo2.3/carrera7.3 autorizados y9.3 final. Trabajo sin commit tras `5908f16`; evidencia externa, no runtime/logs productivos.

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

Gobernanza: reglas/UX **MEDIUM**, privacidad **CRITICAL**, migración/datos **HIGH**. Este cierre acepta exclusivamente4.2/4.3/5.2/6.4:14/31 según `tasks.md`. `verification.md` preserva historia y evidencia suministrada por coordinación; no completa9.x/G2/G3/G4. Sin autocommit, push ni archivo del cambio.
