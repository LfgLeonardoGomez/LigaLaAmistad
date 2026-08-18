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

## 2. Foto y comentario en el resultado — LISTO

Implementado y verificado contra PostgreSQL y Cloudinary reales.

Al cargar el resultado, la organización puede sumar una foto y un comentario
de hasta 280 caracteres.

### Cómo quedaron las decisiones

- **Límite del comentario**: 280 caracteres. La constante vive en
  `matches/models.py` y el frontend la espeja.
- **Corregir el marcador conserva foto y comentario.** El `PUT` distingue
  "campo ausente" de "campo en null" mirando `model_fields_set`: si el cuerpo
  no trae `comment`, se conserva el guardado; si lo trae en `null`, se borra.
- **Deshacer el resultado los limpia.** El motivo no es estético: un partido
  que vuelve a `pending` puede cambiar de fecha **y de parejas**, así que una
  cargada dirigida a una pareja podría terminar mostrándose sobre otro
  emparejamiento. No sería un dato huérfano, sería un dato falso.
- **Carpeta propia en Cloudinary**: `partidos-liga-la-amistad`.
- Consecuencia agregada: comentar y subir foto exigen que el partido esté
  `played`. Devuelve 400 si no.

### Endpoints

```txt
POST   /admin/matches/{id}/result          sets + comentario
PUT    /admin/matches/{id}/result          reemplaza sets, conserva lo demás
PATCH  /admin/matches/{id}/result          edita solo el comentario
POST   /admin/matches/{id}/result/photo    sube la foto
DELETE /admin/matches/{id}/result          deshace todo
```

### Lo que quedó pendiente de esta funcionalidad

- **La foto no se puede borrar sin deshacer el resultado.** Hoy solo se
  reemplaza subiendo otra. Falta aceptar `photo_url: null` en el `PATCH`.
- **El `PATCH` no tiene consumidor en el panel.** El formulario de resultado
  ya permite editar el comentario, que viaja en el `PUT`. El endpoint existe
  porque es la API correcta, pero no lo usa nadie todavía.
- **La foto pública se recorta a 4:3.** Mantiene prolija la grilla, pero una
  foto muy panorámica o muy vertical pierde bordes. Sin validar con el dueño
  del producto.

## 3. Más adelante

Está en `docs/04` como explícitamente fuera del primer slice:

- Playoffs.
- Compensación por baja de pareja.
