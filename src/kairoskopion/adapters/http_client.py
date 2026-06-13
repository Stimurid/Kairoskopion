"""Shared HTTP client with caching and rate limiting.

Uses stdlib urllib.request — no external dependency required.
Caches responses as JSON files keyed by URL hash.
Rate limiter uses a simple per-host token-bucket approach.
"""

from __future__ import annotations

import dataclasses as dc
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Rate limiter (per-host, in-process only)
# ---------------------------------------------------------------------------

_rate_state: dict[str, float] = {}  # host -> last_request_time
_RATE_INTERVAL = 1.0  # seconds between requests to same host


def _rate_limit(host: str) -> None:
    """Block until at least _RATE_INTERVAL seconds since last request to host."""
    now = time.monotonic()
    last = _rate_state.get(host, 0.0)
    wait = _RATE_INTERVAL - (now - last)
    if wait > 0:
        time.sleep(wait)
    _rate_state[host] = time.monotonic()


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

_DEFAULT_CACHE_DIR = Path(".kairoskopion_cache")


def _cache_key(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]


def _cache_path(url: str, cache_dir: Path) -> Path:
    return cache_dir / f"{_cache_key(url)}.json"


def read_cache(url: str, *, cache_dir: Path | None = None,
               max_age_seconds: int = 86400) -> dict[str, Any] | None:
    """Read cached response if fresh enough. Returns None on miss."""
    cdir = cache_dir or _DEFAULT_CACHE_DIR
    path = _cache_path(url, cdir)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        cached_at = data.get("_cached_at", 0)
        if time.time() - cached_at > max_age_seconds:
            return None
        return data.get("body")
    except (json.JSONDecodeError, OSError):
        return None


def write_cache(url: str, body: Any, *, cache_dir: Path | None = None) -> None:
    """Write response body to cache."""
    cdir = cache_dir or _DEFAULT_CACHE_DIR
    cdir.mkdir(parents=True, exist_ok=True)
    path = _cache_path(url, cdir)
    payload = {"url": url, "_cached_at": time.time(), "body": body}
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Structured HTTP result
# ---------------------------------------------------------------------------

@dc.dataclass
class HttpResult:
    """Structured HTTP response or error."""

    ok: bool
    status_code: int = 200
    body: Any = None
    text: str = ""
    error: str = ""
    url: str = ""
    from_cache: bool = False

    def to_dict(self) -> dict[str, Any]:
        return dc.asdict(self)


# ---------------------------------------------------------------------------
# HTTP errors
# ---------------------------------------------------------------------------

class HttpError(Exception):
    """Non-retryable HTTP error."""
    def __init__(self, status: int, message: str, url: str):
        super().__init__(f"HTTP {status}: {message} (url={url})")
        self.status = status
        self.url = url


# ---------------------------------------------------------------------------
# HTTP fetch functions
# ---------------------------------------------------------------------------

def _build_request(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    user_agent: str = "Kairoskopion/0.2 (https://github.com/Stimurid/Kairoskopion; mailto:kairoskopion@proton.me)",
    accept: str = "application/json",
) -> urllib.request.Request:
    hdrs = {"User-Agent": user_agent, "Accept": accept}
    if headers:
        hdrs.update(headers)
    return urllib.request.Request(url, headers=hdrs)


def fetch_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
    cache_dir: Path | None = None,
    max_cache_age: int = 86400,
    rate_limit: bool = True,
    user_agent: str = "Kairoskopion/0.2 (https://github.com/Stimurid/Kairoskopion; mailto:kairoskopion@proton.me)",
) -> dict[str, Any]:
    """Fetch JSON from URL with caching and rate limiting.

    Returns parsed JSON body. Raises HttpError on non-200 responses.
    """
    cached = read_cache(url, cache_dir=cache_dir, max_age_seconds=max_cache_age)
    if cached is not None:
        return cached

    if rate_limit:
        from urllib.parse import urlparse
        host = urlparse(url).hostname or "unknown"
        _rate_limit(host)

    req = _build_request(url, headers=headers, user_agent=user_agent)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            body = json.loads(raw)
    except urllib.error.HTTPError as exc:
        raise HttpError(exc.code, exc.reason, url) from exc
    except urllib.error.URLError as exc:
        raise HttpError(0, str(exc.reason), url) from exc

    write_cache(url, body, cache_dir=cache_dir)
    return body


def fetch_json_safe(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
    cache_dir: Path | None = None,
    max_cache_age: int = 86400,
    rate_limit: bool = True,
    user_agent: str = "Kairoskopion/0.2 (https://github.com/Stimurid/Kairoskopion; mailto:kairoskopion@proton.me)",
    retry_count: int = 2,
) -> HttpResult:
    """Fetch JSON without raising — returns HttpResult with ok/error."""
    cached = read_cache(url, cache_dir=cache_dir, max_age_seconds=max_cache_age)
    if cached is not None:
        return HttpResult(ok=True, body=cached, url=url, from_cache=True)

    if rate_limit:
        from urllib.parse import urlparse
        host = urlparse(url).hostname or "unknown"
        _rate_limit(host)

    last_error = ""
    for attempt in range(max(1, retry_count)):
        try:
            req = _build_request(url, headers=headers, user_agent=user_agent)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                body = json.loads(raw)
                write_cache(url, body, cache_dir=cache_dir)
                return HttpResult(ok=True, body=body, url=url)
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                return HttpResult(
                    ok=False, status_code=429,
                    error="rate_limited", url=url,
                )
            if exc.code == 404:
                return HttpResult(
                    ok=False, status_code=404,
                    error="not_found", url=url,
                )
            last_error = f"HTTP {exc.code}: {exc.reason}"
        except urllib.error.URLError as exc:
            last_error = f"network: {exc.reason}"
        except json.JSONDecodeError as exc:
            return HttpResult(
                ok=False, status_code=200,
                error="invalid_response", url=url,
            )
        except OSError as exc:
            last_error = f"timeout_or_io: {exc}"

    return HttpResult(ok=False, error=last_error, url=url)


def fetch_text_safe(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
    rate_limit: bool = True,
    user_agent: str = "Kairoskopion/0.2 (https://github.com/Stimurid/Kairoskopion; mailto:kairoskopion@proton.me)",
    retry_count: int = 2,
) -> HttpResult:
    """Fetch text/HTML without raising — returns HttpResult."""
    if rate_limit:
        from urllib.parse import urlparse
        host = urlparse(url).hostname or "unknown"
        _rate_limit(host)

    last_error = ""
    for attempt in range(max(1, retry_count)):
        try:
            req = _build_request(
                url, headers=headers, user_agent=user_agent,
                accept="text/html,application/xhtml+xml,*/*",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                text = resp.read().decode("utf-8", errors="replace")
                return HttpResult(ok=True, text=text, url=url)
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                return HttpResult(ok=False, status_code=429, error="rate_limited", url=url)
            if exc.code == 404:
                return HttpResult(ok=False, status_code=404, error="not_found", url=url)
            last_error = f"HTTP {exc.code}: {exc.reason}"
        except urllib.error.URLError as exc:
            last_error = f"network: {exc.reason}"
        except OSError as exc:
            last_error = f"timeout_or_io: {exc}"

    return HttpResult(ok=False, error=last_error, url=url)
