"""
Redis-backed Rate Limiting Middleware for ParallaxAI.
Protects authentication, AI inference, file uploads, and general API endpoints
with configurable per-IP and per-user rate limits, HTTP 429 responses,
Retry-After headers, and safe in-memory fallback if Redis is unavailable.
"""

import time
from typing import Dict, Optional, Tuple
import redis
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from backend.core.config import settings
from backend.core.security import decode_access_token


class RateLimiterStore:
    """
    Dual-mode rate limiter store:
    - Uses Redis atomic INCR + EXPIRE when Redis is reachable.
    - Gracefully falls back to an in-memory fixed-window dictionary if Redis is unreachable.
    """

    def __init__(self) -> None:
        self._redis_client: Optional[redis.Redis] = None
        self._redis_checked_at: float = 0.0
        self._redis_available: bool = False
        self._memory_windows: Dict[str, Tuple[int, int]] = {}

    def _get_redis(self) -> Optional[redis.Redis]:
        now = time.time()
        if self._redis_client is not None and (now - self._redis_checked_at) < 10.0:
            return self._redis_client if self._redis_available else None

        self._redis_checked_at = now
        try:
            if self._redis_client is None:
                self._redis_client = redis.Redis.from_url(
                    settings.REDIS_URL,
                    socket_connect_timeout=1.0,
                    socket_timeout=1.0,
                    decode_responses=True,
                )
            self._redis_client.ping()
            self._redis_available = True
            return self._redis_client
        except Exception:
            self._redis_available = False
            return None

    def increment_and_check(
        self, bucket_key: str, limit: int, window_seconds: int
    ) -> Tuple[bool, int, int, int]:
        """
        Increment the counter for bucket_key within the current time window.
        Returns: (allowed, current_count, remaining, retry_after_seconds)
        """
        now = int(time.time())
        window_start = (now // window_seconds) * window_seconds
        window_reset = window_start + window_seconds
        retry_after = max(1, window_reset - now)
        full_key = f"parallaxai:rl:{bucket_key}:{window_start}"

        r = self._get_redis()
        if r is not None:
            try:
                pipe = r.pipeline()
                pipe.incr(full_key, 1)
                pipe.expire(full_key, window_seconds + 2)
                results = pipe.execute()
                current_count = int(results[0])
                allowed = current_count <= limit
                remaining = max(0, limit - current_count)
                return allowed, current_count, remaining, retry_after
            except Exception:
                self._redis_available = False

        # Safe fallback: in-memory window counter
        # Prune expired keys occasionally
        if len(self._memory_windows) > 5000:
            expired_keys = [
                k for k, (_, exp_ts) in self._memory_windows.items() if exp_ts <= now
            ]
            for k in expired_keys:
                self._memory_windows.pop(k, None)

        count, exp_ts = self._memory_windows.get(full_key, (0, window_reset))
        if exp_ts <= now:
            count = 0
            exp_ts = window_reset
        count += 1
        self._memory_windows[full_key] = (count, exp_ts)
        allowed = count <= limit
        remaining = max(0, limit - count)
        return allowed, count, remaining, retry_after

    def reset_all(self) -> None:
        """Clear all rate-limit counters in both Redis and memory."""
        self._memory_windows.clear()
        r = self._get_redis()
        if r is not None:
            try:
                keys = list(r.scan_iter("parallaxai:rl:*"))
                if keys:
                    r.delete(*keys)
            except Exception:
                pass


rate_limiter_store = RateLimiterStore()


def reset_rate_limits() -> None:
    """Public helper to clear rate-limit counters (used in test suites)."""
    rate_limiter_store.reset_all()


def _extract_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


def _extract_user_or_ip(request: Request) -> str:
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        if token:
            try:
                payload = decode_access_token(token)
                uid = payload.get("uid") or payload.get("sub")
                if uid:
                    return f"user:{uid}"
            except Exception:
                pass
    return f"ip:{_extract_client_ip(request)}"


def classify_rate_limit(request: Request) -> Optional[Tuple[str, int, int]]:
    """
    Determine (bucket_key, limit, window_seconds) for a request,
    or None if the endpoint is exempt from rate limiting (e.g. health check, docs, OPTIONS).
    """
    if request.method == "OPTIONS":
        return None

    path = request.url.path.rstrip("/") or "/"
    if path in ("/health", "/api/v1/system/health", "/docs", "/openapi.json", "/redoc"):
        return None

    client_ip = f"ip:{_extract_client_ip(request)}"

    # 1. Login: 5 requests / minute / IP
    if path in ("/api/v1/auth/login", "/api/auth/login") and request.method == "POST":
        return (
            f"login:{client_ip}",
            settings.RATE_LIMIT_LOGIN_PER_MINUTE,
            60,
        )

    # 2. Registration: 3 requests / hour / IP
    if path == "/api/v1/auth/register" and request.method == "POST":
        return (
            f"register:{client_ip}",
            settings.RATE_LIMIT_REGISTER_PER_HOUR,
            3600,
        )

    # 3. Password reset: 3 requests / hour / IP
    if path in ("/api/v1/auth/forgot-password", "/api/v1/auth/reset-password") and request.method == "POST":
        return (
            f"pwreset:{client_ip}",
            settings.RATE_LIMIT_PASSWORD_RESET_PER_HOUR,
            3600,
        )

    # 4. AI Inference endpoints: 10 requests / minute / user
    is_ai_route = (
        path in ("/api/ai/analyze-decision", "/api/ai/detect-bias")
        or (path.startswith("/api/v1/decisions/") and path.endswith("/analyze"))
        or path.startswith("/api/v1/bias/analyze/")
    )
    if is_ai_route and request.method == "POST":
        actor = _extract_user_or_ip(request)
        return (
            f"ai_inference:{actor}",
            settings.RATE_LIMIT_AI_PER_MINUTE,
            60,
        )

    # 5. File upload endpoints: 10 requests / hour / user
    if "/upload" in path and request.method in ("POST", "PUT"):
        actor = _extract_user_or_ip(request)
        return (
            f"upload:{actor}",
            settings.RATE_LIMIT_UPLOAD_PER_HOUR,
            3600,
        )

    # 6. General API endpoints: 100 requests / minute / user
    if path.startswith("/api/"):
        actor = _extract_user_or_ip(request)
        return (
            f"api:{actor}",
            settings.RATE_LIMIT_API_PER_MINUTE,
            60,
        )

    return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        classification = classify_rate_limit(request)
        if classification is None:
            return await call_next(request)

        bucket_key, limit, window_seconds = classification
        allowed, current_count, remaining, retry_after = (
            rate_limiter_store.increment_and_check(bucket_key, limit, window_seconds)
        )

        rate_headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(retry_after),
        }

        if not allowed:
            rate_headers["Retry-After"] = str(retry_after)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"Rate limit exceeded ({limit} requests per {window_seconds}s). Please retry after {retry_after} seconds.",
                    "error": "too_many_requests",
                    "limit": limit,
                    "window_seconds": window_seconds,
                    "retry_after": retry_after,
                },
                headers=rate_headers,
            )

        response = await call_next(request)
        for header_name, header_val in rate_headers.items():
            response.headers[header_name] = header_val
        return response

