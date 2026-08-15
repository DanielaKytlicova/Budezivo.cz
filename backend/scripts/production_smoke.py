"""Read-only production smoke checks for pilot operations.

This script only performs HTTP GET requests. It does not require production
secrets and never writes to the database.
"""
import json
import os
import sys
from datetime import datetime, timezone
from typing import Callable, Iterable, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


DEFAULT_API_BASE_URL = "https://api.budezivo.cz"
DEFAULT_FRONTEND_BASE_URL = "https://www.budezivo.cz"
DEFAULT_FRONTEND_PATHS = ("/", "/gdpr", "/obchodni-podminky")


def normalize_base_url(value: str, fallback: str) -> str:
    value = (value or "").strip() or fallback
    return value.rstrip("/")


def parse_csv_paths(value: Optional[str]) -> list:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def build_url(base_url: str, path_or_url: str) -> str:
    parsed = urlparse(path_or_url)
    if parsed.scheme and parsed.netloc:
        return path_or_url
    return urljoin(f"{base_url}/", path_or_url.lstrip("/"))


def fetch_url(url: str, timeout: float) -> tuple:
    request = Request(url, headers={"User-Agent": "BudezivoPilotSmoke/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - operator smoke test URL is controlled
            return response.status, response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body
    except URLError as exc:
        return 0, str(exc.reason)
    except TimeoutError:
        return 0, "timeout"


def http_check(
    name: str,
    url: str,
    timeout: float,
    fetch: Callable[[str, float], tuple] = fetch_url,
) -> dict:
    status_code, body = fetch(url, timeout)
    ok = 200 <= status_code < 400
    return {
        "name": name,
        "status": "ok" if ok else "failed",
        "url": url,
        "status_code": status_code,
        "body_preview": body[:120] if not ok else "",
    }


def ready_check(
    url: str,
    timeout: float,
    fetch: Callable[[str, float], tuple] = fetch_url,
) -> dict:
    status_code, body = fetch(url, timeout)
    result = {
        "name": "api_ready",
        "status": "failed",
        "url": url,
        "status_code": status_code,
        "body_preview": "",
    }
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        result["body_preview"] = body[:120]
        return result

    ready = payload.get("ready") is True
    readiness_status = payload.get("status")
    result["readiness_status"] = readiness_status
    if status_code == 200 and ready and readiness_status in {"ok", "degraded"}:
        result["status"] = "ok"
    else:
        result["body_preview"] = json.dumps(payload, ensure_ascii=False)[:120]
    return result


def collect_report(
    *,
    api_base_url: str,
    frontend_base_url: str,
    booking_paths: Iterable[str],
    timeout: float = 15.0,
    fetch: Callable[[str, float], tuple] = fetch_url,
) -> dict:
    api_base_url = normalize_base_url(api_base_url, DEFAULT_API_BASE_URL)
    frontend_base_url = normalize_base_url(frontend_base_url, DEFAULT_FRONTEND_BASE_URL)

    checks = [
        http_check("api_health", build_url(api_base_url, "/health"), timeout, fetch),
        ready_check(build_url(api_base_url, "/ready"), timeout, fetch),
    ]
    checks.extend(
        http_check(f"frontend{path}", build_url(frontend_base_url, path), timeout, fetch)
        for path in DEFAULT_FRONTEND_PATHS
    )

    booking_paths = list(booking_paths)
    if booking_paths:
        checks.extend(
            http_check(f"booking:{path}", build_url(frontend_base_url, path), timeout, fetch)
            for path in booking_paths
        )
        booking_status = "checked"
    else:
        booking_status = "skipped"

    status = "ok" if all(check["status"] == "ok" for check in checks) else "attention_required"
    return {
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "booking_paths": booking_status,
        "checks": checks,
    }


def main() -> int:
    timeout = float(os.environ.get("PRODUCTION_SMOKE_TIMEOUT", "15"))
    report = collect_report(
        api_base_url=os.environ.get("PRODUCTION_API_BASE_URL", DEFAULT_API_BASE_URL),
        frontend_base_url=os.environ.get("PRODUCTION_FRONTEND_BASE_URL", DEFAULT_FRONTEND_BASE_URL),
        booking_paths=parse_csv_paths(os.environ.get("PILOT_BOOKING_PATHS")),
        timeout=timeout,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
