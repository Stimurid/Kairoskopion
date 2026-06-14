"""Environment-driven auth/proxy config for zero-cost API improvements.

Per `docs/AUTH_AND_PROXY_API_LANDSCAPE.md` §6 items 1–5: these are
all free and only require the operator to set an env var. None are
required for the system to work; every adapter degrades cleanly when
the env var is unset.

Supported env vars (all optional):

  - KAIROSKOPION_OPENALEX_MAILTO
    Polite-pool email for OpenAlex. Appended as `?mailto=...` on
    every OpenAlex request. ~10× rate-limit headroom.

  - KAIROSKOPION_CROSSREF_MAILTO
    Same trick for Crossref polite pool.

  - KAIROSKOPION_SEMANTIC_SCHOLAR_API_KEY
    Free-tier S2 API key. Sent as `x-api-key` header. 10× rate limit.

  - KAIROSKOPION_ORCID_CLIENT_ID
  - KAIROSKOPION_ORCID_CLIENT_SECRET
    ORCID Public API OAuth client credentials. Free.

  - KAIROSKOPION_CORE_API_KEY
    CORE API key (free academic tier). Bearer token.

Strict no-secrets-in-repo: this module only READS env vars. The
`.env.example` shows the names; the real values must live in a local
`.env` that is gitignored. No code path here writes or logs the
values themselves — only their presence.
"""

from __future__ import annotations

import logging
import os
from typing import Any
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


def _get(name: str) -> str | None:
    v = os.environ.get(name)
    return v.strip() if v and v.strip() else None


def openalex_mailto() -> str | None:
    """Return the configured OpenAlex polite-pool mailto, or None."""
    return _get("KAIROSKOPION_OPENALEX_MAILTO")


def crossref_mailto() -> str | None:
    return _get("KAIROSKOPION_CROSSREF_MAILTO")


def semantic_scholar_api_key() -> str | None:
    return _get("KAIROSKOPION_SEMANTIC_SCHOLAR_API_KEY")


def orcid_client_credentials() -> tuple[str, str] | None:
    cid = _get("KAIROSKOPION_ORCID_CLIENT_ID")
    sec = _get("KAIROSKOPION_ORCID_CLIENT_SECRET")
    if cid and sec:
        return (cid, sec)
    return None


def core_api_key() -> str | None:
    return _get("KAIROSKOPION_CORE_API_KEY")


def append_qs(url: str, params: dict[str, str]) -> str:
    """Safely append query params to a URL.

    Used for `mailto=` style polite-pool params. If url already has a
    `?`, uses `&`; otherwise `?`.
    """
    if not params:
        return url
    sep = "&" if "?" in url else "?"
    return url + sep + urlencode(params)


def openalex_polite_url(url: str) -> str:
    """Add mailto polite-pool param if configured.

    Idempotent: if the URL already carries `mailto=` it is returned
    unchanged.
    """
    mt = openalex_mailto()
    if not mt:
        return url
    if "mailto=" in url:
        return url
    return append_qs(url, {"mailto": mt})


def crossref_polite_url(url: str) -> str:
    mt = crossref_mailto()
    if not mt:
        return url
    if "mailto=" in url:
        return url
    return append_qs(url, {"mailto": mt})


def config_summary() -> dict[str, Any]:
    """Boolean presence summary — never log actual values."""
    return {
        "openalex_mailto_configured": openalex_mailto() is not None,
        "crossref_mailto_configured": crossref_mailto() is not None,
        "semantic_scholar_key_configured": semantic_scholar_api_key() is not None,
        "orcid_client_credentials_configured":
            orcid_client_credentials() is not None,
        "core_api_key_configured": core_api_key() is not None,
    }
