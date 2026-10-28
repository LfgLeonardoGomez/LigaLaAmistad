"""A sliding window rate limiter, kept in memory.

Enough to stop someone guessing admin passwords from a script. It is per
process, so it does not survive a restart and does not add up across
instances. If the API ever runs on more than one instance, this has to move to
Redis.
"""

import time

from fastapi import HTTPException, Request, status

_attempts: dict[str, list[float]] = {}
_window_seconds: dict[str, int] = {}
_next_gc_at = 0.0
_GC_INTERVAL_SECONDS = 60


def client_key(request: Request) -> str:
    """Return the transport peer, not an arbitrary client-supplied XFF value.

    Behind a reverse proxy this may identify the proxy rather than the caller.
    Extract forwarded client IPs only after configuring and verifying a trusted
    proxy boundary at the ASGI ingress.
    """
    # Do not accept X-Forwarded-For from arbitrary clients. It is only safe
    # when a trusted proxy boundary is configured by the ASGI deployment.
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
    global _next_gc_at
    now = time.monotonic()

    # Opportunistically reclaim inactive buckets, but throttle the full scan
    # so request cost does not grow linearly with the number of active peers.
    if now >= _next_gc_at:
        for bucket_key, stamps in list(_attempts.items()):
            bucket_cutoff = now - _window_seconds.get(bucket_key, window_seconds)
            recent_stamps = [stamp for stamp in stamps if stamp > bucket_cutoff]
            if recent_stamps:
                _attempts[bucket_key] = recent_stamps
            else:
                _attempts.pop(bucket_key, None)
                _window_seconds.pop(bucket_key, None)
        _next_gc_at = now + _GC_INTERVAL_SECONDS

    cutoff = now - window_seconds

    recent = [stamp for stamp in _attempts.get(key, []) if stamp > cutoff]
    _attempts[key] = recent
    _window_seconds[key] = window_seconds

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
        _window_seconds.pop(key, None)


def reset() -> None:
    """Wipe every counter. For tests."""
    global _next_gc_at
    _attempts.clear()
    _window_seconds.clear()
    _next_gc_at = 0.0
