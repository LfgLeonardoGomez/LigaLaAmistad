# Liga La Amistad

Sitio de una liga amateur de pádel: web pública con la tabla y los resultados,
y un panel para que la organización cargue parejas, partidos y resultados.

| | |
|---|---|
| Web pública | https://liga-la-amistad.vercel.app |
| Panel | https://liga-la-amistad.vercel.app/admin |
| API | https://ligalaamistad-production.up.railway.app |
| Documentación de la API | https://ligalaamistad-production.up.railway.app/docs |

## Estructura

```txt
backend/    FastAPI + SQLModel + PostgreSQL   → Railway
frontend/   React + TypeScript + Vite         → Vercel
docs/       alcance, reglas de negocio, modelo de datos, pendientes
```

Cada carpeta tiene su propio README con cómo levantarla, cómo probarla y cómo
se despliega. Antes de tocar código, `docs/` explica el dominio: la tabla se
calcula sola, un partido no guarda su zona ni su ganador, y las parejas no se
eliminan.

## Despliegue automático

Los dos servicios están conectados a este repositorio y **redespliegan solos
con cada push a `main`**. No hay que hacer nada a mano.

Al ser un monorepo, por defecto cada push reconstruye **las dos** aplicaciones
aunque el cambio toque una sola. Eso gasta minutos de build al pedo y, peor,
reinicia la API sin motivo: si alguien está cargando un resultado justo en ese
momento, ve un error.

Se limita indicándole a cada plataforma qué carpeta mirar:

**Railway** — Settings del servicio → *Watch Paths*:

```txt
backend/**
```

**Vercel** — Settings → Git → *Ignored Build Step*:

```bash
git diff --quiet HEAD^ HEAD -- ./
```

Ese comando corre parado en el *Root Directory* del proyecto, que es
`frontend/`. Si el commit no tocó nada de esa carpeta, termina con código 0 y
Vercel cancela el build.

## Variables de entorno

Ninguna se versiona. Cada carpeta tiene un `.env.example` con la lista
completa y qué significa cada una:

- `backend/.env.example` — base de datos, sesión, CORS, Cloudinary, seed
- `frontend/.env.example` — la URL de la API

## Orden de despliegue

Cada servicio necesita la URL del otro, así que la primera vez hay una vuelta:

1. **Railway** despliega el backend y da su dominio
2. **Vercel** despliega el frontend con esa URL en `VITE_API_URL`
3. **Railway** vuelve a cargar `CORS_ORIGINS` con el dominio de Vercel

Sin el paso 3 el panel inicia sesión y todo lo demás responde 401: la cookie
viaja entre dos sitios distintos y el navegador la descarta en silencio.
