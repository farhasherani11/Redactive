"""
API key auth + rate limiting for /analyze.

Now that Redactive is deployed to a public URL, this endpoint needs to be
protected — otherwise anyone who finds the link can burn through the Groq
quota or hammer the service. Two layers here, checked in order:

1. API key check: the request must include a header `X-API-Key` matching
   REDACTIVE_API_KEY. This is intentionally simple — a single shared key,
   not per-user accounts — appropriate for a personal project with one
   owner (you) and one client (the Chrome extension, later).

2. Rate limiting: even with a valid key, no more than RATE_LIMIT requests
   per RATE_LIMIT_WINDOW_SECONDS are allowed. Implemented as a simple
   in-memory sliding window — no new dependency needed, and honest about
   its limitation: this resets on server restart and does not share state
   across multiple server instances. Fine for a single free-tier instance;
   would need a shared store (e.g. Redis) to scale beyond that.
"""

import time
from collections import defaultdict, deque
from fastapi import Header, HTTPException
from app.config import REDACTIVE_API_KEY

RATE_LIMIT = 30
RATE_LIMIT_WINDOW_SECONDS = 60

# Maps API key -> deque of request timestamps within the current window.
_request_log: dict[str, deque] = defaultdict(deque)


def verify_api_key(x_api_key: str = Header(default=None)) -> str:
    """
    FastAPI dependency. Raises 401 if the key is missing/wrong, raises 429
    if the key is valid but over the rate limit. Returns the key on success
    so it can be used as the rate-limit bucket identifier.
    """
    if not REDACTIVE_API_KEY:
        # No key configured server-side — auth is effectively open.
        # Intended for local development only; deployed instances should
        # always have REDACTIVE_API_KEY set.
        return "unauthenticated-local-dev"

    if x_api_key != REDACTIVE_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")

    _enforce_rate_limit(x_api_key)
    return x_api_key


def _enforce_rate_limit(key: str) -> None:
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS
    timestamps = _request_log[key]

    # Drop timestamps outside the current window.
    while timestamps and timestamps[0] < window_start:
        timestamps.popleft()

    if len(timestamps) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: max {RATE_LIMIT} requests per {RATE_LIMIT_WINDOW_SECONDS}s.",
        )

    timestamps.append(now)
