"""Rate limiting configuration and middleware (P2-5 — /api/analyze rate limit)."""
from __future__ import annotations

from fastapi import Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# Create limiter instance with remote address key (supports proxies)
# Pass config_filename=None to prevent automatic .env loading (encoding issues on Windows)
limiter = Limiter(key_func=get_remote_address, config_filename=None)


def rate_limit_error_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Custom error handler for rate limit exceeded (HTTP 429)."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "detail": f"Rate limit exceeded. {exc.detail}",
            "error": "rate_limit_exceeded",
        },
    )


# Rate limit configurations (can be overridden via environment)
ANALYZE_RATE_LIMIT = "5/minute"  # 5 requests per minute on POST /api/analyze
SEARCH_RATE_LIMIT = "10/minute"  # 10 requests per minute on POST /api/search
JOBS_RATE_LIMIT = "20/minute"    # 20 requests per minute on GET /api/jobs/{job_id}
