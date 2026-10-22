"""R2-R6 citation repair on a fictional synthetic Markdown manuscript.

SYNTHETIC TEST ONLY. Every source text, author, work, edition, witness and
decision receipt in this module is invented for testing. There is no real
publication, no real author manuscript and no real approval. The synthetic
author decision is marked SYNTHETIC_TEST and is accepted only because these
tests explicitly open the sandbox with ``allow_synthetic_test=True``.
"""
import hashlib
import json
from pathlib import Path

import pytest

from kairoskopion import cli
from kairoskopion.cli import main as cli_main
from kairoskopion.services.citation_intake_z0 import persist_audit
from kairoskopion.services import citation_repair_r2_r6 as repair

MANUSCRIPT = """# Synthetic Fictional Study

A student reproduces a published result and is scored by rubric (Ferrow 2014).
The rubric should be replaced by requiring the student to reconstruct, test and
transfer the practice that produced the result.

## References

Ferrow, N. (2014). A fictional assessment instrument. Fictional Press.
"""

CITATION_LINE = ("A student reproduces a published result and is scored by "
                 "rubric (Ferrow 2014).")
FRAGMENT = "(Ferrow 2014)"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _draft(tmp_path, text: str = MANUSCRIPT):
    path = tmp_path / "synthetic_manuscript.md"
    # Explicit bytes: Path.write_text would translate \n to \r\n on Windows and
    # make the expected SHAs platform-dependent.
    path.write_bytes(text.encode("utf-8"))
    return path


def _z0(tmp_path, draft):
    _, receipt = persist_audit(draft, tmp_path / "z0")
    queue = receipt.with_name("citation_work_orders.jsonl")
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    orders = [json.loads(line)
              for line in queue.read_text(encoding="utf-8").splitlines()]
    by_id = {i["intake_id"]: i for i in payload["intakes"]}
    case = next(c for c in payload["repair_cases"]
                if by_id[c["intake_id"]]["kind"] == "AUTHOR_YEAR")
    return receipt, queue, orders, case


def _z0_source_sha(tmp_path):
    audit = next((tmp_path / "z0").rglob("citation_intake.json"))
    return json.loads(audit.read_text(encoding="utf-8"))["source"]["sha256"]


def _prior_state(tmp_path, case, outcome="BLOCKED", read_depth="NONE",
                 negatives=("AUTHORIZED_SOURCE_READER_NOT_EXPOSED",)):
    state = {
        "schema": "trm-cite-r1-case-state-v1",
        "case_id": case["case_id"],
        "work_order_ids": [],
        "source_sha256": _z0_source_sha(tmp_path),
        "outcome": outcome,
        "verification": {f"V{i}": "NOT_CHECKED" for i in range(1, 6)},
        "source_identity": {"read_depth": read_depth},
        "negative_evidence": list(negatives),
        "citation_gate": "NOT_PUBLICATION_READY",
        "author_gate": "PENDING",
    }
    path = tmp_path / f"{case['case_id']}.state.json"
    path.write_text(json.dumps(state), encoding="utf-8")
    return state


def _consulted_negative_state(tmp_path, case):
    """Fictional witness was actually read and explicitly assessed as unrelated."""
    state = _prior_state(
        tmp_path, case, outcome="NEGATIVE", read_depth="SECTION_TEXT",
        negatives=("FICTIONAL_WITNESS_READ_CLAIM_NOT_SUPPORTED",))
    state["source_identity"].update({
        "witness_id": "SYNTHETIC_TEST_WITNESS_FERROW",
        "edition_id": "FICTIONAL_PRESS_2014",
    })
    state["source_to_claim_relation"] = "DOES_NOT_SUPPORT_CLAIM"
    state["source_excerpt_note"] = "Imaginary source excerpt actually read."
    (tmp_path / f"{case['case_id']}.state.json").write_text(
        json.dumps(state), encoding="utf-8")
    return state


def _candidate_text(tmp_path, entries):
    path = tmp_path / "candidate_text.json"
    path.write_text(json.dumps({
        "schema": repair.CANDIDATE_TEXT_SCHEMA,
        "candidates": entries,
    }), encoding="utf-8")
    return path


def _norm(value):
    """Normalize dataclass tuples to the JSON list form actually persisted."""
    return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True))


def _proposal(bundle, kind):
    return next(p for p in bundle["r5_proposals"] if
                next(c for c in bundle["r4_candidates"]
                     if c["candidate_id"] == p["candidate_id"])["kind"] == kind)


def _candidate(bundle, kind):
    return next(c for c in bundle["r4_candidates"] if c["kind"] == kind)


def _synthetic_receipt(proposal, decision="APPROVE",
                       user_input="Approve this synthetic repair for testing.",
                       issued_by="AUTHOR", issuer_role="TEST_AUTHOR",
                       synthetic=True):
    """Build a SYNTHETIC_TEST author receipt. Tests only; never in src/."""
    receipt = {
        "schema": repair.RECEIPT_SCHEMA,
        "issued_by": issued_by,
        "issuer_role": issuer_role,
        "witness_class": "SYNTHETIC_TEST" if synthetic
                         else "HUMAN_AUTHOR_DECISION",
        "synthetic": synthetic,
        "decision": decision,
        "user_input": user_input,
        "original_manuscript_sha256": proposal["target_manuscript_sha256"],
        "claim_id": proposal["case_id"],
        "candidate_id": proposal["candidate_id"],
        "diff_sha256": proposal["diff_sha256"],
        "original_text_sha256": proposal["original_text_sha256"],
        "new_text_sha256": proposal["new_text_sha256"],
        "issued_at": "2026-10-21T00:00:00+00:00",
    }
    receipt["receipt_id"] = repair.receipt_identity(receipt)
    return receipt


# ---------------------------------------------------------------------------
# (1)(2) R2 intent and R4 repair repertoire
# ---------------------------------------------------------------------------

def test_r2_detects_weak_citation_and_reconstructs_need_provisionally(tmp_path):
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    _prior_state(tmp_path, case)
    states = repair.load_prior_states([tmp_path])
    bundle = repair.plan_repair(audit, tmp_path / "out", case["case_id"], draft,
                               prior_states=states, queue_orders=orders)
    intent = bundle["r2_intent"]
    assert intent["schema"] == repair.INTENT_SCHEMA
    assert intent["citation_kind"] == "AUTHOR_YEAR"
    # The reconstruction is scoped to the cited line, not the whole document.
    assert intent["existing_claim"].startswith("A student reproduces")
    assert FRAGMENT in intent["existing_claim"]
    assert FRAGMENT in intent["claim_context"]
    assert intent["desired_support"].endswith("PASSAGE_THAT_ENTAILS_THE_CLAIM")
    assert intent["verbatim_source_refs"] == ("Ferrow 2014",)
    assert intent["author_confirmed"] is False
    assert intent["citation_certified"] is False
    assert intent["reconstruction_mode"] == "PROVISIONAL_FROM_Z0_EVIDENCE_ONLY"
    assert "AUTHOR_INTENT_NOT_CONFIRMED_WITH_THE_AUTHOR" in intent["uncertainties"]
    assert "NEGATIVE_EVIDENCE_REQUIRES_NEW_SOURCE_SEARCH" in intent["uncertainties"]


def test_r4_offers_distinct_repairs_with_differing_intellectual_cost(tmp_path):
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    _prior_state(tmp_path, case)
    bundle = repair.plan_repair(
        audit, tmp_path / "out", case["case_id"], draft,
        prior_states=repair.load_prior_states([tmp_path]), queue_orders=orders)
    kinds = [c["kind"] for c in bundle["r4_candidates"]]
    assert set(kinds) == set(repair.REPAIR_REPERTOIRE)
    assert len(kinds) >= 3
    assert len({c["intellectual_cost"] for c in bundle["r4_candidates"]}) >= 3
    for candidate in bundle["r4_candidates"]:
        assert candidate["author_gate"] == "PENDING"
        assert candidate["auto_approved"] is False
        assert candidate["verification_certified"] is False
        assert candidate["scientific_debt"]
        assert candidate["source_explanation"]
        assert candidate["debt_explanation"]
        assert candidate["source_to_claim_relation"]
    normative = _candidate(bundle, "PRESENT_NORMATIVE_AUTHOR_CONCLUSION_EXPLICITLY")
    assert normative["source_to_claim_relation"] == (
        "SOURCE_DECOUPLED_CLAIM_ATTRIBUTED_TO_THE_AUTHOR_NOT_TO_THE_SOURCE")
    assert "MACHINE_CANNOT_ESTABLISH_THAT_THE_SOURCE_ENTAILS_THE_CLAIM" in \
        normative["scientific_debt"]
    # With only BLOCKED evidence there is no observed identity to correct.
    bibliography = _candidate(bundle, "BIBLIOGRAPHY_DETAIL_REPAIR")
    assert bibliography["applicable"] is False
    assert "NO_OBSERVED_SOURCE_IDENTITY_TO_CORRECT" in bibliography["refusal_codes"]


def test_r3_reentry_is_bounded_preserves_negative_evidence_and_provenance(tmp_path):
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    _prior_state(tmp_path, case, negatives=("SOURCE_1_NOT_FOUND", "PAYWALLED"))
    bundle = repair.plan_repair(
        audit, tmp_path / "out", case["case_id"], draft,
        prior_states=repair.load_prior_states([tmp_path]), queue_orders=orders)
    reentry = bundle["r3_reentry"]
    assert reentry["schema"] == repair.REENTRY_SCHEMA
    assert reentry["execution_status"] == "QUEUED_NOT_EXECUTED"
    assert reentry["acquisition_authorized_by_this_object"] is False
    assert reentry["supersedes_prior_requests"] is False
    assert list(reentry["carries_negative_evidence"]) == [
        "PAYWALLED", "SOURCE_1_NOT_FOUND"]
    assert reentry["indago_hunt"] == "INDAGO_BOUNDED_HUNT_REQUIRED"
    assert any("PRESERVES_2_PRIOR_NEGATIVE_FINDINGS" in p
               for p in reentry["indago_provenance"])
    assert any("REUSES_EXISTING_SOURCE_STORE_NO_DUPLICATE_STORE" in p
               for p in reentry["indago_provenance"])


def test_r3_is_not_reissued_when_an_anchored_passage_is_on_record(tmp_path):
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    _prior_state(tmp_path, case, outcome="OBSERVED", read_depth="ANCHORED_PASSAGE",
                 negatives=())
    bundle = repair.plan_repair(
        audit, tmp_path / "out", case["case_id"], draft,
        prior_states=repair.load_prior_states([tmp_path]), queue_orders=orders)
    assert bundle["r3_reentry"] is None
    assert _candidate(bundle, "BIBLIOGRAPHY_DETAIL_REPAIR")["applicable"] is True


# ---------------------------------------------------------------------------
# (3) R5 reversible patch, no write to the original
# ---------------------------------------------------------------------------

def test_plan_produces_reversible_patch_and_never_touches_the_original(tmp_path):
    draft = _draft(tmp_path)
    before = draft.read_bytes()
    audit, queue, orders, case = _z0(tmp_path, draft)
    _consulted_negative_state(tmp_path, case)
    bundle = repair.plan_repair(
        audit, tmp_path / "out", case["case_id"], draft,
        prior_states=repair.load_prior_states([tmp_path]), queue_orders=orders)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    assert proposal["applicability"] == "READY_FOR_AUTHOR_REVIEW"
    assert proposal["author_gate"] == "PENDING"
    assert proposal["manuscript_mutated"] is False
    assert proposal["applied"] is False
    assert proposal["target_manuscript_sha256"] == _sha(before)
    assert proposal["original_fragment"] == FRAGMENT
    assert proposal["original_text_sha256"] == _sha(FRAGMENT.encode())
    assert proposal["suggested_new_text"] == ""
    assert FRAGMENT not in proposal["suggested_new_text"]
    assert proposal["diff"].startswith("--- a/synthetic_manuscript.md")
    assert "+A student reproduces" in proposal["diff"]
    assert proposal["inverse_diff_sha256"] != proposal["diff_sha256"]
    assert draft.read_bytes() == before
    assert not list((tmp_path / "out").rglob("*.md"))


def test_author_wording_is_required_for_prose_bearing_repairs(tmp_path):
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    _prior_state(tmp_path, case)
    bundle = repair.plan_repair(
        audit, tmp_path / "out", case["case_id"], draft,
        prior_states=repair.load_prior_states([tmp_path]), queue_orders=orders)
    for kind in ("CHANGE_SOURCE", "WEAKEN_OR_SPLIT_THESIS",
                 "PRESENT_NORMATIVE_AUTHOR_CONCLUSION_EXPLICITLY"):
        proposal = _proposal(bundle, kind)
        assert proposal["applicability"] == "BLOCKED_NO_SUGGESTED_TEXT"
        assert proposal["suggested_new_text"] == ""
        assert "SUGGESTED_TEXT_MUST_COME_FROM_THE_AUTHOR_OR_ANALYST" in \
            proposal["debts"]
    abstain = _proposal(bundle, "ABSTAIN_NO_CHANGE")
    assert abstain["applicability"] == "NO_CHANGE_PROPOSED"


def test_operator_supplied_wording_renders_a_ready_proposal(tmp_path):
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    _prior_state(tmp_path, case)
    wording = _candidate_text(tmp_path, [{
        "kind": "PRESENT_NORMATIVE_AUTHOR_CONCLUSION_EXPLICITLY",
        "old_text": "is scored by rubric (Ferrow 2014).",
        "suggested_new_text":
            "is scored by rubric (Ferrow 2014); as this article argues, the "
            "practice should be transferred rather than scored.",
    }])
    bundle = repair.plan_repair(
        audit, tmp_path / "out", case["case_id"], draft,
        prior_states=repair.load_prior_states([tmp_path]), queue_orders=orders,
        candidate_text_path=wording)
    proposal = _proposal(bundle, "PRESENT_NORMATIVE_AUTHOR_CONCLUSION_EXPLICITLY")
    assert proposal["applicability"] == "READY_FOR_AUTHOR_REVIEW"
    assert proposal["old_text"] == "is scored by rubric (Ferrow 2014)."
    assert proposal["text_source"] == "AUTHOR_OR_ANALYST_WORDING_REQUIRED"
    # The author's wording, not the machine's, decides the new sentence.
    assert proposal["suggested_new_text"].startswith("is scored by rubric")
    assert "transferred rather than scored" in proposal["suggested_new_text"]


# ---------------------------------------------------------------------------
# (4) the gate
# ---------------------------------------------------------------------------

def test_pending_gate_refuses_apply_without_a_bound_author_receipt(tmp_path):
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    _consulted_negative_state(tmp_path, case)
    bundle = repair.plan_repair(
        audit, tmp_path / "out", case["case_id"], draft,
        prior_states=repair.load_prior_states([tmp_path]), queue_orders=orders)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    copy = tmp_path / "copy.md"

    with pytest.raises(ValueError, match="Unknown decision receipt schema"):
        repair.apply_patch(draft, proposal, {}, copy)

    with pytest.raises(ValueError, match="human AUTHOR"):
        receipt = _synthetic_receipt(proposal, issued_by="ASSISTANT")
        repair.apply_patch(draft, proposal, receipt, copy,
                           allow_synthetic_test=True)

    with pytest.raises(ValueError, match="Non-human issuer role"):
        receipt = _synthetic_receipt(proposal, issuer_role="MODEL")
        repair.apply_patch(draft, proposal, receipt, copy,
                           allow_synthetic_test=True)

    assert not copy.exists()
    assert draft.read_bytes() == MANUSCRIPT.encode("utf-8")


def test_reject_and_revision_decisions_never_apply(tmp_path):
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    _consulted_negative_state(tmp_path, case)
    bundle = repair.plan_repair(
        audit, tmp_path / "out", case["case_id"], draft,
        prior_states=repair.load_prior_states([tmp_path]), queue_orders=orders)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    for decision in ("REJECT", "REQUEST_REVISION"):
        copy = tmp_path / f"copy_{decision}.md"
        receipt = _synthetic_receipt(proposal, decision=decision)
        with pytest.raises(ValueError, match="Decision is not APPROVE"):
            repair.apply_patch(draft, proposal, receipt, copy,
                               allow_synthetic_test=True)
        assert not copy.exists()


def test_receipt_must_be_bound_to_this_exact_patch(tmp_path):
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    _consulted_negative_state(tmp_path, case)
    bundle = repair.plan_repair(
        audit, tmp_path / "out", case["case_id"], draft,
        prior_states=repair.load_prior_states([tmp_path]), queue_orders=orders)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    copy = tmp_path / "copy.md"
    for field, value in (
        ("original_manuscript_sha256", "0" * 64),
        ("claim_id", "cr_deadbeefdeadbeefdead"),
        ("candidate_id", "r4_deadbeefdeadbeefdead"),
        ("diff_sha256", "1" * 64),
        ("original_text_sha256", "2" * 64),
    ):
        receipt = _synthetic_receipt(proposal)
        receipt[field] = value
        receipt["receipt_id"] = repair.receipt_identity(receipt)
        with pytest.raises(ValueError,
                           match="not bound to this patch: " + field):
            repair.apply_patch(draft, proposal, receipt, copy,
                               allow_synthetic_test=True)
    assert not copy.exists()


def test_tampered_or_unidentified_decision_id_is_refused(tmp_path):
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    _consulted_negative_state(tmp_path, case)
    bundle = repair.plan_repair(
        audit, tmp_path / "out", case["case_id"], draft,
        prior_states=repair.load_prior_states([tmp_path]), queue_orders=orders)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    copy = tmp_path / "copy.md"

    receipt = _synthetic_receipt(proposal)
    receipt["receipt_id"] = "dr_forged"
    with pytest.raises(ValueError, match="does not match its own content"):
        repair.apply_patch(draft, proposal, receipt, copy,
                           allow_synthetic_test=True)

    receipt = _synthetic_receipt(proposal)
    receipt["user_input"] = "Approve this."  # id no longer covers the content
    with pytest.raises(ValueError, match="does not match its own content"):
        repair.apply_patch(draft, proposal, receipt, copy,
                           allow_synthetic_test=True)

    receipt = _synthetic_receipt(proposal, user_input="   ")
    receipt["receipt_id"] = repair.receipt_identity(receipt)
    with pytest.raises(ValueError, match="no verbatim user input"):
        repair.apply_patch(draft, proposal, receipt, copy,
                           allow_synthetic_test=True)
    assert not copy.exists()


def test_synthetic_receipt_cannot_authorize_a_real_apply(tmp_path):
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    _consulted_negative_state(tmp_path, case)
    bundle = repair.plan_repair(
        audit, tmp_path / "out", case["case_id"], draft,
        prior_states=repair.load_prior_states([tmp_path]), queue_orders=orders)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    copy = tmp_path / "copy.md"
    receipt = _synthetic_receipt(proposal)
    with pytest.raises(ValueError, match="Synthetic test receipt"):
        repair.apply_patch(draft, proposal, receipt, copy)
    assert not copy.exists()


# ---------------------------------------------------------------------------
# (5) sandboxed approval applies to a copy, atomically, with an inverse patch
# ---------------------------------------------------------------------------

def test_sandboxed_approval_applies_to_copy_and_emits_inverse_patch(tmp_path):
    draft = _draft(tmp_path)
    original = draft.read_bytes()
    audit, queue, orders, case = _z0(tmp_path, draft)
    _consulted_negative_state(tmp_path, case)
    bundle = repair.plan_repair(
        audit, tmp_path / "out", case["case_id"], draft,
        prior_states=repair.load_prior_states([tmp_path]), queue_orders=orders)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    copy = tmp_path / "applied_copy.md"
    receipt = _synthetic_receipt(proposal)

    applied = repair.apply_patch(draft, proposal, receipt, copy,
                                 allow_synthetic_test=True)
    assert applied["schema"] == repair.APPLY_SCHEMA
    assert applied["original_manuscript_mutated"] is False
    assert applied["synthetic_test_receipt"] is True
    assert applied["original_manuscript_sha256"] == _sha(original)
    assert draft.read_bytes() == original
    assert copy.read_bytes() != original
    assert _sha(copy.read_bytes()) == applied["applied_copy_sha256"]
    assert _sha(copy.read_bytes()) == proposal["patched_manuscript_sha256"]
    assert FRAGMENT not in copy.read_text(encoding="utf-8").split("## References")[0]
    assert applied["inverse_diff_sha256"] == proposal["inverse_diff_sha256"]
    assert applied["verification"] == {f"V{i}": "NOT_CHECKED" for i in range(1, 6)}
    assert applied["citation_gate"] == "NOT_PUBLICATION_READY"

    # Atomic + fresh-path only.
    with pytest.raises(ValueError, match="overwrite an existing file"):
        repair.apply_patch(draft, proposal, receipt, copy,
                           allow_synthetic_test=True)
    with pytest.raises(ValueError, match="onto the original manuscript"):
        repair.apply_patch(draft, proposal, receipt, draft,
                           allow_synthetic_test=True)


def test_apply_refuses_to_overwrite_the_original_and_sibling_copies(tmp_path):
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    _consulted_negative_state(tmp_path, case)
    bundle = repair.plan_repair(
        audit, tmp_path / "out", case["case_id"], draft,
        prior_states=repair.load_prior_states([tmp_path]), queue_orders=orders)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    receipt = _synthetic_receipt(proposal)
    with pytest.raises(ValueError, match="onto the original manuscript"):
        repair.apply_patch(draft, proposal, receipt, draft,
                           allow_synthetic_test=True)
    assert draft.read_bytes() == MANUSCRIPT.encode("utf-8")


# ---------------------------------------------------------------------------
# (6) R6 readback keeps the debt
# ---------------------------------------------------------------------------

def test_r6_rereads_copy_and_reports_debt_not_fabricated_success(tmp_path):
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    _consulted_negative_state(tmp_path, case)
    bundle = repair.plan_repair(
        audit, tmp_path / "out", case["case_id"], draft,
        prior_states=repair.load_prior_states([tmp_path]), queue_orders=orders)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    copy = tmp_path / "applied_copy.md"
    applied = repair.apply_patch(draft, proposal,
                                 _synthetic_receipt(proposal), copy,
                                 allow_synthetic_test=True)

    check = repair.post_patch_check(copy, proposal, applied)
    assert check["schema"] == repair.CHECK_SCHEMA
    assert check["reread_status"] == "REREAD_VIA_Z0"
    assert check["z0_reread_schema_version"] == "trm-cite-z0-v03"
    assert check["applied_copy_sha256"] == _sha(copy.read_bytes())
    assert check["original_manuscript_sha256"] == _sha(MANUSCRIPT.encode("utf-8"))
    # The citation is genuinely gone from the patched line: a real readback,
    # not a restatement of the proposal.
    assert check["citation_present_after_patch"] is False
    assert check["reread_intake_id"] is None
    assert check["verification"] == {f"V{i}": "NOT_CHECKED" for i in range(1, 6)}
    assert check["any_verification_passed"] is False
    assert check["scientific_status"] == "DEBT_RETAINED_NO_PUBLICATION_PASS"
    assert check["citation_gate"] == "NOT_PUBLICATION_READY"
    assert check["journal_style"] == "NOT_CHECKED_NO_VENUE_PROFILE"
    assert "SOURCE_SUPPORT_NOT_INDEPENDENTLY_VERIFIED" in check["scientific_debts"]
    assert "VENUE_STYLE_PROFILE_NOT_SUPPLIED" in check["scientific_debts"]


def test_r6_refuses_without_a_real_apply_or_on_a_stale_copy(tmp_path):
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    _consulted_negative_state(tmp_path, case)
    bundle = repair.plan_repair(
        audit, tmp_path / "out", case["case_id"], draft,
        prior_states=repair.load_prior_states([tmp_path]), queue_orders=orders)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    copy = tmp_path / "applied_copy.md"
    applied = repair.apply_patch(draft, proposal,
                                 _synthetic_receipt(proposal), copy,
                                 allow_synthetic_test=True)

    with pytest.raises(ValueError, match="real apply receipt"):
        repair.post_patch_check(copy, proposal, {"schema": "nope"})

    copy.write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Applied copy SHA mismatch"):
        repair.post_patch_check(copy, proposal, applied)


def test_r6_refuses_when_nothing_was_applied(tmp_path):
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    _consulted_negative_state(tmp_path, case)
    bundle = repair.plan_repair(
        audit, tmp_path / "out", case["case_id"], draft,
        prior_states=repair.load_prior_states([tmp_path]), queue_orders=orders)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    copy = tmp_path / "unchanged_copy.md"
    copy.write_bytes(draft.read_bytes())
    applied = {
        "schema": repair.APPLY_SCHEMA,
        "patch_id": proposal["patch_id"],
        "original_manuscript_sha256": _sha(draft.read_bytes()),
        "applied_copy_sha256": _sha(copy.read_bytes()),
        "author_gate": "AUTHOR_APPROVED_THIS_PATCH_ONLY",
    }
    with pytest.raises(ValueError, match="nothing was applied"):
        repair.post_patch_check(copy, proposal, applied)


# ---------------------------------------------------------------------------
# (7) undo restores exact original bytes
# ---------------------------------------------------------------------------

def test_undo_restores_exact_original_source_bytes(tmp_path):
    draft = _draft(tmp_path)
    original = draft.read_bytes()
    audit, queue, orders, case = _z0(tmp_path, draft)
    _consulted_negative_state(tmp_path, case)
    bundle = repair.plan_repair(
        audit, tmp_path / "out", case["case_id"], draft,
        prior_states=repair.load_prior_states([tmp_path]), queue_orders=orders)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    copy = tmp_path / "applied_copy.md"
    applied = repair.apply_patch(draft, proposal,
                                 _synthetic_receipt(proposal), copy,
                                 allow_synthetic_test=True)
    snapshot = Path(json.loads(audit.read_text(encoding="utf-8"))
                    ["source"]["original_snapshot_path"])

    restored = tmp_path / "restored.md"
    undo = repair.undo_patch(copy, applied, snapshot, restored)
    assert undo["schema"] == repair.UNDO_SCHEMA
    assert undo["original_sha256_preserved"] is True
    assert undo["exact_source_bytes_restored"] is True
    assert restored.read_bytes() == original
    assert _sha(restored.read_bytes()) == applied["original_manuscript_sha256"]
    assert draft.read_bytes() == original


def test_undo_refuses_on_snapshot_or_copy_drift(tmp_path):
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    _consulted_negative_state(tmp_path, case)
    bundle = repair.plan_repair(
        audit, tmp_path / "out", case["case_id"], draft,
        prior_states=repair.load_prior_states([tmp_path]), queue_orders=orders)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    copy = tmp_path / "applied_copy.md"
    applied = repair.apply_patch(draft, proposal,
                                 _synthetic_receipt(proposal), copy,
                                 allow_synthetic_test=True)
    snapshot = Path(json.loads(audit.read_text(encoding="utf-8"))["source"]
                    ["original_snapshot_path"])
    bad_snapshot = tmp_path / "bad_snapshot.md"
    bad_snapshot.write_text("not the original\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Original snapshot SHA mismatch"):
        repair.undo_patch(copy, applied, bad_snapshot, tmp_path / "r1.md")
    copy.write_text("drifted\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Applied copy SHA mismatch"):
        repair.undo_patch(copy, applied, snapshot, tmp_path / "r2.md")





# ---------------------------------------------------------------------------
# (8) replay, drift and ambiguity
# ---------------------------------------------------------------------------

def test_replay_is_immutable_and_identical_after_reset(tmp_path):
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    _consulted_negative_state(tmp_path, case)
    states = repair.load_prior_states([tmp_path])
    first = repair.plan_repair(audit, tmp_path / "out", case["case_id"], draft,
                               prior_states=states, queue_orders=orders)
    second = repair.plan_repair(audit, tmp_path / "out", case["case_id"], draft,
                                prior_states=states, queue_orders=orders)
    assert first == second
    stored = next((tmp_path / "out").rglob("plan_*.json"))
    stored_bytes = stored.read_bytes()
    assert json.loads(stored.read_text(encoding="utf-8")) == _norm(first)

    proposal = _proposal(first, "REMOVE_UNSUPPORTED_CITATION")
    copy = tmp_path / "round1.md"
    applied = repair.apply_patch(draft, proposal,
                                 _synthetic_receipt(proposal), copy,
                                 allow_synthetic_test=True)
    snapshot = Path(json.loads(audit.read_text(encoding="utf-8"))["source"]
                    ["original_snapshot_path"])
    repair.undo_patch(copy, applied, snapshot, tmp_path / "restored1.md")

    # Reset and replay: same plan bytes, same proposal identity, same patch.
    third = repair.plan_repair(audit, tmp_path / "out", case["case_id"], draft,
                               prior_states=states, queue_orders=orders)
    assert third == first
    assert stored.read_bytes() == stored_bytes
    replay = _proposal(third, "REMOVE_UNSUPPORTED_CITATION")
    assert replay["patch_id"] == proposal["patch_id"]
    assert replay["diff_sha256"] == proposal["diff_sha256"]
    copy2 = tmp_path / "round2.md"
    applied2 = repair.apply_patch(draft, replay,
                                  _synthetic_receipt(replay), copy2,
                                  allow_synthetic_test=True)
    assert applied2["applied_copy_sha256"] == applied["applied_copy_sha256"]
    assert copy2.read_bytes() == copy.read_bytes()


def test_wrong_manifest_sha_fails_closed(tmp_path):
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    _prior_state(tmp_path, case)
    with pytest.raises(ValueError, match="SHA mismatch"):
        repair.plan_repair(audit, tmp_path / "out", case["case_id"], draft,
                           expected_sha="0" * 64)

    edited = draft.read_text(encoding="utf-8").replace("student", "pupil")
    draft.write_text(edited, encoding="utf-8")
    with pytest.raises(ValueError, match="not the audited original"):
        repair.plan_repair(audit, tmp_path / "out", case["case_id"], draft)
    # The audited original snapshot is untouched by the drift.
    assert _sha(draft.read_bytes()) != _sha(MANUSCRIPT.encode("utf-8"))


def test_edited_manuscript_makes_the_proposal_unreproducible_at_apply(tmp_path):
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    _consulted_negative_state(tmp_path, case)
    bundle = repair.plan_repair(
        audit, tmp_path / "out", case["case_id"], draft,
        prior_states=repair.load_prior_states([tmp_path]), queue_orders=orders)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    draft.write_text(draft.read_text(encoding="utf-8").replace("rubric ", ""),
                     encoding="utf-8")
    with pytest.raises(ValueError, match="Original manuscript SHA mismatch"):
        repair.apply_patch(draft, proposal, _synthetic_receipt(proposal),
                           tmp_path / "copy.md", allow_synthetic_test=True)


def test_colliding_anchor_text_fails_closed(tmp_path):
    text = MANUSCRIPT.replace(
        CITATION_LINE,
        "A student reproduces a published result (Ferrow 2014) and is scored "
        "by rubric (Ferrow 2014).")
    draft = _draft(tmp_path, text)
    audit, queue, orders, case = _z0(tmp_path, draft)
    _prior_state(tmp_path, case)
    wording = _candidate_text(tmp_path, [{
        "kind": "CHANGE_SOURCE",
        "old_text": "(Ferrow 2014)",
        "suggested_new_text": "(Ashby 2019)",
    }])
    bundle = repair.plan_repair(
        audit, tmp_path / "out", case["case_id"], draft,
        prior_states=repair.load_prior_states([tmp_path]), queue_orders=orders,
        candidate_text_path=wording)
    # The first AUTHOR_YEAR case sits on the ambiguous line.
    proposal = _proposal(bundle, "CHANGE_SOURCE")
    assert proposal["applicability"] == "BLOCKED_ANCHOR_TEXT_NOT_UNIQUE"
    assert proposal["suggested_new_text"] == ""
    assert "not unique" in proposal["debts"][0]


def test_missing_anchor_locator_fails_closed(tmp_path):
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    _consulted_negative_state(tmp_path, case)
    proposal = _proposal(
        repair.plan_repair(audit, tmp_path / "out", case["case_id"], draft,
                           prior_states=repair.load_prior_states([tmp_path]),
                           queue_orders=orders),
        "REMOVE_UNSUPPORTED_CITATION")
    broken = dict(proposal,
                  target_locator="line:9999",
                  anchor=dict(proposal["anchor"], locator="line:9999"))
    with pytest.raises(ValueError, match="anchor locator absent"):
        repair.apply_patch(draft, broken, _synthetic_receipt(broken),
                           tmp_path / "copy.md", allow_synthetic_test=True)


def test_unknown_case_and_unknown_schema_are_refused(tmp_path):
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    with pytest.raises(ValueError, match="not in the original audit"):
        repair.plan_repair(audit, tmp_path / "out", "cr_nope", draft)
    bad = tmp_path / "bad_audit.json"
    bad.write_text(json.dumps({"schema_version": "something-else"}),
                   encoding="utf-8")
    with pytest.raises(ValueError, match="Unknown Z0 audit schema"):
        repair.plan_repair(bad, tmp_path / "out", case["case_id"], draft)


def test_unlinked_prior_evidence_is_preserved_not_dropped(tmp_path):
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    _prior_state(tmp_path, case)
    orphan = tmp_path / "orphan.state.json"
    orphan.write_text(json.dumps({
        "schema": "trm-cite-r1-task-state-v1", "case_id": "R1-05",
        "work_order_ids": [], "outcome": "BLOCKED", "negative_evidence": ["X"],
    }), encoding="utf-8")
    bundle = repair.plan_repair(
        audit, tmp_path / "out", case["case_id"], draft,
        prior_states=repair.load_prior_states([tmp_path]), queue_orders=orders)
    assert bundle["prior_evidence"]["linked_state_count"] == 1
    assert len(bundle["prior_evidence"]["unlinked_states_preserved"]) == 1
    assert orphan.exists()
    assert not any("DELETE" in p
                   for p in bundle["r3_reentry"]["indago_provenance"])


# ---------------------------------------------------------------------------
# structural guards
# ---------------------------------------------------------------------------

def test_crlf_and_bom_manuscripts_round_trip_exactly(tmp_path):
    """Windows line endings and a UTF-8 BOM must not corrupt the patch."""
    for label, raw in (
        ("crlf", MANUSCRIPT.replace("\n", "\r\n").encode("utf-8")),
        ("bom", b"\xef\xbb\xbf" + MANUSCRIPT.encode("utf-8")),
        ("bom_crlf", b"\xef\xbb\xbf"
         + MANUSCRIPT.replace("\n", "\r\n").encode("utf-8")),
    ):
        case_dir = tmp_path / label
        case_dir.mkdir()
        draft = case_dir / "synthetic_manuscript.md"
        draft.write_bytes(raw)
        audit, _, _, case = _z0(case_dir, draft)
        _consulted_negative_state(case_dir, case)
        bundle = repair.plan_repair(
            audit, case_dir / "out", case["case_id"], draft,
            prior_states=repair.load_prior_states([case_dir]))
        proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
        assert proposal["applicability"] == "READY_FOR_AUTHOR_REVIEW", label
        copy = case_dir / "copy.md"
        applied = repair.apply_patch(draft, proposal,
                                     _synthetic_receipt(proposal), copy,
                                     allow_synthetic_test=True)
        out = copy.read_bytes()
        assert out == raw.replace(b"(Ferrow 2014)", b""), label
        assert raw.startswith(b"\xef\xbb\xbf") == out.startswith(b"\xef\xbb\xbf")
        assert draft.read_bytes() == raw
        snapshot = Path(json.loads(audit.read_text(encoding="utf-8"))["source"]
                        ["original_snapshot_path"])
        repair.undo_patch(copy, applied, snapshot, case_dir / "restored.md")
        assert (case_dir / "restored.md").read_bytes() == raw, label


def _ready_bundle(tmp_path, draft=None):
    draft = draft or _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    _consulted_negative_state(tmp_path, case)
    bundle = repair.plan_repair(
        audit, tmp_path / "out", case["case_id"], draft,
        prior_states=repair.load_prior_states([tmp_path]), queue_orders=orders)
    return draft, audit, bundle, case


def test_approval_cannot_be_replayed_against_different_text(tmp_path):
    """The signed diff must be exactly what the manuscript produces."""
    draft, _, bundle, _ = _ready_bundle(tmp_path)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    receipt = _synthetic_receipt(proposal)
    assert proposal["suggested_new_text"] == ""

    text, _ = repair._decode(draft.read_bytes())
    evil_text = "\nINJECTED PARAGRAPH never shown to the author."
    start, end = repair.resolve_patch_span(
        text, proposal["anchor"], proposal["old_text"],
        proposal["original_fragment"], True)
    patched = text[:start] + evil_text + text[end:]
    forged = dict(
        proposal,
        suggested_new_text=evil_text,
        new_text_sha256=repair._text_digest(evil_text),
        patched_manuscript_sha256=_sha(patched.encode("utf-8")))
    # Every field the author actually saw is still byte-identical.
    assert forged["diff_sha256"] == proposal["diff_sha256"]
    assert forged["old_text"] == proposal["old_text"]
    copy = tmp_path / "copy.md"

    # Layer 1: the receipt is bound to the new text as well as the diff.
    with pytest.raises(ValueError, match="not bound to this patch: new_text_sha256"):
        repair.apply_patch(draft, forged, receipt, copy,
                           allow_synthetic_test=True)

    # Layer 2: even re-binding the receipt to the forged text, the diff is
    # recomputed from the manuscript and must equal the signed diff.
    rebound = _synthetic_receipt(forged)
    with pytest.raises(ValueError, match="does not match the diff the author"):
        repair.apply_patch(draft, forged, rebound, copy,
                           allow_synthetic_test=True)
    assert not copy.exists()
    assert draft.read_bytes() == MANUSCRIPT.encode("utf-8")


def test_stripping_synthetic_markers_invalidates_the_receipt_id(tmp_path):
    """Laundering a test receipt cannot cross into a real apply.

    Editing the synthetic markers invalidates the receipt id. Re-issuing the id
    still cannot help without the author's keyed attestation, which is the only
    thing a peer process cannot forge.
    """
    draft, _, bundle, _ = _ready_bundle(tmp_path)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    synthetic = _synthetic_receipt(proposal)
    copy = tmp_path / "copy.md"
    laundered = dict(synthetic, synthetic=False,
                     witness_class="HUMAN_AUTHOR_DECISION")
    assert laundered["receipt_id"] == synthetic["receipt_id"]
    with pytest.raises(ValueError, match="does not match its own content"):
        repair.apply_patch(draft, proposal, laundered, copy)

    # Re-minting the id for the cleaned receipt still lacks the author's MAC.
    laundered["receipt_id"] = repair.receipt_identity(laundered)
    assert laundered["receipt_id"] != synthetic["receipt_id"]
    key = b"author-secret"
    with pytest.raises(ValueError, match="not keyed by the author's secret"):
        repair.apply_patch(draft, proposal, laundered, copy, author_key=key)
    assert not copy.exists()

    # With the author's own key it is legitimately accepted.
    laundered["receipt_mac"] = repair.receipt_mac(laundered, key)
    applied = repair.apply_patch(draft, proposal, laundered, copy,
                                 author_key=key)
    assert applied["synthetic_test_receipt"] is False


def test_unknown_witness_class_is_refused(tmp_path):
    draft, _, bundle, _ = _ready_bundle(tmp_path)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    receipt = _synthetic_receipt(proposal, synthetic=False)
    receipt["witness_class"] = "TOTALLY_MADE_UP"
    receipt["receipt_id"] = repair.receipt_identity(receipt)
    copy = tmp_path / "copy.md"
    with pytest.raises(ValueError, match="Unknown decision witness class"):
        repair.apply_patch(draft, proposal, receipt, copy,
                           allow_synthetic_test=True)
    assert not copy.exists()


def test_out_of_range_and_negative_anchor_offsets_are_refused(tmp_path):
    draft, _, bundle, _ = _ready_bundle(tmp_path)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    text, _ = repair._decode(draft.read_bytes())
    for anchor in (
        dict(proposal["anchor"], start_codepoint=-19, end_codepoint=26),
        dict(proposal["anchor"], start_codepoint=0, end_codepoint=10 ** 9),
        dict(proposal["anchor"], start_codepoint=9, end_codepoint=3),
    ):
        with pytest.raises(ValueError, match="out of range"):
            repair.resolve_patch_span(text, anchor, proposal["old_text"],
                                      proposal["original_fragment"], True)


def test_case_id_cannot_escape_the_output_directory(tmp_path):
    draft = _draft(tmp_path)
    audit, _, _, _ = _z0(tmp_path, draft)
    out = tmp_path / "out"
    with pytest.raises(ValueError, match="Unsafe identifier"):
        repair.plan_repair(audit, out, "../../../../pwned", draft)
    assert not (tmp_path.parent / "pwned.json").exists()


def test_proposal_id_must_match_its_own_intent_and_candidate(tmp_path):
    draft, _, bundle, _ = _ready_bundle(tmp_path)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    forged = dict(proposal, patch_id="r5_forged")
    copy = tmp_path / "copy.md"
    with pytest.raises(ValueError, match="does not match its own intent"):
        repair.apply_patch(draft, forged, _synthetic_receipt(forged), copy,
                           allow_synthetic_test=True)
    assert not copy.exists()


def test_tampered_diff_is_refused_before_the_original_is_touched(tmp_path):
    draft, _, bundle, _ = _ready_bundle(tmp_path)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    tampered = dict(proposal, inverse_diff="COMPLETELY BOGUS UNDO PATCH")
    receipt = _synthetic_receipt(tampered)
    receipt["receipt_id"] = repair.receipt_identity(receipt)
    copy = tmp_path / "copy.md"
    with pytest.raises(ValueError, match="inverse diff SHA"):
        repair.apply_patch(draft, tampered, receipt, copy,
                           allow_synthetic_test=True)
    assert not copy.exists()
    assert draft.read_bytes() == MANUSCRIPT.encode("utf-8")


def test_r6_refuses_when_the_original_manuscript_drifted_after_apply(tmp_path):
    draft, _, bundle, _ = _ready_bundle(tmp_path)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    copy = tmp_path / "copy.md"
    applied = repair.apply_patch(draft, proposal, _synthetic_receipt(proposal),
                                 copy, allow_synthetic_test=True)
    draft.write_bytes(b"TAMPERED ORIGINAL AFTER APPLY\n")
    with pytest.raises(ValueError, match="changed after apply"):
        repair.post_patch_check(copy, proposal, applied)


def test_r6_refuses_a_proposal_from_a_different_patch(tmp_path):
    draft, _, bundle, _ = _ready_bundle(tmp_path)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    copy = tmp_path / "copy.md"
    applied = repair.apply_patch(draft, proposal, _synthetic_receipt(proposal),
                                 copy, allow_synthetic_test=True)
    other = dict(proposal, patch_id="r5_someotherpatch")
    with pytest.raises(ValueError, match="describe different patches"):
        repair.post_patch_check(copy, other, applied)


def test_no_repair_is_offered_that_asserts_an_unevidenced_defect(tmp_path):
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    # Zero prior evidence: Z0 itself says "not audited, do not assume defect".
    bundle = repair.plan_repair(audit, tmp_path / "out", case["case_id"], draft,
                               queue_orders=orders)
    assert _candidate(bundle, "REMOVE_UNSUPPORTED_CITATION")["applicable"] is False
    assert _candidate(bundle, "BIBLIOGRAPHY_DETAIL_REPAIR")["applicable"] is False
    assert _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")["applicability"] == (
        "NOT_APPLICABLE_NO_EVIDENCE_ON_RECORD_THAT_THE_SOURCE_LACKS_SUPPORT")
    # ABSTAIN remains the honest default.
    assert _candidate(bundle, "ABSTAIN_NO_CHANGE")["applicable"] is True
    assert "NO_R1_EVIDENCE_ON_RECORD" in bundle["r2_intent"]["uncertainties"]


def test_prior_state_bound_to_another_manuscript_version_is_refused(tmp_path):
    draft = _draft(tmp_path)
    audit, _, _, case = _z0(tmp_path, draft)
    source_sha = json.loads(audit.read_text(encoding="utf-8"))["source"]["sha256"]
    stale = tmp_path / "stale.state.json"
    stale.write_text(json.dumps({
        "schema": "trm-cite-r1-case-state-v1", "case_id": case["case_id"],
        "source_sha256": "0" * 64, "outcome": "OBSERVED",
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="different manuscript version"):
        repair.load_prior_states([tmp_path], source_sha)
    # The same file is accepted when no expected version is supplied.
    assert len(repair.load_prior_states([tmp_path])) == 1


def test_frozen_records_do_not_alias_the_source_audit(tmp_path):
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    _prior_state(tmp_path, case)
    bundle = repair.plan_repair(
        audit, tmp_path / "out", case["case_id"], draft,
        prior_states=repair.load_prior_states([tmp_path]), queue_orders=orders)
    intent = repair.reconstruct_intent(
        json.loads((Path(audit)).read_text(encoding="utf-8")),
        case["case_id"], [])
    intake = next(i for i in json.loads(Path(audit).read_text(encoding="utf-8"))
                  ["intakes"] if i["intake_id"] == intent.intake_id)
    before = json.dumps(intake["anchor"], sort_keys=True)
    intent.anchor["locator"] = "tampered"
    assert json.dumps(intake["anchor"], sort_keys=True) == before
    assert bundle["author_gate"] == "PENDING"


def _author_receipt(proposal, key, decision="APPROVE"):
    receipt = _synthetic_receipt(proposal, decision=decision, synthetic=False)
    receipt["witness_class"] = "HUMAN_AUTHOR_DECISION"
    receipt["receipt_id"] = repair.receipt_identity(receipt)
    receipt["receipt_mac"] = repair.receipt_mac(receipt, key)
    return receipt


def test_keyed_receipt_mac_is_required_when_an_author_key_is_supplied(tmp_path):
    draft, _, bundle, _ = _ready_bundle(tmp_path)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    key = b"author-secret-not-in-the-repository"
    copy = tmp_path / "copy.md"

    # A receipt with no MAC cannot pass a keyed check.
    plain = _synthetic_receipt(proposal, synthetic=False)
    plain["witness_class"] = "HUMAN_AUTHOR_DECISION"
    plain["receipt_id"] = repair.receipt_identity(plain)
    with pytest.raises(ValueError, match="not keyed by the author's secret"):
        repair.apply_patch(draft, proposal, plain, copy, author_key=key)

    # A receipt keyed by the wrong secret is refused too.
    wrong = _author_receipt(proposal, b"a-different-secret")
    with pytest.raises(ValueError, match="not keyed by the author's secret"):
        repair.apply_patch(draft, proposal, wrong, copy, author_key=key)

    # The author's own key works.
    applied = repair.apply_patch(draft, proposal, _author_receipt(proposal, key),
                                 copy, author_key=key)
    assert applied["author_gate"] == "AUTHOR_APPROVED_THIS_PATCH_ONLY"
    assert applied["synthetic_test_receipt"] is False


def test_receipt_mac_covers_the_content_it_attests(tmp_path):
    draft, _, bundle, _ = _ready_bundle(tmp_path)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    key = b"author-secret"
    receipt = _author_receipt(proposal, key)
    # Editing the decision invalidates the MAC, not just the id.
    tampered = dict(receipt, decision="REJECT")
    with pytest.raises(ValueError, match="not keyed by the author's secret"):
        repair.apply_patch(draft, proposal, tampered, tmp_path / "copy.md",
                           author_key=key)
    assert repair.receipt_mac(receipt, key) != repair.receipt_mac(tampered, key)
    with pytest.raises(ValueError, match="non-empty bytes"):
        repair.receipt_mac(receipt, b"")


def test_r6_cannot_skip_original_reverification(tmp_path):
    draft, _, bundle, _ = _ready_bundle(tmp_path)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    copy = tmp_path / "copy.md"
    applied = repair.apply_patch(draft, proposal, _synthetic_receipt(proposal),
                                 copy, allow_synthetic_test=True)
    stripped = {k: v for k, v in applied.items()
                if k != "original_manuscript_path"}
    with pytest.raises(ValueError, match="record the original manuscript path"):
        repair.post_patch_check(copy, proposal, stripped)


def test_an_anchored_passage_vetoes_removing_the_citation(tmp_path):
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    _prior_state(tmp_path, case, outcome="OBSERVED",
                 read_depth="ANCHORED_PASSAGE", negatives=())
    anchored = tmp_path / f"{case['case_id']}.state.json"
    anchored.write_text(json.dumps(json.loads(anchored.read_text())), "utf-8")
    # An unrelated blocked hunt must not re-enable deletion.
    other = tmp_path / "other.state.json"
    other.write_text(json.dumps({
        "schema": "trm-cite-r1-case-state-v1", "case_id": case["case_id"],
        "source_sha256": _z0_source_sha(tmp_path), "outcome": "BLOCKED",
        "negative_evidence": ["UNRELATED_HUNT_NOT_FOUND"],
    }), encoding="utf-8")
    bundle = repair.plan_repair(
        audit, tmp_path / "out", case["case_id"], draft,
        prior_states=repair.load_prior_states([tmp_path]), queue_orders=orders)
    assert _candidate(bundle, "REMOVE_UNSUPPORTED_CITATION")["applicable"] is False
    assert "NO_EVIDENCE_ON_RECORD_THAT_THE_SOURCE_LACKS_SUPPORT" in \
        _candidate(bundle, "REMOVE_UNSUPPORTED_CITATION")["refusal_codes"]


def test_anchor_fragment_drift_is_detected(tmp_path):
    """Guard: the recorded fragment must still sit at the recorded offsets."""
    draft, _, bundle, _ = _ready_bundle(tmp_path)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    text, _ = repair._decode(draft.read_bytes())
    anchor = proposal["anchor"]
    shifted = dict(anchor, start_codepoint=anchor["start_codepoint"] - 5,
                   end_codepoint=anchor["end_codepoint"] - 5)
    with pytest.raises(ValueError, match="no longer match the recorded"):
        repair.resolve_patch_span(text, shifted, proposal["old_text"],
                                  proposal["original_fragment"], True)


def test_patched_sha_reproducibility_guard_is_load_bearing(tmp_path):
    draft, _, bundle, _ = _ready_bundle(tmp_path)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    forged = dict(proposal, patched_manuscript_sha256="f" * 64)
    forged["receipt_note"] = None
    receipt = _synthetic_receipt(proposal)
    with pytest.raises(ValueError, match="patched SHA"):
        repair.apply_patch(draft, forged, receipt, tmp_path / "copy.md",
                           allow_synthetic_test=True)
    assert not (tmp_path / "copy.md").exists()
    assert draft.read_bytes() == MANUSCRIPT.encode("utf-8")


def test_applied_proposal_cannot_be_replayed(tmp_path):
    """Guard: a proposal already applied is no longer in a PENDING state."""
    draft, _, bundle, _ = _ready_bundle(tmp_path)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    stale = dict(proposal, author_gate="APPROVED", applied=True)
    receipt = _synthetic_receipt(stale)
    receipt["receipt_id"] = repair.receipt_identity(receipt)
    with pytest.raises(ValueError, match="not in an applicable PENDING state"):
        repair.apply_patch(draft, stale, receipt, tmp_path / "copy.md",
                           allow_synthetic_test=True)
    assert not (tmp_path / "copy.md").exists()


def test_replacement_text_must_contain_the_verified_fragment(tmp_path):
    draft, _, bundle, _ = _ready_bundle(tmp_path)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    text, _ = repair._decode(draft.read_bytes())
    with pytest.raises(ValueError, match="does not contain the verified"):
        repair.resolve_patch_span(text, proposal["anchor"], "scored by rubric",
                                  proposal["original_fragment"], True)


def test_inverse_diff_is_recomputed_not_trusted(tmp_path):
    draft, _, bundle, _ = _ready_bundle(tmp_path)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    forged = dict(proposal, inverse_diff="BOGUS UNDO")
    forged["inverse_diff_sha256"] = repair._text_digest("BOGUS UNDO")
    receipt = _synthetic_receipt(forged)
    receipt["receipt_id"] = repair.receipt_identity(receipt)
    with pytest.raises(ValueError, match="inverse diff"):
        repair.apply_patch(draft, forged, receipt, tmp_path / "copy.md",
                           allow_synthetic_test=True)
    assert not (tmp_path / "copy.md").exists()


def test_malformed_records_raise_typed_refusals_not_keyerrors(tmp_path):
    """Every proposal field an apply/readback reads must be validated up front."""
    draft, _, bundle, _ = _ready_bundle(tmp_path)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    receipt = _synthetic_receipt(proposal)
    copy = tmp_path / "copy.md"
    for field in repair._PROPOSAL_REQUIRED_FIELDS:
        broken = {k: v for k, v in proposal.items() if k != field}
        with pytest.raises(repair.RepairRefusal, match="missing required"):
            repair.apply_patch(draft, broken, receipt,
                               tmp_path / f"c_{field}.md",
                               allow_synthetic_test=True)
        assert not (tmp_path / f"c_{field}.md").exists()
    applied = repair.apply_patch(draft, proposal, receipt, copy,
                                 allow_synthetic_test=True)
    for field in repair._PROPOSAL_REQUIRED_FIELDS:
        broken = {k: v for k, v in proposal.items() if k != field}
        with pytest.raises(repair.RepairRefusal, match="missing required"):
            repair.post_patch_check(copy, broken, applied)
    assert draft.read_bytes() == MANUSCRIPT.encode("utf-8")
    # A non-object anchor is also typed, not a TypeError.
    with pytest.raises(repair.RepairRefusal, match="anchor is not an object"):
        repair.apply_patch(draft, dict(proposal, anchor=["not", "a", "dict"]),
                           receipt, copy, allow_synthetic_test=True)


def test_missing_original_snapshot_is_a_typed_refusal(tmp_path):
    draft, _, bundle, _ = _ready_bundle(tmp_path)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    copy = tmp_path / "copy.md"
    applied = repair.apply_patch(draft, proposal, _synthetic_receipt(proposal),
                                 copy, allow_synthetic_test=True)
    with pytest.raises(repair.RepairRefusal, match="not readable"):
        repair.undo_patch(copy, applied, tmp_path / "absent.md",
                          tmp_path / "restored.md")


def test_apply_detects_original_drift_before_writing(tmp_path, monkeypatch):
    """Guard: the original must be re-checked BEFORE anything is written.

    Simulates the manuscript changing between validation and the write, which
    is the window the pre-write re-check exists to close.
    """
    draft, _, bundle, _ = _ready_bundle(tmp_path)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    receipt = _synthetic_receipt(proposal)
    copy = tmp_path / "copy.md"
    real = Path.read_bytes
    reads = {"n": 0}

    def flaky(self):
        if self.resolve() == draft.resolve():
            reads["n"] += 1
            # Call 1 is the validation read; call 2 is the pre-write re-check.
            if reads["n"] >= 2:
                return b"TAMPERED MID-FLIGHT\n"
        return real(self)

    monkeypatch.setattr(Path, "read_bytes", flaky)
    with pytest.raises(ValueError, match="changed while the patch was being"):
        repair.apply_patch(draft, proposal, receipt, copy,
                           allow_synthetic_test=True)
    monkeypatch.undo()
    assert not copy.exists()
    assert draft.read_bytes() == MANUSCRIPT.encode("utf-8")


def test_module_exposes_no_receipt_minting_entry_point():
    exported = {name for name in dir(repair) if not name.startswith("_")}
    receipt_callables = {name for name in exported
                         if "receipt" in name.lower()
                         and callable(getattr(repair, name))}
    # receipt_identity/receipt_mac compute an author's attestation; they cannot
    # turn an unapproved case into an approved one. Nothing here CREATES a
    # decision, an APPROVE outcome, or a PENDING proposal.
    assert receipt_callables == {"receipt_identity", "receipt_mac",
                                 "validate_decision_receipt"}
    for forbidden in ("mint_receipt", "issue_receipt", "approve_patch",
                      "auto_approve", "synthetic_receipt", "make_receipt",
                      "sign_receipt", "grant_approval", "authorize_patch",
                      "create_receipt", "build_receipt", "forge_receipt"):
        assert not hasattr(repair, forbidden)
    source = Path(repair.__file__).read_text(encoding="utf-8")
    # The pipeline MAY persist its own apply/undo/check records, but it must
    # never PERSIST a decision receipt: an approval is author input, never an
    # output this code produces.
    written = [line.strip() for line in source.splitlines()
               if line.strip().startswith(("_write_immutable",
                                           "_write_json_immutable("))]
    assert written, "expected the pipeline to persist some of its own records"
    for line in written:
        low = line.lower()
        assert "decision" not in low
        assert "approv" not in low
    assert any("apply_receipt" in line for line in written)
    # And no code path defaults the synthetic sandbox open.
    assert "allow_synthetic_test: bool = True" not in source


def test_plan_bundle_declares_no_certification_and_no_write(tmp_path):
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    _prior_state(tmp_path, case)
    bundle = repair.plan_repair(
        audit, tmp_path / "out", case["case_id"], draft,
        prior_states=repair.load_prior_states([tmp_path]), queue_orders=orders)
    assert bundle["verification"] == {f"V{i}": "NOT_CHECKED" for i in range(1, 6)}
    assert bundle["citation_gate"] == "NOT_PUBLICATION_READY"
    assert bundle["author_gate"] == "PENDING"
    assert bundle["manuscript_mutated"] is False
    assert bundle["applied_to_copy"] is False
    assert bundle["external_search_authorized_by_this_object"] is False
    assert bundle["source_certification"] == "NONE_TRANSPORT_IS_NOT_CERTIFICATION"
    assert bundle["work_edition_witness_provenance"][
        "operator_declarations_not_independently_proved"] is True


def test_docx_and_pdf_surfaces_are_blocked_not_faked(tmp_path):
    # A real Z0 audit is minted from the Markdown twin; only the manuscript
    # surface changes, so the refusal must come from R5 surface coverage.
    draft = _draft(tmp_path)
    audit, _, _, case = _z0(tmp_path, draft)
    docx = tmp_path / "synthetic.docx"
    docx.write_bytes(draft.read_bytes())
    _prior_state(tmp_path, case)
    with pytest.raises(ValueError, match="native editor service: BLOCKED"):
        repair.plan_repair(audit, tmp_path / "out", case["case_id"], docx,
                           prior_states=repair.load_prior_states([tmp_path]))
    pdf = tmp_path / "synthetic.pdf"
    pdf.write_bytes(draft.read_bytes())
    with pytest.raises(ValueError, match="native editor service: BLOCKED"):
        repair.plan_repair(audit, tmp_path / "out", case["case_id"], pdf)
    assert docx.read_bytes() == MANUSCRIPT.encode("utf-8")
    assert pdf.read_bytes() == MANUSCRIPT.encode("utf-8")
    # A blocked surface must not silently fall back to a text patch.
    assert not list((tmp_path / "out").rglob("*.json"))


def test_provenance_fields_survive_into_the_plan(tmp_path):
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    state = _prior_state(tmp_path, case, outcome="OBSERVED",
                         read_depth="ANCHORED_PASSAGE", negatives=())
    state["source_identity"] = {
        "work_id": "work-fictional", "edition_id": "edition-fictional",
        "witness_id": "witness-fictional", "passage_id": "passage-fictional",
    }
    (tmp_path / f"{case['case_id']}.state.json").write_text(
        json.dumps(state), encoding="utf-8")
    bundle = repair.plan_repair(
        audit, tmp_path / "out", case["case_id"], draft,
        prior_states=repair.load_prior_states([tmp_path]), queue_orders=orders)
    carried = bundle["work_edition_witness_provenance"]["carried_from_prior_states"]
    assert carried[0]["identity"] == state["source_identity"]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def test_cli_plan_is_the_default_and_writes_no_manuscript(tmp_path, capsys):
    draft = _draft(tmp_path)
    before = draft.read_bytes()
    audit, _, _, case = _z0(tmp_path, draft)
    _prior_state(tmp_path, case)
    code = cli_main(["cite-repair", "--audit", str(audit), "--case",
                     case["case_id"], "--manuscript", str(draft),
                     "--out", str(tmp_path / "out")])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == repair.PLAN_SCHEMA
    assert payload["author_gate"] == "PENDING"
    assert draft.read_bytes() == before
    assert not list((tmp_path / "out").rglob("*.md"))


def test_cli_apply_check_and_undo_round_trip(tmp_path, capsys):
    draft = _draft(tmp_path)
    original = draft.read_bytes()
    audit, _, _, case = _z0(tmp_path, draft)
    _consulted_negative_state(tmp_path, case)
    cli_main(["cite-repair", "plan", "--audit", str(audit), "--case",
              case["case_id"], "--manuscript", str(draft),
              "--out", str(tmp_path / "out"),
              "--prior-state", str(tmp_path)])
    capsys.readouterr()
    bundle = json.loads(next((tmp_path / "out").rglob("plan_*.json"))
                        .read_text(encoding="utf-8"))
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(json.dumps(proposal), encoding="utf-8")
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(
        json.dumps(_synthetic_receipt(proposal)), encoding="utf-8")
    copy = tmp_path / "copy.md"

    # The CLI exposes no synthetic sandbox, so a synthetic receipt is refused.
    code = cli_main(["cite-repair", "apply", "--manuscript", str(draft),
                     "--proposal", str(proposal_path), "--receipt",
                     str(receipt_path), "--copy", str(copy),
                     "--out", str(tmp_path / "apply")])
    assert code == 2
    assert "Synthetic test receipt" in capsys.readouterr().err
    assert not copy.exists()

    # The sandbox is Python-level only.
    applied = repair.apply_patch(draft, proposal,
                                 _synthetic_receipt(proposal), copy,
                                 allow_synthetic_test=True)
    apply_path = tmp_path / "apply" / "apply_receipt.json"
    repair._write_json_immutable(apply_path, applied)

    code = cli_main(["cite-repair", "check", "--proposal", str(proposal_path),
                     "--apply-receipt", str(apply_path), "--copy", str(copy),
                     "--out", str(tmp_path / "check")])
    assert code == 3  # scientific debt, not a pass
    check = json.loads((tmp_path / "check" / "post_patch_check.json")
                       .read_text(encoding="utf-8"))
    assert check["scientific_status"] == "DEBT_RETAINED_NO_PUBLICATION_PASS"
    assert check["original_manuscript_reverified"] is True
    capsys.readouterr()

    snapshot = Path(json.loads(audit.read_text(encoding="utf-8"))["source"]
                    ["original_snapshot_path"])
    code = cli_main(["cite-repair", "undo", "--apply-receipt", str(apply_path),
                     "--copy", str(copy), "--original-snapshot", str(snapshot),
                     "--restored", str(tmp_path / "restored.md"),
                     "--out", str(tmp_path / "undo")])
    assert code == 0
    assert (tmp_path / "restored.md").read_bytes() == original
    assert draft.read_bytes() == original


def test_cli_exposes_no_synthetic_sandbox_switch():
    parser_text = (Path(repair.__file__).read_text(encoding="utf-8"))
    assert "--allow-synthetic-test" not in parser_text
    cli_text = Path(cli.__file__).read_text(encoding="utf-8")
    assert "allow_synthetic_test" not in cli_text
    with pytest.raises(SystemExit):
        cli_main(["cite-repair", "apply", "--help"])


def test_cli_refusal_returns_two_and_leaves_no_artifact(tmp_path, capsys):
    draft = _draft(tmp_path)
    audit, _, _, case = _z0(tmp_path, draft)
    code = cli_main(["cite-repair", "plan", "--audit", str(audit), "--case",
                     case["case_id"], "--manuscript", str(draft),
                     "--out", str(tmp_path / "out"),
                     "--expected-manuscript-sha256", "0" * 64])
    assert code == 2
    assert "refused" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()

def test_blocked_source_cannot_justify_deleting_a_citation(tmp_path):
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    _prior_state(tmp_path, case, outcome="BLOCKED", read_depth="NONE",
                 negatives=("SOURCE_READER_NOT_AVAILABLE",))
    bundle = repair.plan_repair(
        audit, tmp_path / "out", case["case_id"], draft,
        prior_states=repair.load_prior_states([tmp_path]), queue_orders=orders)
    candidate = _candidate(bundle, "REMOVE_UNSUPPORTED_CITATION")
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    assert candidate["applicable"] is False
    assert "NO_EVIDENCE_ON_RECORD_THAT_THE_SOURCE_LACKS_SUPPORT" in candidate["refusal_codes"]
    assert proposal["applicability"] != "READY_FOR_AUTHOR_REVIEW"


def test_observed_unassessed_source_does_not_justify_deletion(tmp_path):
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    state = _prior_state(tmp_path, case, outcome="OBSERVED",
                         read_depth="SECTION_TEXT", negatives=())
    state["source_identity"]["witness_id"] = "FICTIONAL_SECTION_WITNESS"
    (tmp_path / f"{case['case_id']}.state.json").write_text(json.dumps(state))
    bundle = repair.plan_repair(
        audit, tmp_path / "out", case["case_id"], draft,
        prior_states=repair.load_prior_states([tmp_path]), queue_orders=orders)
    assert _candidate(bundle,"REMOVE_UNSUPPORTED_CITATION")["applicable"] is False


def test_negative_without_readable_witness_cannot_justify_deletion(tmp_path):
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    state = _prior_state(tmp_path, case, outcome="NEGATIVE",
                         read_depth="NONE", negatives=("LOOKUP_EMPTY",))
    state["source_to_claim_relation"] = "DOES_NOT_SUPPORT_CLAIM"
    (tmp_path / f"{case['case_id']}.state.json").write_text(json.dumps(state))
    bundle = repair.plan_repair(
        audit, tmp_path / "out", case["case_id"], draft,
        prior_states=repair.load_prior_states([tmp_path]), queue_orders=orders)
    assert _candidate(bundle,"REMOVE_UNSUPPORTED_CITATION")["applicable"] is False


def test_synthetic_witness_class_persists_when_flag_missing(tmp_path):
    draft, _, bundle, _ = _ready_bundle(tmp_path)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    receipt = _synthetic_receipt(proposal)
    del receipt["synthetic"]
    receipt["receipt_id"] = repair.receipt_identity(receipt)
    copied = tmp_path / "synthetic-copy.md"
    applied = repair.apply_patch(draft, proposal, receipt, copied,
                                allow_synthetic_test=True)
    assert applied["synthetic_test_receipt"] is True
    assert applied["decision_witness_class"] == "SYNTHETIC_TEST"
    checked = repair.post_patch_check(copied, proposal, applied)
    assert checked["synthetic_test_receipt"] is True
    assert checked["decision_witness_class"] == "SYNTHETIC_TEST"


def test_missing_original_after_apply_returns_typed_refusal(tmp_path):
    draft, _, bundle, _ = _ready_bundle(tmp_path)
    proposal = _proposal(bundle, "REMOVE_UNSUPPORTED_CITATION")
    copied = tmp_path / "copy.md"
    applied = repair.apply_patch(draft, proposal,
                                 _synthetic_receipt(proposal), copied,
                                 allow_synthetic_test=True)
    draft.unlink()
    with pytest.raises(repair.RepairRefusal) as caught:
        repair.post_patch_check(copied, proposal, applied)
    assert caught.value.code == "ORIGINAL_MISSING_AFTER_APPLY"


def test_real_r1_consumer_source_evidence_shape_does_not_trigger_rehunt(tmp_path):
    """R1 serializes anchors in source_evidence[], not source_identity.

    A genuine unique passage is recognized for planning; V1-V5 remain
    independently unverified. No synthetic witness becomes scientific PASS.
    """
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    state = _prior_state(tmp_path, case, outcome="OBSERVED",
                         read_depth="ANCHORED_PASSAGE", negatives=())
    state.pop("source_identity", None)
    state["source_evidence"] = [{
        "work_id": "FICTIONAL_WORK_A",
        "edition_id": "FICTIONAL_EDITION_1",
        "witness_id": "SHA256_FICTIONAL_WITNESS",
        "read_depth": "ANCHORED_PASSAGE",
        "passage_id": "passage:fictional_unique_1",
        "passage_occurrences": 1,
        "locator_present": True,
        "locator": "[PDF_PAGE_INDEX_1]",
        "source_provenance": "OWNER_CORPUS",
    }]
    (tmp_path / f"{case['case_id']}.state.json").write_text(
        json.dumps(state), encoding="utf-8")
    bundle = repair.plan_repair(
        audit, tmp_path / "out", case["case_id"], draft,
        prior_states=repair.load_prior_states([tmp_path]), queue_orders=orders)
    assert bundle["r3_reentry"] is None
    assert "IDENTITY_AND_PASSAGE_PROPOSED" in {
        item["evidence_label"] for item in bundle["r4_candidates"]}
    assert _candidate(bundle, "REMOVE_UNSUPPORTED_CITATION")["applicable"] is False
    prior = bundle["work_edition_witness_provenance"]["carried_from_prior_states"][0]
    assert prior["identity"]["witness_id"] == "SHA256_FICTIONAL_WITNESS"
    assert prior["witnesses"][0]["source_provenance"] == "OWNER_CORPUS"
    assert set(bundle["verification"].values()) == {"NOT_CHECKED"}
    assert bundle["citation_gate"] == "NOT_PUBLICATION_READY"


def test_actual_r1_invalid_anchor_id_does_not_shortcut_research(tmp_path):
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    state = _prior_state(tmp_path, case, outcome="OBSERVED",
                         read_depth="ANCHORED_PASSAGE", negatives=())
    state.pop("source_identity", None)
    state["source_evidence"] = [{
        "witness_id": "FICTIONAL_WITNESS",
        "read_depth": "ANCHORED_PASSAGE",
        "passage_id": "passage:anchor_missing",
        "passage_occurrences": 1,
        "locator_present": True,
    }]
    (tmp_path / f"{case['case_id']}.state.json").write_text(
        json.dumps(state), encoding="utf-8")
    bundle = repair.plan_repair(
        audit, tmp_path / "out", case["case_id"], draft,
        prior_states=repair.load_prior_states([tmp_path]), queue_orders=orders)
    assert bundle["r3_reentry"] is not None
    assert "IDENTITY_ONLY_PROPOSED" in {
        item["evidence_label"] for item in bundle["r4_candidates"]}
    assert bundle["citation_gate"] == "NOT_PUBLICATION_READY"


def test_real_r1_incomplete_passage_proof_requires_reentry(tmp_path):
    """A real R1 record may not self-certify an anchor with missing proof."""
    draft = _draft(tmp_path)
    audit, queue, orders, case = _z0(tmp_path, draft)
    state = _prior_state(tmp_path, case, outcome="OBSERVED",
                         read_depth="ANCHORED_PASSAGE", negatives=())
    state.pop("source_identity", None)
    source_evidence = {
        "witness_id": "FICTIONAL_WITNESS",
        "read_depth": "ANCHORED_PASSAGE",
        "passage_id": "passage:fictional",
        "passage_occurrences": 1,
        "locator_present": True,
    }
    for removed in ("passage_id", "passage_occurrences", "locator_present"):
        invalid = dict(source_evidence)
        invalid.pop(removed)
        state["source_evidence"] = [invalid]
        (tmp_path / f"{case['case_id']}.state.json").write_text(
            json.dumps(state), encoding="utf-8")
        location = tmp_path / ("out_" + removed)
        bundle = repair.plan_repair(
            audit, location, case["case_id"], draft,
            prior_states=repair.load_prior_states([tmp_path]),
            queue_orders=orders)
        assert bundle["r3_reentry"] is not None, removed
        assert _candidate(bundle,"REMOVE_UNSUPPORTED_CITATION")["applicable"] is False
