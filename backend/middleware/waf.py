"""
Simple WAF (Web Application Firewall) middleware.
Blocks common SQL injection and XSS patterns in request parameters.
"""
import logging
import re
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# Patterns that indicate SQL injection attempts
_SQL_PATTERNS = [
    re.compile(r"(?:--|;)\s*(DROP|ALTER|TRUNCATE|DELETE|INSERT|UPDATE)\s", re.IGNORECASE),
    re.compile(r"UNION\s+(ALL\s+)?SELECT", re.IGNORECASE),
    re.compile(r"'\s*OR\s+'?\d*'?\s*=\s*'?\d*'?", re.IGNORECASE),
    re.compile(r"'\s*;\s*(DROP|ALTER|TRUNCATE)", re.IGNORECASE),
    re.compile(r"(SLEEP|BENCHMARK|WAITFOR)\s*\(", re.IGNORECASE),
    re.compile(r"0x[0-9a-fA-F]{8,}", re.IGNORECASE),  # hex-encoded payloads
]

# Patterns that indicate XSS attempts
_XSS_PATTERNS = [
    re.compile(r"<script[\s>]", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"on(load|error|click|mouseover|focus|blur)\s*=", re.IGNORECASE),
    re.compile(r"<iframe[\s>]", re.IGNORECASE),
    re.compile(r"<object[\s>]", re.IGNORECASE),
    re.compile(r"eval\s*\(", re.IGNORECASE),
    re.compile(r"document\.(cookie|location|write)", re.IGNORECASE),
]

# Exempt paths (e.g. legal text editing, email templates that contain HTML)
_EXEMPT_PATHS = {"/api/email-templates", "/api/legal"}


def _check_value(value: str) -> str | None:
    """Check a string value for malicious patterns. Returns pattern type or None."""
    for pat in _SQL_PATTERNS:
        if pat.search(value):
            return "sql_injection"
    for pat in _XSS_PATTERNS:
        if pat.search(value):
            return "xss"
    return None


class WAFMiddleware(BaseHTTPMiddleware):
    """Lightweight WAF that inspects query params, path, and small request bodies."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip exempt paths
        for exempt in _EXEMPT_PATHS:
            if path.startswith(exempt):
                return await call_next(request)

        # Check query parameters
        for key, value in request.query_params.items():
            threat = _check_value(value)
            if threat:
                logger.warning(f"WAF blocked {threat} in query param '{key}' from {request.client.host}: {value[:100]}")
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Požadavek zablokován bezpečnostním filtrem"},
                )

        # Check path segments
        for segment in path.split("/"):
            if len(segment) > 4:  # skip short segments like 'api'
                threat = _check_value(segment)
                if threat:
                    logger.warning(f"WAF blocked {threat} in path from {request.client.host}: {segment[:100]}")
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "Požadavek zablokován bezpečnostním filtrem"},
                    )

        # Check small JSON bodies (POST/PUT/PATCH) — only up to 10KB to avoid perf issues
        if request.method in ("POST", "PUT", "PATCH"):
            content_type = request.headers.get("content-type", "")
            content_length = int(request.headers.get("content-length", "0") or "0")
            if "application/json" in content_type and 0 < content_length <= 10240:
                body = await request.body()
                body_str = body.decode("utf-8", errors="ignore")
                threat = _check_value(body_str)
                if threat:
                    logger.warning(f"WAF blocked {threat} in body from {request.client.host}: {body_str[:200]}")
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "Požadavek zablokován bezpečnostním filtrem"},
                    )

        return await call_next(request)
