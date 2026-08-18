from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import admin_users_router
from app.auth.router import router as auth_router
from app.core.config import settings
from app.matches.router import router as matches_router
from app.public.router import router as public_router
from app.sponsors.router import router as sponsors_router
from app.teams.router import router as teams_router

app = FastAPI(title="Liga La Amistad API")

# The schema is owned by Alembic: run `alembic upgrade head` before starting.
# Creating tables here would hide a migration that was never applied.

app.add_middleware(
    CORSMiddleware,
    # Never "*" here: browsers drop credentials on a wildcard origin, and the
    # whole admin session travels in a cookie.
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(public_router)
app.include_router(auth_router)
app.include_router(admin_users_router)
app.include_router(teams_router)
app.include_router(matches_router)
app.include_router(sponsors_router)


@app.get("/health", tags=["health"])
def health():
    """Liveness plus the settings that decide whether a session can survive.

    None of this is secret — the cookie attributes are visible in any login
    response — and having it in one place turns "the panel logs me out on
    refresh" from a guess into a fact.
    """
    return {
        "status": "ok",
        "cookie": {
            "samesite": settings.cookie_samesite,
            "secure": settings.cookie_secure,
        },
        "cors_origins": settings.cors_origin_list,
        # Whether image uploads will work at all. A boolean, never the keys.
        "cloudinary": settings.cloudinary_is_configured,
    }
