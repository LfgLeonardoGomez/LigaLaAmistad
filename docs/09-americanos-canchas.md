# Americanos: canchas y preparación por pasos

## Operación

1. Configuración: nombre, una/dos zonas, inicio de eliminatorias y canchas disponibles.
2. Parejas: alta individual o múltiple, edición y eliminación.
3. Zonas: distribución manual o aleatoria y revisión de cupos.
4. Fixture: resumen y generación definitiva.

La grilla representa la disposición física: **4–5–6 arriba, 1–2–3 abajo**.
Se requiere al menos una cancha, sin duplicados, entre 1 y 6. Los números no
se renumeran: seleccionar 3 y 6 produce partidos en las canchas 3 y 6.

Se puede volver a los pasos previos mientras el evento sea borrador; primero
hay que guardar o descartar la edición activa. Guardar no cambia el paso.
Generar sigue siendo irreversible: bloquea configuración, parejas y reparto.
La confirmación se presenta en un modal del panel. Al confirmar se abre
directamente la primera ronda; si no hay cruces de grupos, se abre clasificación.
El historial muestra la pareja campeona cuando el evento está finalizado.

## Fixture y eliminatorias

- Cada ronda global tiene como máximo tantos partidos como canchas elegidas.
- Una cancha y una pareja aparecen como máximo una vez por ronda.
- Se conserva el todos contra todos de cada zona, sin repetir ni omitir cruces.
- Con capacidad reducida se intercalan cruces A/B para compartir las canchas.
  Se mantienen los bloques Berger; no se compactan bloques distintos.
- Las parejas que no juegan aparecen libres, con motivo por capacidad,
  imparidad o zona finalizada.
- Con siete parejas en una zona y al menos tres canchas hay siete rondas,
  veintiún partidos únicos y exactamente un libre por pareja. Cada pareja juega
  contra sus seis rivales. Con menos canchas, los descansos por capacidad se
  repiten necesariamente; eso no significa que se repita un cruce o se asigne
  otro libre lógico de Berger.
- Cada partido eliminatorio recibe una cancha sugerida, reutilizable en
  distintos turnos. Una etapa eliminatoria **no representa simultaneidad**.
- Desde el cuadro se puede cambiar la sugerencia por otra cancha seleccionada
  mientras el partido no tenga resultado y el evento siga en eliminatorias.
  El cambio es independiente de participantes, resultados y avances del cuadro.
- En el tanteador eliminatorio se permite un dígito entre 0 y 7, con sets
  completos 6–0 a 6–4, 7–5 y 7–6 (o sus inversos). El foco pasa de A a B,
  después a Guardar y, tras guardar explícitamente, al siguiente partido
  pendiente. No se guardan resultados automáticamente al escribir.
- El ajuste usa `PUT /admin/americanos/{event_id}/playoffs/{node_id}/court`,
  con `expected_revision` y `court_number`, autenticación y protección CSRF.

## Persistencia y despliegue pendiente

Migración nueva: `a2c37e91d046_add_americano_courts.py`, después de
`f1a62d9c4b83`. **Debe aplicarse antes de iniciar el backend actualizado.**

Los eventos guardan una máscara de seis bits (`court_mask`, 1–63), expuesta
como lista ordenada `courts` en la API. Los partidos guardan `court_number`.
La base también impide repetir una cancha dentro de una ronda de grupos.

Para eventos anteriores, la migración conserva seis canchas, rondas, cruces,
resultados y revisiones. Sólo agrega números de cancha: `display_order` en
grupos y el slot en eliminatorias. El orden histórico con seis canchas no se
modifica, porque la confirmación reconstruye y verifica el fixture completo.

No se ejecutó ninguna migración en producción. Se ensayó upgrade/downgrade
con datos históricos en SQLite en memoria y se verificó el plan de metadata
con dialecto PostgreSQL. Además, se aplicó la cadena completa de migraciones
en PostgreSQL 17 local aislado. La validación con datos históricos reales y el
despliegue en producción siguen pendientes de autorización.

Para probar manualmente el entorno local y el caso de empate, ver
[Prueba local de Americanos](10-prueba-local-americanos.md).

## Verificación sin build

Desde `backend/`, con `DATABASE_URL=sqlite:///:memory:` y
`CORS_ORIGINS=http://testserver` únicamente para el proceso de pruebas:

```powershell
$env:DATABASE_URL='sqlite:///:memory:'
$env:CORS_ORIGINS='http://testserver'
.\.venv\Scripts\python.exe -m pytest --noconftest (Get-ChildItem tests/test_americano*.py).FullName -k 'not real_postgres' -q
```

Desde `frontend/`: `node_modules/.bin/tsc.cmd --noEmit`.

Prueba de navegador: iniciar Vite en `127.0.0.1:5175` (modo desarrollo, no
build), después ejecutar desde `backend/`:

```powershell
.\.venv\Scripts\python.exe browser_checks/americano_courts_wizard.py
```

El navegador intercepta todas las llamadas al API y usa el backend real con
una base privada en memoria. No modifica bases ni perfiles existentes.
