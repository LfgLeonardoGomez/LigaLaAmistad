# Prueba local de Americanos

## Entorno aislado, sin build

- Frontend: <http://localhost:5175/admin/americanos>.
- API: <http://localhost:8010/docs>.
- PostgreSQL 17 en Docker: `127.0.0.1:5544`, base `liga_americanos_dev`.
- Acceso **sólo local**: `admin@liga.local` / `Liga-local-2026!`.

Docker se usa para la base. La API usa el `.venv` existente y el frontend Vite
en modo desarrollo, con recarga automática. No se construyen imágenes de la
aplicación ni bundles. Los puertos habituales 8000 y 5173 no se modifican.

El launcher selecciona una ruta de configuración ausente mediante
`LIGA_ENV_FILE`, evitando heredar credenciales del `backend/.env`. Las subidas
a Cloudinary quedan deshabilitadas. El health local debe mostrar
`"cloudinary": false`.

## Arranque y parada

Desde la raíz, con Docker Desktop activo y las dependencias locales instaladas:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/start-americanos-dev.ps1
```

El script levanta la base, aplica migraciones exclusivamente a esa base, crea
el administrador local y un ejemplo idempotente. Si los puertos ya están
ocupados, se detiene sin cerrar procesos existentes.

Para detener **sólo** los procesos creados por el launcher:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/stop-americanos-dev.ps1
```

La parada verifica identidad y antigüedad de los PID antes de cerrar API y
Vite. La base y los datos se conservan. Sus logs están en `.local-dev/` (no
versionado). Para detener también el contenedor, sin borrar su volumen:

```powershell
docker compose -f compose.dev.yml stop
```

## Cómo probar el empate

1. Abrí **Demo empate puestos 1 y 2** en Americanos.
2. Las rondas ya están completas: Ana/Sol y Luz/Eva empatan en puntos y
   diferencia de games. Faltan sus puestos 1 y 2 para definir la final.
3. Pulsá **Resolver empates**. **Iniciar playoffs** también abre el diálogo
   cuando hay una decisión humana pendiente.
4. Elegí parejas diferentes para las plazas 1 y 2.
5. Pulsá **Guardar desempates**; la tabla muestra el orden guardado.
6. Pulsá **Iniciar playoffs** para congelar la clasificación y crear la final.

No se aplica un criterio deportivo nuevo ni un sorteo automático: la persona
administradora decide el orden del bloque empatado. El ejemplo no se reinicia
ni sobrescribe al volver a arrancar el entorno.

## Canchas y pasos

Creá otro evento desde la misma pantalla. Elegí canchas, por ejemplo 3 y 6,
cargá parejas, distribuí zonas y revisá el fixture. Guardá o descartá la edición
activa antes de cambiar de paso. En grupos se respeta el máximo de partidos
simultáneos; en eliminatorias se propone una cancha ajustable antes de jugar.

## Regresiones de navegador

Desde `backend/`, con Vite local activo:

```powershell
.\.venv\Scripts\python.exe browser_checks/americano_ties.py
.\.venv\Scripts\python.exe browser_checks/americano_courts_wizard.py
.\.venv\Scripts\python.exe browser_checks/local_americano_smoke.py
```

Las dos primeras usan el backend real con SQLite privada en memoria y cubren
desempates, persistencia, confirmación, canchas y pasos. La última
comprueba el login y el diálogo en el ejemplo PostgreSQL persistente, **sin
guardar decisiones ni consumir el ejemplo**; debe ejecutarse antes de que una
persona resuelva ese evento.
