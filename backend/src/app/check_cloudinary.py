"""Checks the Cloudinary setup end to end, without printing any secret.

    uv run python -m app.check_cloudinary

Reads the credentials from .env, uploads a tiny generated image to the folder
the app uses, prints the resulting URL and deletes it again. If this passes,
uploading a photo from the admin panel will work.
"""

import base64
import io
import sys

import cloudinary
import cloudinary.api
import cloudinary.uploader

from app.core.config import settings

# A 1x1 PNG: the smallest thing that is still a real image round trip.
PIXEL = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def masked(value: str) -> str:
    """Enough to tell whether a value is set and which one it is. Never the whole thing."""
    if not value:
        return "(vacío)"
    if len(value) <= 6:
        return "*" * len(value)
    return f"{value[:3]}…{value[-2:]}  ({len(value)} caracteres)"


def main() -> int:
    print("--- configuración ---")
    print(f"  cloud_name : {settings.cloudinary_cloud_name or '(vacío)'}")
    print(f"  api_key    : {masked(settings.cloudinary_api_key)}")
    print(f"  api_secret : {masked(settings.cloudinary_api_secret)}")
    print(f"  carpeta parejas  : {settings.cloudinary_teams_folder}")
    print(f"  carpeta sponsors : {settings.cloudinary_sponsors_folder}")

    if not settings.cloudinary_is_configured:
        print("\nFALTAN CREDENCIALES. Completá las tres variables en backend/.env")
        return 1

    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )

    print("\n--- probando la conexión ---")
    try:
        cloudinary.api.ping()
        print("  ping: OK")
    except Exception as error:
        print(f"  ping: FALLÓ -> {type(error).__name__}: {str(error)[:160]}")
        return 1

    print("\n--- subiendo una imagen de prueba ---")
    try:
        result = cloudinary.uploader.upload(
            io.BytesIO(PIXEL),
            folder=settings.cloudinary_teams_folder,
            public_id="prueba-de-conexion",
            overwrite=True,
        )
    except Exception as error:
        print(f"  subida: FALLÓ -> {type(error).__name__}: {str(error)[:200]}")
        return 1

    print(f"  subida: OK")
    print(f"  carpeta real : {result.get('folder') or result.get('asset_folder')}")
    print(f"  url          : {result['secure_url']}")

    print("\n--- borrando la prueba ---")
    cloudinary.uploader.destroy(result["public_id"])
    print("  borrada")

    print("\nTodo listo. Subir una foto desde el panel va a funcionar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
