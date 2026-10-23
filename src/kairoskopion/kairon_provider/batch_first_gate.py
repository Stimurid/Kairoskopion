"""Batch-first invariant gate for the MAI-batch pre-author gate.

This module enforces a single invariant: if the user asks for 10+ routes and
author-rework is not activated, then no article-by-article rewrite or
individual send can preempt batch-wide construction. The gate returns a
machine-readable decision so callers, CI, and CLI users see an explicit
reason code, not a silent fallback.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


BATCH_FIRST_THRESHOLD = 10


class BatchFirstDecisionKind(str, Enum):
    PROCEED_BATCH = "PROCEED_BATCH"
    REFUSE_BATCH_FIRST = "REFUSE_BATCH_FIRST"


REFUSAL_INDIVIDUAL_SEND = "BATCH_FIRST_INDIVIDUAL_SEND_FORBIDDEN"
REFUSAL_AUTHOR_REWORK_MISSING = "BATCH_FIRST_AUTHOR_REWORK_REQUIRED"
REFUSAL_ARTICLE_REWRITE_FORBIDDEN = "BATCH_FIRST_ARTICLE_REWRITE_FORBIDDEN"


@dataclass
class BatchFirstDecision:
    kind: str
    route_count: int
    author_rework_enabled: bool
    individual_send_requested: bool
    article_rewrite_requested: bool
    threshold: int = BATCH_FIRST_THRESHOLD
    reason_code: str | None = None
    reason_text: str | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _proceed(
    route_count: int,
    *,
    author_rework_enabled: bool,
    individual_send_requested: bool,
    article_rewrite_requested: bool,
    notes: list[str] | None = None,
) -> BatchFirstDecision:
    return BatchFirstDecision(
        kind=BatchFirstDecisionKind.PROCEED_BATCH.value,
        route_count=route_count,
        author_rework_enabled=author_rework_enabled,
        individual_send_requested=individual_send_requested,
        article_rewrite_requested=article_rewrite_requested,
        reason_code=None,
        reason_text=None,
        notes=list(notes or []),
    )


def _refuse(
    route_count: int,
    *,
    author_rework_enabled: bool,
    individual_send_requested: bool,
    article_rewrite_requested: bool,
    reason_code: str,
    reason_text: str,
) -> BatchFirstDecision:
    return BatchFirstDecision(
        kind=BatchFirstDecisionKind.REFUSE_BATCH_FIRST.value,
        route_count=route_count,
        author_rework_enabled=author_rework_enabled,
        individual_send_requested=individual_send_requested,
        article_rewrite_requested=article_rewrite_requested,
        reason_code=reason_code,
        reason_text=reason_text,
    )


def enforce_batch_first(
    route_count: int,
    *,
    author_rework_enabled: bool = False,
    individual_send_requested: bool = False,
    article_rewrite_requested: bool = False,
    threshold: int = BATCH_FIRST_THRESHOLD,
) -> BatchFirstDecision:
    """Return a machine-readable decision enforcing the batch-first invariant.

    Refusal reasons are explicit so callers can branch on them without
    parsing free-form strings.
    """

    if route_count < 0:
        raise ValueError("route_count must be >= 0")
    if threshold < 1:
        raise ValueError("threshold must be >= 1")

    large_batch = route_count >= threshold

    if individual_send_requested and large_batch and not author_rework_enabled:
        return _refuse(
            route_count,
            author_rework_enabled=author_rework_enabled,
            individual_send_requested=individual_send_requested,
            article_rewrite_requested=article_rewrite_requested,
            reason_code=REFUSAL_INDIVIDUAL_SEND,
            reason_text=(
                f"individual_send requested for batch of {route_count} routes "
                f"(>= {threshold}) without author_rework activation; "
                "batch-wide construction must complete first"
            ),
        )
    if article_rewrite_requested and large_batch and not author_rework_enabled:
        return _refuse(
            route_count,
            author_rework_enabled=author_rework_enabled,
            individual_send_requested=individual_send_requested,
            article_rewrite_requested=article_rewrite_requested,
            reason_code=REFUSAL_ARTICLE_REWRITE_FORBIDDEN,
            reason_text=(
                f"article-by-article rewrite requested for batch of "
                f"{route_count} routes (>= {threshold}) without "
                "author_rework activation; pre-author batch gate must complete first"
            ),
        )

    if large_batch and not author_rework_enabled:
        return _proceed(
            route_count,
            author_rework_enabled=author_rework_enabled,
            individual_send_requested=individual_send_requested,
            article_rewrite_requested=article_rewrite_requested,
            notes=[
                "large batch proceeds in batch-first mode; author_rework is "
                "explicitly off"
            ],
        )

    if author_rework_enabled:
        return _proceed(
            route_count,
            author_rework_enabled=author_rework_enabled,
            individual_send_requested=individual_send_requested,
            article_rewrite_requested=article_rewrite_requested,
            notes=[
                "author_rework is enabled; batch-first gate allows "
                "individual handling once pre-author gate signals READY"
            ],
        )

    return _proceed(
        route_count,
        author_rework_enabled=author_rework_enabled,
        individual_send_requested=individual_send_requested,
        article_rewrite_requested=article_rewrite_requested,
    )