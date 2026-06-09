"""Freshness / staleness tracking for sources and adapter results.

Assesses how current a SourceSnapshot or AdapterResult is relative to
a policy. No network refresh — purely local metadata assessment.
"""

from __future__ import annotations

import dataclasses as dc
from datetime import datetime, timezone
from typing import Any

from .enums import StalenessStatus
from .schema import _DictMixin, _field, _now


@dc.dataclass
class FreshnessPolicy(_DictMixin):
    fresh_hours: int = 168
    aging_hours: int = 720
    stale_hours: int = 2160
    name: str = "default"


_DEFAULT_POLICY = FreshnessPolicy()


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None


def _hours_since(ts_str: str | None) -> float | None:
    dt = _parse_iso(ts_str)
    if dt is None:
        return None
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = now - dt
    return delta.total_seconds() / 3600


def assess_freshness(
    retrieved_at: str | None,
    *,
    is_mock: bool = False,
    policy: FreshnessPolicy | None = None,
) -> str:
    """Assess freshness status of a timestamped item.

    Mock items always return 'mock'. Items without timestamps return 'unknown'.
    """
    if is_mock:
        return "mock"

    hours = _hours_since(retrieved_at)
    if hours is None:
        return StalenessStatus.UNKNOWN_FRESHNESS.value

    p = policy or _DEFAULT_POLICY
    if hours <= p.fresh_hours:
        return StalenessStatus.FRESH.value
    if hours <= p.aging_hours:
        return StalenessStatus.POSSIBLY_STALE.value
    if hours <= p.stale_hours:
        return StalenessStatus.STALE.value
    return StalenessStatus.EXPIRED.value


def assess_source_freshness(
    source_snapshot: dict[str, Any],
    policy: FreshnessPolicy | None = None,
) -> dict[str, Any]:
    """Assess freshness of a SourceSnapshot dict.

    Returns a dict with freshness_status, hours_since_retrieval, next_review_after.
    """
    retrieved_at = source_snapshot.get("retrieved_at")
    parser = source_snapshot.get("parser_used", "")
    is_mock = "mock" in parser.lower() if parser else False

    status = assess_freshness(retrieved_at, is_mock=is_mock, policy=policy)
    hours = _hours_since(retrieved_at)

    p = policy or _DEFAULT_POLICY
    next_review = None
    if status == StalenessStatus.FRESH.value and hours is not None:
        next_review = f"{p.fresh_hours - hours:.0f} hours"

    return {
        "snapshot_id": source_snapshot.get("snapshot_id"),
        "freshness_status": status,
        "hours_since_retrieval": round(hours, 1) if hours is not None else None,
        "next_review_after": next_review,
        "policy_name": p.name,
    }


def assess_adapter_result_freshness(
    adapter_result: dict[str, Any],
    policy: FreshnessPolicy | None = None,
) -> dict[str, Any]:
    """Assess freshness of an AdapterResult dict.

    Mock adapter results always return 'mock' status.
    """
    is_mock = adapter_result.get("is_mock", True)
    retrieved_at = adapter_result.get("retrieved_at")

    status = assess_freshness(retrieved_at, is_mock=is_mock, policy=policy)
    hours = _hours_since(retrieved_at)

    return {
        "adapter_result_id": adapter_result.get("adapter_result_id"),
        "adapter_name": adapter_result.get("adapter_name"),
        "freshness_status": status,
        "hours_since_retrieval": round(hours, 1) if hours is not None else None,
        "is_mock": is_mock,
        "policy_name": (policy or _DEFAULT_POLICY).name,
    }


def batch_assess_freshness(
    items: list[dict[str, Any]],
    *,
    item_type: str = "source",
    policy: FreshnessPolicy | None = None,
) -> list[dict[str, Any]]:
    """Assess freshness of a list of items."""
    if item_type == "adapter":
        return [assess_adapter_result_freshness(i, policy) for i in items]
    return [assess_source_freshness(i, policy) for i in items]
