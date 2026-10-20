"""Tests for the batch-first invariant gate.

The gate is the only safety rail protecting batch-wide construction from
accidental article-by-article drift. It must:
* Refuse individual-send requests for 10+ routes without author rework.
* Refuse article-by-article rewrite requests for 10+ routes without
  author rework.
* Allow author_rework-enabled batches even with many routes.
* Allow any operation when the route count is below the threshold.
* Carry machine-readable reason codes that callers can branch on.
"""

from __future__ import annotations

import pytest

from kairoskopion.kairon_provider import (
    BATCH_FIRST_THRESHOLD,
    BatchFirstDecision,
    BatchFirstDecisionKind,
    REFUSAL_ARTICLE_REWRITE_FORBIDDEN,
    REFUSAL_INDIVIDUAL_SEND,
    enforce_batch_first,
)


def test_large_batch_individual_send_refused_without_author_rework():
    decision = enforce_batch_first(
        route_count=10,
        author_rework_enabled=False,
        individual_send_requested=True,
    )
    assert decision.kind == BatchFirstDecisionKind.REFUSE_BATCH_FIRST.value
    assert decision.reason_code == REFUSAL_INDIVIDUAL_SEND
    assert decision.route_count == 10
    assert decision.individual_send_requested is True


def test_large_batch_article_rewrite_refused_without_author_rework():
    decision = enforce_batch_first(
        route_count=15,
        author_rework_enabled=False,
        article_rewrite_requested=True,
    )
    assert decision.kind == BatchFirstDecisionKind.REFUSE_BATCH_FIRST.value
    assert decision.reason_code == REFUSAL_ARTICLE_REWRITE_FORBIDDEN


def test_large_batch_with_author_rework_proceeds():
    decision = enforce_batch_first(
        route_count=25,
        author_rework_enabled=True,
        individual_send_requested=True,
    )
    assert decision.kind == BatchFirstDecisionKind.PROCEED_BATCH.value
    assert decision.reason_code is None


def test_small_batch_individual_send_proceeds():
    decision = enforce_batch_first(
        route_count=5,
        author_rework_enabled=False,
        individual_send_requested=True,
    )
    assert decision.kind == BatchFirstDecisionKind.PROCEED_BATCH.value


def test_large_batch_without_rework_proceeds_in_batch_first_mode():
    decision = enforce_batch_first(
        route_count=12,
        author_rework_enabled=False,
        individual_send_requested=False,
        article_rewrite_requested=False,
    )
    assert decision.kind == BatchFirstDecisionKind.PROCEED_BATCH.value
    assert decision.notes and "batch-first" in decision.notes[0].lower()


def test_threshold_default_is_10():
    assert BATCH_FIRST_THRESHOLD == 10


def test_decision_to_dict_is_json_safe():
    decision = enforce_batch_first(
        route_count=11,
        author_rework_enabled=False,
        individual_send_requested=True,
    )
    blob = decision.to_dict()
    assert blob["kind"] == BatchFirstDecisionKind.REFUSE_BATCH_FIRST.value
    assert blob["reason_code"] == REFUSAL_INDIVIDUAL_SEND
    assert blob["route_count"] == 11


def test_negative_route_count_rejected():
    with pytest.raises(ValueError, match="route_count"):
        enforce_batch_first(route_count=-1)


def test_threshold_must_be_positive():
    with pytest.raises(ValueError, match="threshold"):
        enforce_batch_first(route_count=10, threshold=0)


def test_custom_threshold_refuses_below_default_count():
    decision = enforce_batch_first(
        route_count=8,
        author_rework_enabled=False,
        individual_send_requested=True,
        threshold=5,
    )
    assert decision.kind == BatchFirstDecisionKind.REFUSE_BATCH_FIRST.value


def test_reason_text_contains_route_count_and_threshold():
    decision = enforce_batch_first(
        route_count=14,
        author_rework_enabled=False,
        individual_send_requested=True,
    )
    assert "14" in decision.reason_text
    assert "10" in decision.reason_text
    assert "author_rework" in decision.reason_text


def test_proceed_decision_carries_input_flags():
    decision = enforce_batch_first(
        route_count=3,
        author_rework_enabled=False,
        individual_send_requested=False,
        article_rewrite_requested=True,
    )
    assert decision.kind == BatchFirstDecisionKind.PROCEED_BATCH.value
    assert decision.article_rewrite_requested is True


def test_large_batch_rework_enabled_proceeds_with_notes():
    decision = enforce_batch_first(
        route_count=50,
        author_rework_enabled=True,
        individual_send_requested=False,
        article_rewrite_requested=False,
    )
    assert decision.kind == BatchFirstDecisionKind.PROCEED_BATCH.value
    assert decision.author_rework_enabled is True
    assert any("author_rework" in note for note in decision.notes)


def test_refusal_does_not_block_proceeding_with_other_route_counts():
    refused = enforce_batch_first(
        route_count=20,
        author_rework_enabled=False,
        individual_send_requested=True,
    )
    assert refused.kind == BatchFirstDecisionKind.REFUSE_BATCH_FIRST.value
    next_call = enforce_batch_first(
        route_count=20,
        author_rework_enabled=True,
        individual_send_requested=True,
    )
    assert next_call.kind == BatchFirstDecisionKind.PROCEED_BATCH.value


def test_decision_dataclass_supports_equality():
    a = enforce_batch_first(route_count=4)
    b = enforce_batch_first(route_count=4)
    assert a.kind == b.kind
    assert a.threshold == b.threshold