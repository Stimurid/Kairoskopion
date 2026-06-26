"""Downstream usage status for registry records (P6).

Answers the question: can a downstream consumer treat this record
as canonical, or must it flag a warning / refuse?
"""

from __future__ import annotations

from typing import Any


def record_usage_status(record: Any) -> str:
    """Return one of: canonical, provisional_with_warning, rejected_unusable, unknown.

    Rules:
    - accepted + curator_confirmed → canonical
    - provisional + any review → provisional_with_warning
    - rejected (either field) → rejected_unusable
    - everything else → unknown
    """
    source = getattr(record, "source_status", "unknown")
    review = getattr(record, "review_status", "pending")

    if source == "rejected" or review == "rejected":
        return "rejected_unusable"
    if source == "accepted" and review == "curator_confirmed":
        return "canonical"
    if source == "provisional":
        return "provisional_with_warning"
    return "unknown"
