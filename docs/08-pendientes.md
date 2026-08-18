# 08 — Pendientes

Lo que falta, en orden. Se actualiza a medida que se cierra cada punto.

## 1. Deploy (en curso)

| Paso | Estado |
|---|---|
| Cuenta y proyecto en Railway | pendiente — lo hace el usuario |
| Plugin de PostgreSQL en Railway | pendiente |
| Variables de entorno en Railway | pendiente — la lista está en `backend/README.md` |
| Cuenta y proyecto en Vercel | pendiente |
| Credenciales de Cloudinary en `backend/.env` | pendiente |

El código de ambos lados ya está listo: `railway.json` corre las migraciones y
levanta el servidor, y el frontend compila para Vercel sin configuración extra.

## 2. Foto y comentario en el resultado de un partido

**Prioridad alta, apenas termine el deploy.**

Al cargar el resultado de un partido, la organización puede sumar una foto y un
comentario. La idea es social: que la pareja ganadora pueda cargar la foto del
partido y un comentario para cargar a la que perdió.

### Qué toca

Es la primera funcionalidad que cambia el modelo de datos desde el MVP.

- **Modelo**: dos campos nuevos en `Match` (`photo_url`, `comment`) o una tabla
  aparte si más adelante se quieren varios comentarios por partido. Para el
  alcance actual, dos campos alcanzan.
- **Migración**: una revisión de Alembic. Los partidos ya cargados quedan con
  ambos campos en `null`, así que no hace falta backfill.
- **API**: `POST` y `PUT` de resultado aceptan los dos campos; `MatchRead` los
  devuelve. La subida de la foto sigue el mismo camino que la de las parejas:
  un endpoint aparte que sube a Cloudinary y guarda la URL.
- **Panel**: los campos se agregan al formulario de resultado que ya existe.
- **Web pública**: la tarjeta de resultado muestra la foto y el comentario
  cuando están, y se ve igual que hoy cuando no están.

### Decisiones abiertas

- ¿El comentario tiene límite de caracteres? Propuesta: 280.
- ¿Se puede editar o borrar el comentario después de cargarlo? Hoy `PUT` de
  resultado reemplaza todo; habría que definir si la foto y el comentario
  también se reemplazan o si sobreviven a una corrección del marcador.
- ¿La foto va a la misma carpeta de Cloudinary que las parejas o a una propia?

## 3. Más adelante

Está en `docs/04` como explícitamente fuera del primer slice:

- Playoffs.
- Compensación por baja de pareja.
