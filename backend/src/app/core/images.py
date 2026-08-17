"""Image uploads.

The backend never serves image files: it receives the upload, forwards it to
Cloudinary and stores only the returned URL.

The upload call blocks, so the endpoints that use this must be plain `def`
functions. FastAPI then runs them in its thread pool instead of stalling the
event loop.
"""

import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def upload_image(file: UploadFile, folder: str) -> str:
    """Upload an image and return its public URL."""
    if not settings.cloudinary_is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Image upload is not configured",
        )

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image type. Allowed: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}",
        )

    content = file.file.read()
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Image is larger than {MAX_IMAGE_BYTES // (1024 * 1024)} MB",
        )

    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )

    try:
        result = cloudinary.uploader.upload(content, folder=folder)
    except Exception as error:  # network, credentials, quota — all look the same here
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Image upload failed",
        ) from error

    return result["secure_url"]
