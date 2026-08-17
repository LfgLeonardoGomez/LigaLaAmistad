# 01 — Alcance del producto

## Objetivo

Crear una web para la liga de pádel **Liga La Amistad**, organizada entre amigos, con una parte pública para mostrar información del torneo y un panel administrativo simple para cargar datos operativos.

El proyecto debe cubrir las necesidades reales de esta liga, evitando convertirlo prematuramente en una plataforma genérica de torneos.

## Contexto del torneo

- Hay 20 parejas participantes.
- Las parejas se dividen en 2 zonas.
- Cada zona tiene 10 parejas.
- En cada zona juegan todos contra todos.
- Las 20 parejas están definidas desde el inicio de la liga.
- La zona de una pareja se asigna al crearla y no se modifica nunca.
- Los partidos son organizados por los propios participantes.
- No existen fechas/jornadas fijas del torneo como "fecha 1", "fecha 2", etc.
- El administrador carga partidos con una fecha fija.
- Una vez jugado el partido, el administrador carga los sets y el sistema calcula el ganador automáticamente.
- El administrador puede corregir un resultado ya cargado.
- Todas las parejas clasifican a playoff, pero la implementación de playoffs queda para una etapa posterior.

## Partes del sistema

### Web pública

La web pública es visible para cualquier visitante.

Debe mostrar:

- Home del torneo.
- Información general de la liga.
- Parejas participantes.
- Tabla de posiciones por zona.
- Historial de partidos jugados.
- Sponsors.

### Panel administrativo

El panel administrativo es privado.

Debe permitir:

- Iniciar sesión como administrador.
- Gestionar parejas (crear y editar jugadores y foto; la zona no se edita).
- Subir fotos de parejas a Cloudinary.
- Gestionar sponsors.
- Subir logos de sponsors a Cloudinary.
- Crear partidos pendientes, filtrando parejas por zona.
- Cargar resultados de partidos jugados.
- Corregir o eliminar un resultado ya cargado.
- Ver partidos pendientes y jugados por separado.
- Ver tabla de posiciones con métricas completas.

No habrá roles. Todos los administradores tienen los mismos permisos.

El primer administrador se crea mediante un seed inicial, no desde la interfaz.

## Alcance del MVP

El MVP debe resolver:

1. Gestión de parejas (alta y edición).
2. Carga de fotos de parejas.
3. Gestión de partidos de fase de zonas.
4. Carga de resultados por sets.
5. Corrección de resultados ya cargados.
6. Cálculo automático de ganador.
7. Cálculo automático de tabla de posiciones.
8. Vista pública de tabla simplificada.
9. Vista pública de partidos jugados.
10. Gestión de sponsors.
11. Login administrativo simple.

### Nota sobre las zonas

Las zonas no son una entidad a gestionar. Son dos, fijas (Zona A y Zona B), creadas por seed.

Su rol es doble y siempre de agrupación:

- Visual: separar las tablas de clasificación en la web pública.
- Operativo: filtrar parejas al crear un partido.

No hay altas, bajas ni edición de zonas en ninguna parte del sistema.

## Fuera de alcance inicial

Queda fuera del MVP:

- Gestión completa de playoffs.
- Redistribución automática de puntos por baja de una pareja.
- Eliminación de parejas.
- Roles y permisos avanzados.
- Registro público de usuarios.
- Comentarios o interacción social.
- Notificaciones.
- Gestión de canchas.
- Gestión de horarios.
- Pagos.
- Multi torneo.
- Multi tenant.
- App mobile.

## Infraestructura propuesta

- Frontend: React + TypeScript + Vite.
- Deploy frontend: Vercel.
- Backend: FastAPI.
- Deploy backend: Railway.
- Base de datos: PostgreSQL en Railway.
- Imágenes: Cloudinary.

## Criterio de diseño

El sistema debe ser simple, entendible y mantenible.

La prioridad es que el desarrollador pueda programarlo a mano, entendiendo cada pieza, con asistencia de IA pero sin delegar el aprendizaje ni la arquitectura.
