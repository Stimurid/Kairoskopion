"""User decision tracking (spec Wave 3 §20)."""

from __future__ import annotations

import dataclasses as dc
from typing import Any

from .enums import DecisionStatus
from .ids import decision_id
from .schema import _DictMixin, _field, _now


@dc.dataclass
class UserDecision(_DictMixin):
    decision_id: str = dc.field(default_factory=decision_id)
    related_entity_id: str | None = _field()
    decision_type: str = ""
    status: str = DecisionStatus.PENDING.value
    user_note: str | None = _field()
    timestamp: str = dc.field(default_factory=_now)
    effect: str | None = _field()


def record_decision(
    *,
    entity_id: str,
    decision_type: str,
    status: DecisionStatus = DecisionStatus.PENDING,
    note: str | None = None,
    effect: str | None = None,
) -> UserDecision:
    return UserDecision(
        related_entity_id=entity_id,
        decision_type=decision_type,
        status=status.value,
        user_note=note,
        effect=effect,
    )
