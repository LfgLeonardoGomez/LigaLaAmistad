"""CSRF protection for cookie-authenticated browser mutations.

The admin session is a cookie and the API is cross-site from the Vercel UI.
Require both the exact configured browser origin and a non-simple header on
every unsafe route. Browsers preflight that header; an untrusted origin is not
authorized by CORSMiddleware and cannot send the mutation.
"""

from fastapi import HTTPException, Request, status

from app.core.config import settings

CSRF_HEADER = "x-requested-with"
CSRF_HEADER_VALUE = "XMLHttpRequest"


def require_same_origin(request: Request) -> None:
    """Reject unsafe requests without our UI origin and custom request header."""
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return

    origin = request.headers.get("origin")
    marker = request.headers.get(CSRF_HEADER)
    if origin not in settings.cors_origin_list or marker != CSRF_HEADER_VALUE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-site request rejected",
        )
