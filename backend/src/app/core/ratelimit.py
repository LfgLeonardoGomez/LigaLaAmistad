"""A sliding window rate limiter, kept in memory.

Enough to stop someone guessing admin passwords from a script. It is per
process, so it does not survive a restart and does not add up across instances.
If the API ever runs on more than one instance, this has to move to Redis.
"""

import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

_attempts: dict[str, list[float]] = defaultdict(list)


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def check_rate_limit(request: Request, max_attempts: int, window_seconds: int) -> None:
    """Raise 429 when this client used up its attempts inside the window."""
    key = _client_key(request)
    now = time.monotonic()
    cutoff = now - window_seconds

    recent = [stamp for stamp in _attempts[key] if stamp > cutoff]
    _attempts[key] = recent

    if len(recent) >= max_attempts:
        retry_after = int(recent[0] + window_seconds - now) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later",
            headers={"Retry-After": str(retry_after)},
        )

    _attempts[key].append(now)


def clear_attempts(request: Request) -> None:
    """Forget this client's attempts. Called after a successful login."""
    _attempts.pop(_client_key(request), None)


def reset() -> None:
    """Wipe every counter. For tests."""
    _attempts.clear()
