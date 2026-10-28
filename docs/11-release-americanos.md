# Preparación de release — Americanos y seguridad

## Ejecución autorizada (2026-10-28)

- Backup privado de PostgreSQL 18 por SSH temporal, sin habilitar endpoint
  público. Snapshot de sólo lectura en revisión `f1a62d9c4b83`.
- Archivo externo al repositorio: `BackupsLigaLaAmistad/20261028T114958Z/database.dump`.
  SHA-256: `ada97f15703dde510297bea347baad82ac4ee52e55b0ad2fc7f32747e81400ee`.
- Restauración comprobada en contenedor sin red ni puertos: 20 tablas y 416
  filas, con hashes iguales al snapshot. Clave SSH revocada y copias eliminadas.
- Fase 1: `0152748`, Vercel SUCCESS y encabezado CSRF verificado en el bundle
  público antes de publicar backend.
- Fase 2: `c75b787`, Railway SUCCESS. Logs confirman migración a
  `a2c37e91d046`, arranque y health 200; OpenAPI expone canchas y campeón.
- Fase 3: interfaz completa y documentación, publicada después de verificar
  la segunda fase. La comprobación final no inserta eventos de prueba ni
  resultados en producción; el recorrido administrativo requiere iniciar
  sesión nuevamente en el panel.
- Los estados pendientes del apartado siguiente corresponden a la auditoría
  previa; este apartado registra la ejecución posterior.

## Estado revisado (2026-10-28)

- Base remota `main` y backend Railway: `14df6c1`.
- Railway: Dockerfile en `/backend`, watch path `backend/**`, health `/health`.
- API productiva y frontend Vercel responden 200.
- Producción todavía no tiene `courts` en creación ni `champion` en el resumen.
- La API actual acepta por CORS el header `X-Requested-With` desde el dominio
  productivo del frontend. Se verificó con un preflight, sin modificar datos.
- Cambios locales todavía sin commit/push. No se hicieron builds ni deploys.
- Variables de Railway comprobadas sin imprimir secretos: `SECRET_KEY` presente
  (64 caracteres), `DATABASE_URL` presente, cookies `Secure=true` y
  `SameSite=none`, CORS del dominio Vercel y sin `LIGA_ENV_FILE` local.

## Evidencia de validación

- Suite backend completa después del ajuste Alembic: **2.101 passed**, dos
  escenarios PostgreSQL omitidos en SQLite y ejecutados aparte en PostgreSQL.
- Después de instalar los tres wheels corregidos: **44 tests** de cuentas,
  imágenes y endpoints públicos, **21 tests** PostgreSQL de auth/CSRF y los
  **dos escenarios PostgreSQL de concurrencia**, todos PASS.
- Regresión Chromium final: 14 mutaciones en base privada, contraste de pasos
  y texto secundario AA en ambos temas, canchas, fixture, foco, playoffs e
  historial PASS. TypeScript `--noEmit` y `git diff --check` PASS.
- Ensayo con datos históricos PostgreSQL, reversibilidad y `alembic check`
  PASS. Auditorías de dependencias de producción sin avisos conocidos.
- Backup productivo, commits, push y builds/despliegues de las plataformas:
  **pendientes**, no ejecutados por esta revisión.

## Requisitos antes de publicar

1. Confirmar un backup reciente y recuperable del PostgreSQL productivo. No
   exportar datos a archivos del repositorio ni asumir que el volumen es backup.
2. Incluir los archivos nuevos: especialmente `core/csrf.py` y la migración
   `a2c37e91d046_add_americano_courts.py`, además de componentes y tests.
3. No versionar `.env`, `.local-dev/`, tokens, logs ni cookies. Las credenciales
   de los helpers de desarrollo son exclusivamente para el PostgreSQL aislado.
4. Acordar una ventana sin crear/generar Americanos ni cargar resultados. No
   permitir escrituras administrativas durante la migración y el recambio de
   la instancia anterior por la nueva. La actualización de tokens
   invalida sesiones anteriores: las personas administradoras deben recargar
   la página e iniciar sesión nuevamente.

## Orden recomendado: tres fases verificadas

Un único push con frontend y backend dispara dos plataformas en paralelo.
Eso introduce una ventana de incompatibilidad:

- Backend nuevo + cliente anterior: las mutaciones sin el header CSRF son 403.
- Interfaz nueva + backend anterior: el campo `courts` no es aceptado y faltan
  datos necesarios para la nueva configuración.

Por eso, publicar **una fase por vez y esperar que termine**:

1. **Transporte frontend:** publicar sólo `frontend/src/api/client.ts` para que
   los clientes recargados envíen `X-Requested-With`. Es compatible con el API
   actual. Confirmar Vercel listo antes de seguir.
2. **Backend:** publicar seguridad, contratos, migración y corrección del
   registro de modelos Alembic. Docker ejecuta preflight, `alembic upgrade head`
   y seed idempotente antes de Uvicorn. Verificar Railway SUCCESS, `/health`,
   CORS, nuevo contrato OpenAPI y ausencia de errores de migración.
3. **Interfaz:** publicar selección de canchas, pasos, desempates, tanteador,
   campeones y paleta clara suave. Verificar Vercel listo y solicitar recarga
   del panel. Agregar la documentación y herramientas locales en sus commits
   correspondientes, sin dejar cambios backend para una fase sólo frontend.

El primer frontend no añade controles nuevos ni envía `courts`, así que puede
funcionar mientras se migra el backend. El backend nuevo conserva los defaults
para clientes anteriores. La recarga sigue siendo necesaria para pestañas con
JavaScript viejo o cookies previas a la actualización de seguridad.

## Migración y comprobación local

Auditorías de dependencias de producción: frontend (`npm audit --omit=dev`) y
backend Linux (`uv audit --locked --no-dev`) sin avisos conocidos tras actualizar
`dnspython` a 2.9.0, Mako a 1.4.2 y `urllib3` a 2.8.0. Son consultas puntuales al
catálogo de avisos, no una garantía de ausencia de vulnerabilidades.

La migración agrega columnas y restricciones sin regenerar cruces. Los eventos
anteriores conservan seis canchas, rondas y resultados; los partidos reciben
números de cancha a partir de su orden original.

El ensayo `backend/browser_checks/release_postgres_check.py` crea una base
**nueva** en `127.0.0.1:5544`, nunca usa una URL productiva ni la demo del usuario:

- instala el esquema anterior;
- carga un americano histórico de siete parejas y 21 partidos, más un campeón;
- ensaya upgrade/downgrade/re-upgrade verificando que las columnas anteriores
  conserven exactamente sus datos;
- ejecuta `alembic check` para comprobar paridad del esquema;
- confirma el fixture histórico después de migrar;
- corre pruebas PostgreSQL de concurrencia y de autenticación/CSRF.

El entorno Alembic importa también votos, predicciones y playoffs de liga.
Los CHECK de enum de Americanos conservan los mismos nombres y valores, pero
ahora son explícitos en metadata para no aparecer como eliminados en autogenerate.
No hay una migración adicional para ese ajuste de registro.

El ensayo PostgreSQL pasó preservación de datos, upgrade/downgrade/re-upgrade,
`alembic check` sin operaciones pendientes, confirmación del fixture anterior,
dos escenarios de carrera score/confirm y 21 tests de autenticación/CSRF.

## Smoke posterior y rollback

- Comprobar web pública, login, listado de Americanos, lectura de rondas y de
  eventos anteriores. Verificar desde navegador el origin y las cookies HTTPS.
- Comprobar el header de seguridad del frontend y que el bundle apunte al API
  productivo, no a localhost.
- Cargar resultados reales sólo después del smoke; no insertar datos ficticios
  en producción sin autorización.
- Si falla el despliegue, detener la publicación y conservar el backup. Es
  preferible revertir la versión de aplicación manteniendo columnas aditivas
  a bajar esquema en caliente. Un rollback al backend previo a CSRF también
  revierte protecciones, por lo que no debe usarse como solución permanente.
- Nunca ejecutar `downgrade`, borrar volúmenes ni restaurar un backup en
  producción como parte de un rollback automático.
