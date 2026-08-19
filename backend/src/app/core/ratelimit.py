"""A sliding window rate limiter, kept in memory.

Enough to stop someone guessing admin passwords from a script. It is per
process, so it does not survive a restart and does not add up across
instances. If the API ever runs on more than one instance, this has to move to
Redis.
"""

import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

_attempts: dict[str, list[float]] = defaultdict(list)


def client_key(request: Request) -> str:
    """Who is knocking, as far as this can be known behind a proxy.

    `request.client.host` is the address of whatever spoke to the server last.
    On a platform that routes through a fleet of edge servers that is the edge,
    not the caller, and it can differ between two requests from the same
    person — which silently turns the limit off. The forwarded header is the
    only place the original address survives.

    Treat this as best effort: a caller can put whatever they like in that
    header. The per-email limit below is the one that actually holds.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else "unknown"


def check_rate_limit(
    key: str,
    max_attempts: int,
    window_seconds: int,
    detail: str = "Too many login attempts. Try again later",
) -> None:
    """Raise 429 when this key used up its attempts inside the window.

    `detail` is a parameter because this now guards more than the login: a
    voter told to slow down should not be read an error about passwords.
    """
    now = time.monotonic()
    cutoff = now - window_seconds

    recent = [stamp for stamp in _attempts[key] if stamp > cutoff]
    _attempts[key] = recent

    if len(recent) >= max_attempts:
        retry_after = int(recent[0] + window_seconds - now) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"Retry-After": str(retry_after)},
        )

    _attempts[key].append(now)


def clear_attempts(*keys: str) -> None:
    """Forget these keys. Called after a successful login."""
    for key in keys:
        _attempts.pop(key, None)


def reset() -> None:
    """Wipe every counter. For tests."""
    _attempts.clear()
