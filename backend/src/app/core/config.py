from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# HS256 signs with SHA256, whose block size is 32 bytes. A shorter key weakens
# the signature, and PyJWT only warns about it.
MIN_SECRET_KEY_LENGTH = 32


class Settings(BaseSettings):
    """Application settings, read from environment variables or a local .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # postgresql+psycopg://user:password@host:port/database
    database_url: str = "postgresql+psycopg://liga:liga@localhost:5433/liga"

    # Override in production. Changing it invalidates every issued token.
    secret_key: str = "dev-only-secret-replace-this-before-deploying"
    access_token_expire_minutes: int = 60 * 8

    # Cookies must be sent over HTTPS in production.
    cookie_secure: bool = False

    # "lax" is right while both sides share a site, which includes two ports on
    # localhost. Once the front end is on Vercel and the API on Railway they are
    # different sites, and only "none" (which requires cookie_secure) is sent.
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    # Comma separated. Browsers refuse credentials when the origin is "*", so
    # every front end origin has to be listed explicitly.
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Login attempts allowed per IP inside the window, before answering 429.
    login_max_attempts: int = 10
    login_window_seconds: int = 300

    # Image hosting. Uploads are rejected with 503 while these are empty.
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""

    # Where each kind of image lands in the Cloudinary media library. They must
    # match the folders that exist in the account, or Cloudinary creates them.
    cloudinary_teams_folder: str = "parejas-liga-la-amistad"
    cloudinary_sponsors_folder: str = "sponsors-liga-la-amistad"

    @field_validator("secret_key")
    @classmethod
    def _reject_weak_secret(cls, value: str) -> str:
        if len(value) < MIN_SECRET_KEY_LENGTH:
            raise ValueError(
                f"SECRET_KEY must be at least {MIN_SECRET_KEY_LENGTH} characters. "
                'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )
        return value

    @field_validator("database_url")
    @classmethod
    def _force_psycopg_driver(cls, value: str) -> str:
        """Managed hosts hand out `postgres://` or `postgresql://` URLs.

        SQLAlchemy maps both to psycopg2, which this project does not install.
        Rewriting the scheme here means the deploy works with the URL as given.
        """
        for prefix in ("postgresql://", "postgres://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix) :]
        return value

    @model_validator(mode="after")
    def _samesite_none_requires_secure(self) -> "Settings":
        """Browsers silently drop a SameSite=None cookie that is not Secure.

        Silently: no console error, no network error. The session simply never
        arrives. Failing at startup is far cheaper than debugging that.
        """
        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise ValueError(
                "COOKIE_SAMESITE=none requires COOKIE_SECURE=true, "
                "or browsers will discard the session cookie"
            )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def cloudinary_is_configured(self) -> bool:
        return all(
            [
                self.cloudinary_cloud_name,
                self.cloudinary_api_key,
                self.cloudinary_api_secret,
            ]
        )


settings = Settings()
