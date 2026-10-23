"""TRM-CITE-002 R2-R6: deterministic, replay-safe, author-gated citation repair.

This module never fetches a source, never writes the original manuscript and
never certifies a citation. It turns an immutable Z0 audit plus any existing R1
case states into five typed objects:

* ``IntentReconstruction`` (R2) - provisional reconstruction of the author's
  existing claim, the support they actually need, the verbatim source
  references already on record, and the explicit uncertainties.
* ``ResearchReentry`` (R3) - a *new bounded* research request, emitted only when
  nothing on hand can answer R2. Prior negative evidence is carried forward and
  Indago-hunt provenance is preserved; a reentry never deletes or supersedes an
  earlier request.
* ``RepairCandidate`` (R4) - several distinct repairs with differing
  intellectual cost, an explicit source-to-claim relation and the scientific
  debt each one carries. Nothing is approved automatically.
* ``ProposalPatch`` (R5) - an exact target manuscript SHA, the exact original
  anchor and old-text SHA, suggested new text, and a reversible whole-file diff.
  Always ``author_gate = PENDING``; planning never writes the manuscript.
* ``PostPatchCheck`` (R6) - a readback of the applied *copy* through the same
  Z0 intake, reporting retained scientific debt instead of a fabricated V1-V5
  success.

The author's decision is an external ``DecisionReceipt`` bound to the exact
manuscript SHA, claim, candidate, diff and the exact bytes that would be
written. The binding is recomputed from the manuscript at apply time, so an
approval cannot be replayed against different text.

What this module enforces, mechanically:

* the module contains no function that mints, issues or self-approves a
  receipt, and no command-line surface accepts a synthetic one;
* a receipt must be bound to one exact patch, and the written bytes are
  recomputed from the manuscript and matched against the signed diff;
* editing any field that decides whether a write is authorised - including
  ``synthetic``, ``witness_class`` and ``issuer_role`` - invalidates the
  receipt id;
* an operator may additionally demand a keyed ``receipt_mac`` (HMAC-SHA256
  over the receipt identity) to attest that the receipt really came from the
  author rather than from a peer process.

What this module cannot enforce: on a single shared machine a peer process can
write any file, so *provenance* of the receipt is an operator and process
control property, not something this code can cryptographically establish.
Treat a receipt as author-attested only when it arrived through a channel the
author controls - for example the keyed ``receipt_mac`` above, or a receipt
delivered directly by the author. A JSON file that merely *says*
``issued_by: AUTHOR`` is a claim, not an approval.

Surface coverage is deliberately narrow: R5 anchoring and application are
implemented for the ``line:`` body sections of UTF-8 Markdown and plain text
that Z0 already scans. DOCX, PDF and structured-envelope surfaces are refused
with an explicit BLOCKED status rather than faked.
"""
from __future__ import annotations

import argparse
import copy
import dataclasses
import difflib
import hashlib
import hmac
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .citation_intake_z0 import (
    VERSION as Z0_VERSION,
    _id,
    _write_immutable,
    audit_manuscript,
)

VERSION = "trm-cite-r2-r6-v01"

PLAN_SCHEMA = "trm-cite-r2-r6-plan-v1"
INTENT_SCHEMA = "trm-cite-r2-intent-v1"
REENTRY_SCHEMA = "trm-cite-r3-reentry-v1"
CANDIDATES_SCHEMA = "trm-cite-r4-candidates-v1"
PROPOSAL_SCHEMA = "trm-cite-r5-proposal-v1"
RECEIPT_SCHEMA = "trm-cite-r2-decision-receipt-v1"
APPLY_SCHEMA = "trm-cite-r5-apply-receipt-v1"
UNDO_SCHEMA = "trm-cite-r5-undo-receipt-v1"
CHECK_SCHEMA = "trm-cite-r6-post-patch-check-v1"
CANDIDATE_TEXT_SCHEMA = "trm-cite-r5-candidate-text-v1"

VERIFICATION_KEYS = ("V1", "V2", "V3", "V4", "V5")
NOT_CHECKED = {key: "NOT_CHECKED" for key in VERIFICATION_KEYS}

# R4 repair repertoire: kind -> (intellectual cost, source-to-claim relation).
# The relation states what the source does for the claim *after* the repair.
REPAIR_REPERTOIRE: dict[str, tuple[str, str]] = {
    "BIBLIOGRAPHY_DETAIL_REPAIR": (
        "LOW",
        "IDENTITY_CORRECTED_ARGUMENTATIVE_SUPPORT_STILL_UNREVIEWED",
    ),
    "CHANGE_SOURCE": (
        "HIGH",
        "NEW_SOURCE_MUST_CARRY_THE_EXISTING_CLAIM",
    ),
    "PRESENT_NORMATIVE_AUTHOR_CONCLUSION_EXPLICITLY": (
        "MEDIUM",
        "SOURCE_DECOUPLED_CLAIM_ATTRIBUTED_TO_THE_AUTHOR_NOT_TO_THE_SOURCE",
    ),
    "WEAKEN_OR_SPLIT_THESIS": (
        "HIGH",
        "CLAIM_SCOPE_REDUCED_TO_WHAT_THE_SOURCE_ESTABLISHES",
    ),
    "REMOVE_UNSUPPORTED_CITATION": (
        "MEDIUM",
        "CLAIM_RETAINED_SOURCE_LINK_DELETED",
    ),
    "ABSTAIN_NO_CHANGE": (
        "NONE",
        "NO_CHANGE_PROPOSED",
    ),
}

# Kinds whose new text the machine may derive structurally from the anchor.
# Anything else needs author/analyst wording: this module will not invent
# scholarly prose.
MACHINE_RENDERABLE = frozenset({"REMOVE_UNSUPPORTED_CITATION"})

DECISIONS = ("APPROVE", "REJECT", "REQUEST_REVISION")
NON_HUMAN_ISSUERS = frozenset({
    "AI", "ASSISTANT", "AGENT", "MODEL", "LLM", "AUTOMATION", "PIPELINE",
})
ALLOWED_WITNESS_CLASSES = ("HUMAN_AUTHOR_DECISION", "SYNTHETIC_TEST")

READABLE_WRITABLE_SUFFIXES = (".md", ".txt")
ANCHORED_READ_DEPTHS = ("ANCHORED_PASSAGE", "FULL_BOOK")
SAFE_NAME = re.compile(r"[A-Za-z0-9_.-]{1,120}")


class RepairRefusal(ValueError):
    """A typed fail-closed refusal. Never a partial success."""

    def __init__(self, message: str, code: str = "REFUSED") -> None:
        super().__init__(message)
        self.code = code


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _text_digest(value: str) -> str:
    return _digest(value.encode("utf-8"))


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise RepairRefusal("Expected JSON object: " + str(path))
    return value


def _bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       indent=2) + "\n").encode()


def _write_json_immutable(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_immutable(path, _bytes(payload))
    return path


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line
            in Path(path).read_text(encoding="utf-8-sig").splitlines()
            if line.strip()]
    if any(not isinstance(row, dict) for row in rows):
        raise RepairRefusal("JSONL rows must be objects: " + str(path))
    return rows


def _safe_component(value: str) -> str:
    """Reject anything that is not a plain filename component."""
    if not SAFE_NAME.fullmatch(value) or value in (".", ".."):
        raise RepairRefusal("Unsafe identifier used as a filename: " + value,
                            "UNSAFE_IDENTIFIER")
    return value


def _owned(mapping: Any) -> dict[str, Any]:
    """Deep-copy a mapping so a frozen record never aliases caller state."""
    return copy.deepcopy(dict(mapping))


# --------------------------------------------------------------------------
# typed objects
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class IntentReconstruction:
    """R2: what the manuscript already claims and what support it needs."""

    schema: str
    intent_id: str
    case_id: str
    intake_id: str
    source_sha256: str
    origin_type: str
    citation_kind: str
    existing_claim: str
    claim_context: str
    anchor: dict[str, Any]
    desired_support: str
    verbatim_source_refs: tuple[str, ...]
    prior_evidence_summary: tuple[str, ...]
    uncertainties: tuple[str, ...]
    reconstruction_mode: str
    author_confirmed: bool
    citation_certified: bool

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class ResearchReentry:
    """R3: a bounded new research request, only when nothing on hand answers R2."""

    schema: str
    reentry_id: str
    intent_id: str
    bounded_question: str
    required_output: tuple[str, ...]
    reason_codes: tuple[str, ...]
    carries_negative_evidence: tuple[str, ...]
    prior_request_ids: tuple[str, ...]
    prior_request_ids_complete: bool
    indago_hunt: str
    indago_provenance: tuple[str, ...]
    supersedes_prior_requests: bool
    execution_status: str
    acquisition_authorized_by_this_object: bool

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class RepairCandidate:
    """R4: one evidence-labelled repair option, never auto-approved."""

    candidate_id: str
    intent_id: str
    kind: str
    rank: int
    intellectual_cost: str
    source_to_claim_relation: str
    source_explanation: str
    debt_explanation: str
    scientific_debt: tuple[str, ...]
    evidence_label: str
    applicable: bool
    refusal_codes: tuple[str, ...]
    text_source: str
    author_gate: str
    auto_approved: bool
    verification_certified: bool

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class ProposalPatch:
    """R5: a reversible, author-gated patch proposal. Planning writes nothing."""

    schema: str
    patch_id: str
    candidate_id: str
    intent_id: str
    case_id: str
    target_manuscript_sha256: str
    target_surface: str
    target_locator: str
    anchor: dict[str, Any]
    original_fragment: str
    original_fragment_sha256: str
    old_text: str
    original_text_sha256: str
    suggested_new_text: str
    new_text_sha256: str
    patched_manuscript_sha256: str
    diff: str
    diff_sha256: str
    inverse_diff: str
    inverse_diff_sha256: str
    applicability: str
    debts: tuple[str, ...]
    text_source: str
    author_gate: str
    manuscript_mutated: bool
    applied: bool

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class PostPatchCheck:
    """R6: readback of an applied copy. Debt is retained; no false pass."""

    schema: str
    check_id: str
    case_id: str
    candidate_id: str
    patch_id: str
    apply_receipt_sha256: str
    original_manuscript_sha256: str
    applied_copy_sha256: str
    original_manuscript_reverified: bool
    reread_status: str
    reread_intake_id: str | None
    citation_present_after_patch: bool
    fragment_after_patch: str | None
    verification: dict[str, str]
    journal_style: str
    scientific_debts: tuple[str, ...]
    citation_gate: str
    author_gate: str
    scientific_status: str
    any_verification_passed: bool
    z0_coverage_debts: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


# --------------------------------------------------------------------------
# manuscript geometry
# --------------------------------------------------------------------------

def _decode(raw: bytes) -> tuple[str, bool]:
    """Decode without universal-newline translation so bytes round-trip."""
    return raw.decode("utf-8-sig"), raw.startswith(b"\xef\xbb\xbf")


def _encode(text: str, has_bom: bool) -> bytes:
    raw = text.encode("utf-8")
    return b"\xef\xbb\xbf" + raw if has_bom else raw


def _line_spans(text: str, is_markdown: bool) -> dict[str, tuple[int, int]]:
    """Codepoint spans of Z0's ``line:{i}`` body sections in the decoded text.

    Mirrors ``citation_intake_z0._load_sections`` for plain text and Markdown:
    every physical line is counted, fence lines and fenced content are not
    sections.
    """
    spans: dict[str, tuple[int, int]] = {}
    offset = 0
    fenced = False
    for index, line in enumerate(text.splitlines(keepends=True), 1):
        content = line.rstrip("\r\n")
        if is_markdown and re.match(r"^\s*(?:\x60{3}|~{3})", content):
            fenced = not fenced
        elif not fenced:
            spans[f"line:{index}"] = (offset, offset + len(content))
        offset += len(line)
    return spans


def resolve_patch_span(text: str, anchor: dict[str, Any], old_text: str,
                       original_fragment: str,
                       is_markdown: bool) -> tuple[int, int]:
    """Resolve a Z0 anchor plus a replacement span, or refuse.

    Every condition fails closed with a stable machine-readable code. Python
    slice semantics would make a negative offset alias a valid one, so offsets
    are range-checked before any slicing happens.
    """
    if not old_text:
        raise RepairRefusal("Stale or ambiguous passage: empty anchor text",
                            "EMPTY_ANCHOR_TEXT")
    spans = _line_spans(text, is_markdown)
    locator = str(anchor.get("locator", ""))
    if locator not in spans:
        raise RepairRefusal(
            "Stale or ambiguous passage: anchor locator absent from "
            "manuscript: " + locator, "ANCHOR_LOCATOR_ABSENT")
    start, end = spans[locator]
    section = text[start:end]
    try:
        low = int(anchor.get("start_codepoint", 0))
        high = int(anchor.get("end_codepoint", low))
    except (TypeError, ValueError) as exc:
        raise RepairRefusal(
            "Stale or ambiguous passage: anchor offsets are not integers",
            "ANCHOR_OFFSETS_NOT_INTEGERS") from exc
    if not 0 <= low <= high <= len(section):
        raise RepairRefusal(
            "Stale or ambiguous passage: anchor offsets out of range for the "
            "recorded locator", "ANCHOR_OFFSETS_OUT_OF_RANGE")
    # The Z0-recorded fragment must still sit at the recorded offsets.
    if section[low:high] != original_fragment:
        raise RepairRefusal(
            "Stale or ambiguous passage: anchor offsets no longer match the "
            "recorded original text", "ANCHOR_FRAGMENT_DRIFT")
    if section.count(old_text) != 1:
        raise RepairRefusal(
            "Stale or ambiguous passage: anchor text is not unique inside its "
            "section", "ANCHOR_TEXT_NOT_UNIQUE")
    if original_fragment not in old_text:
        raise RepairRefusal(
            "Stale or ambiguous passage: replacement text does not contain the "
            "verified original fragment", "REPLACEMENT_EXCLUDES_FRAGMENT")
    offset = section.index(old_text)
    return start + offset, start + offset + len(old_text)


def _file_diff(before: str, after: str, name: str) -> str:
    return "".join(difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        fromfile="a/" + name, tofile="b/" + name, n=3))


def _atomic_write_bytes(path: Path, raw: bytes) -> None:
    """Write a fresh file atomically; never overwrite an existing artifact."""
    path = Path(path)
    if path.exists():
        raise RepairRefusal(
            "Refusing to overwrite an existing file: " + str(path),
            "DESTINATION_EXISTS")
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=".apply-", dir=str(path.parent))
    os.close(handle)
    try:
        Path(temp_name).write_bytes(raw)
        os.replace(temp_name, path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise


# --------------------------------------------------------------------------
# R2
# --------------------------------------------------------------------------

def _desired_support(kind: str, origin_type: str) -> str:
    if origin_type == "AUTHOR_DESIRED":
        return "AUTHOR_STATED_SOURCE_NEED_STILL_UNKNOWN"
    if kind == "BIBLIOGRAPHY_ENTRY":
        return "IDENTITY_AND_BIBLIOGRAPHIC_DETAIL_OF_A_LISTED_WORK"
    if kind == "UNATTRIBUTED_QUOTE_CANDIDATE":
        return "ATTESTED_SOURCE_OR_AN_EXPLICIT_UNATTRIBUTED_QUOTE_DECISION"
    return ("WORK_EDITION_WITNESS_IDENTITY_PLUS_A_PASSAGE_THAT_ENTAILS_THE_CLAIM")


def _witness_descriptors(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Read old R2 descriptors and genuine R1 source_evidence[] records."""
    result: list[dict[str, Any]] = []
    legacy = state.get("source_identity")
    if isinstance(legacy, dict):
        result.append(legacy)
    for item in state.get("source_evidence") or ():
        if isinstance(item, dict):
            result.append(item)
    return result


def _observed_anchored(state: dict[str, Any]) -> bool:
    """Evidence of a real unique passage, NOT source-to-claim V1–V5 PASS."""
    if state.get("outcome") != "OBSERVED":
        return False
    for witness in _witness_descriptors(state):
        if witness.get("read_depth") not in ANCHORED_READ_DEPTHS:
            continue
        # A real R1 source_evidence[] entry is structurally stricter than
        # the historical operator-authored source_identity descriptor.
        # No paper is considered anchored if its actual R1 passage id,
        # occurrence count, or locator attestation is absent.
        if witness in (state.get("source_evidence") or ()):
            pid = witness.get("passage_id")
            if not isinstance(pid, str) or not pid.startswith("passage:"):
                continue
            if pid == "passage:anchor_missing":
                continue
            if witness.get("passage_occurrences") != 1:
                continue
            if witness.get("locator_present") is not True:
                continue
        else:
            if witness.get("passage_id") in (
                "passage:anchor_missing", "anchor_missing"):
                continue
            if ("passage_occurrences" in witness
                    and witness["passage_occurrences"] != 1):
                continue
            if witness.get("locator_present") is False:
                continue
        return True
    return False


def evidence_label(state: dict[str, Any]) -> str:
    outcome = state.get("outcome")
    if outcome == "OBSERVED":
        return ("IDENTITY_AND_PASSAGE_PROPOSED" if _observed_anchored(state)
                else "IDENTITY_ONLY_PROPOSED")
    if outcome == "NEGATIVE":
        return "NEGATIVE_EVIDENCE_ON_RECORD"
    return "NO_SOURCE_EVIDENCE"


def load_prior_states(paths: list[Path],
                      source_sha256: str | None = None) -> list[dict[str, Any]]:
    """Read existing R1 case states. Read-only; never rewritten or discarded.

    A state that declares a different manuscript version is stale evidence and
    is refused outright rather than silently contributing to a repair decision.
    """
    states: list[dict[str, Any]] = []
    for entry in paths or []:
        entry = Path(entry)
        found = sorted(entry.glob("*.state.json")) if entry.is_dir() else [entry]
        for item in found:
            state = _read_json(item)
            declared = state.get("source_sha256") or state.get(
                "original_source_sha256")
            if (source_sha256 and declared
                    and str(declared).lower() != source_sha256.lower()):
                raise RepairRefusal(
                    "Prior R1 state is bound to a different manuscript "
                    "version: " + str(item), "PRIOR_STATE_VERSION_DRIFT")
            state["_path"] = str(item)
            states.append(state)
    return states


def link_prior_states(audit: dict[str, Any], queue: list[dict[str, Any]],
                      states: list[dict[str, Any]]) -> tuple[list, list]:
    """Split carried evidence into case-linked and unlinked-but-preserved sets."""
    by_order = {o["work_order_id"]: o for o in queue}
    case_ids = {c["case_id"] for c in audit["repair_cases"]}
    linked: list[dict[str, Any]] = []
    unlinked: list[dict[str, Any]] = []
    for state in states:
        hit = state.get("case_id") in case_ids
        if not hit:
            order_ids = state.get("work_order_ids")
            if order_ids is None and state.get("work_order_id"):
                order_ids = [state["work_order_id"]]
            for oid in order_ids or ():
                order = by_order.get(oid)
                if order and order.get("case_id") in case_ids:
                    hit = True
                    break
        (linked if hit else unlinked).append(state)
    return linked, unlinked


def reconstruct_intent(audit: dict[str, Any], case_id: str,
                        states: list[dict[str, Any]],
                        operator_note: str | None = None) -> IntentReconstruction:
    """R2: provisional, deterministic reconstruction of the author's need."""
    case = next((c for c in audit["repair_cases"] if c["case_id"] == case_id), None)
    if case is None:
        raise RepairRefusal("Repair case is not in the original audit: "
                            + case_id, "UNKNOWN_CASE")
    intake = next((i for i in audit["intakes"]
                   if i["intake_id"] == case["intake_id"]), None)
    if intake is None:
        raise RepairRefusal("Repair case has no original intake: " + case_id,
                            "CASE_WITHOUT_INTAKE")
    source_sha = audit["source"]["sha256"]
    if intake["source_sha256"] != source_sha:
        raise RepairRefusal("Original manuscript SHA mismatch for " + case_id,
                            "INTAKE_VERSION_DRIFT")

    summary = tuple(sorted({
        f"{s.get('outcome', 'UNKNOWN')}:{evidence_label(s)}:"
        f"case={s.get('case_id')}:{s.get('_path', '')}" for s in states}))
    negatives = sorted({str(x) for s in states
                        for x in (s.get("negative_evidence") or [])})

    uncertainties = {
        "CLAIM_SUPPORT_NOT_INDEPENDENTLY_VERIFIED",
        "AUTHOR_INTENT_NOT_CONFIRMED_WITH_THE_AUTHOR",
        "VENUE_STYLE_PROFILE_NOT_SUPPLIED",
        "ORIGINAL_MANUSCRIPT_MUST_STAY_BYTE_IDENTICAL",
    }
    if not states:
        uncertainties.add("NO_R1_EVIDENCE_ON_RECORD")
    if negatives:
        uncertainties.add("NEGATIVE_EVIDENCE_REQUIRES_NEW_SOURCE_SEARCH")
    if any(v != "NOT_CHECKED" for v in case["verification"].values()):
        uncertainties.add("TRANSPORT_EVIDENCE_IS_NOT_SCIENTIFIC_CERTIFICATION")
    if not operator_note:
        uncertainties.add("NO_OPERATOR_NOTE_SUPPLIED")

    return IntentReconstruction(
        schema=INTENT_SCHEMA,
        intent_id=_id("r2", source_sha, case_id),
        case_id=case_id,
        intake_id=intake["intake_id"],
        source_sha256=source_sha,
        origin_type=intake["origin_type"],
        citation_kind=intake["kind"],
        existing_claim=intake["claim_context"].strip(),
        claim_context=intake["claim_context"],
        anchor=_owned(intake["anchor"]),
        desired_support=_desired_support(intake["kind"], intake["origin_type"]),
        verbatim_source_refs=tuple(intake["source_hints"]),
        prior_evidence_summary=summary,
        uncertainties=tuple(sorted(uncertainties)),
        reconstruction_mode=("OPERATOR_NOTE_PLUS_Z0_EVIDENCE" if operator_note
                             else "PROVISIONAL_FROM_Z0_EVIDENCE_ONLY"),
        author_confirmed=False,
        citation_certified=False,
    )


# --------------------------------------------------------------------------
# R3
# --------------------------------------------------------------------------

def plan_reentry(intent: IntentReconstruction, states: list[dict[str, Any]],
                 queue: list[dict[str, Any]]) -> ResearchReentry | None:
    """R3: emit a bounded reentry only when no carried evidence can answer R2."""
    if any(_observed_anchored(s) for s in states):
        # The file is already observed; do not dispatch a duplicate hunt.
        # Semantic V4 and publisher identity may still remain NOT_CHECKED.
        return None
    negatives = sorted({str(x) for s in states
                        for x in (s.get("negative_evidence") or [])})
    prior = sorted({str(o["work_order_id"]) for o in queue
                    if o.get("case_id") == intent.case_id})
    anchor = intent.anchor
    reasons = {"NO_ANCHORED_PASSAGE_EVIDENCE_ON_RECORD"}
    if negatives:
        reasons.add("NEGATIVE_EVIDENCE_REQUIRES_NEW_SOURCE_SEARCH")
    if not queue:
        reasons.add("WORK_ORDER_QUEUE_NOT_SUPPLIED_PRIOR_REQUESTS_UNKNOWN")
    return ResearchReentry(
        schema=REENTRY_SCHEMA,
        reentry_id=_id("r3", intent.intent_id),
        intent_id=intent.intent_id,
        bounded_question=(
            "Identify a Work/Edition/Witness whose verbatim passage entails the "
            f"claim anchored at {anchor.get('locator')} "
            f"[{anchor.get('start_codepoint')}:{anchor.get('end_codepoint')}], "
            "or record a durable negative result; do not promote transport into "
            "scientific support."),
        required_output=(
            "WORK_EDITION_WITNESS_IDENTITY",
            "VERBATIM_PASSAGE_WITH_LOCATOR",
            "EXPLICIT_RELATION_OF_PASSAGE_TO_THE_CLAIM",
            "NEGATIVE_RESULT_IF_NO_SOURCE_EXISTS",
        ),
        reason_codes=tuple(sorted(reasons)),
        carries_negative_evidence=tuple(negatives),
        prior_request_ids=tuple(prior),
        prior_request_ids_complete=bool(queue),
        indago_hunt="INDAGO_BOUNDED_HUNT_REQUIRED",
        indago_provenance=(
            "TRM_CITE_R2_R6_R3_REENTRY",
            "PRESERVES_" + str(len(negatives)) + "_PRIOR_NEGATIVE_FINDINGS",
            "REUSES_EXISTING_SOURCE_STORE_NO_DUPLICATE_STORE",
        ),
        supersedes_prior_requests=False,
        execution_status="QUEUED_NOT_EXECUTED",
        acquisition_authorized_by_this_object=False,
    )


# --------------------------------------------------------------------------
# R4
# --------------------------------------------------------------------------

_CANDIDATE_NOTES = {
    "BIBLIOGRAPHY_DETAIL_REPAIR": (
        "Repairs the recorded bibliographic detail only; the argument the "
        "source supports is unchanged and still unreviewed.",
        (),
    ),
    "CHANGE_SOURCE": (
        "Requires a different source that is not on record; this module "
        "cannot search, fetch or nominate a replacement.",
        ("REQUIRES_A_NEW_SOURCE_THAT_IS_NOT_ON_RECORD",),
    ),
    "PRESENT_NORMATIVE_AUTHOR_CONCLUSION_EXPLICITLY": (
        "States the normative conclusion as the author's own and decouples it "
        "from the cited source, which does not establish the stronger "
        "practice-transfer norm.",
        ("MACHINE_CANNOT_ESTABLISH_THAT_THE_SOURCE_ENTAILS_THE_CLAIM",
         "AUTHOR_MUST_ACCEPT_OWING_THE_NORMATIVE_CLAIM_TO_THEMSELVES"),
    ),
    "WEAKEN_OR_SPLIT_THESIS": (
        "Narrows the claim to what the source establishes; the scope choice "
        "belongs to the author.",
        ("SCOPE_REDUCTION_IS_AN_AUTHORIAL_JUDGEMENT",),
    ),
    "REMOVE_UNSUPPORTED_CITATION": (
        "Deletes the citation linkage while keeping the claim, leaving the "
        "claim unsupported rather than silently re-attributed.",
        ("REMOVAL_DOES_NOT_RESOLVE_THE_UNSUPPORTED_CLAIM",),
    ),
    "ABSTAIN_NO_CHANGE": (
        "No change. The scientific debt stays visible and unresolved.",
        ("NO_CHANGE_THE_DEBT_REMAINS_OPEN",),
    ),
}


def build_candidates(intent: IntentReconstruction,
                     states: list[dict[str, Any]]) -> list[RepairCandidate]:
    """R4: several distinct repairs with differing intellectual cost.

    No repair is offered unless the evidence on record supports offering it.
    Deleting a citation asserts a defect, so it needs actual evidence that the
    source does not carry the claim; zero evidence yields ABSTAIN only.
    """
    has_observed = any(s.get("outcome") == "OBSERVED" for s in states)
    has_anchored = any(_observed_anchored(s) for s in states)
    # Failed access (BLOCKED/ERROR) is epistemically unknown, not negative
    # evidence; a mere OBSERVED transport is not a scientific mismatch.
    # R1 must explicitly identify a readable witness and judge the specific
    # claim to be unsupported before any machine deletion is proposed.
    consulted_mismatch = any(
        s.get("outcome") in ("NEGATIVE", "OBSERVED")
        and s.get("source_to_claim_relation") == "DOES_NOT_SUPPORT_CLAIM"
        and bool(s.get("negative_evidence"))
        and any(
            w.get("read_depth") in {"SECTION_TEXT", "ANCHORED_PASSAGE", "FULL_TEXT"}
            and bool(w.get("witness_id"))
            for w in _witness_descriptors(s)
        )
        for s in states)
    # An anchored passage on record still VETOS machine deletion.
    defect_evidenced = (not has_anchored) and consulted_mismatch
    labels = sorted({evidence_label(s) for s in states}) or ["NO_SOURCE_EVIDENCE"]

    candidates: list[RepairCandidate] = []
    for rank, kind in enumerate(REPAIR_REPERTOIRE, start=1):
        cost, relation = REPAIR_REPERTOIRE[kind]
        source_note, extra = _CANDIDATE_NOTES[kind]
        debts = {
            "SOURCE_TO_CLAIM_RELATION_NOT_INDEPENDENTLY_REVIEWED",
            "VENUE_STYLE_PROFILE_NOT_SUPPLIED",
        }
        refusals: list[str] = []
        applicable = True
        if kind == "BIBLIOGRAPHY_DETAIL_REPAIR" and not has_observed:
            applicable = False
            refusals.append("NO_OBSERVED_SOURCE_IDENTITY_TO_CORRECT")
        if kind == "REMOVE_UNSUPPORTED_CITATION" and not defect_evidenced:
            applicable = False
            refusals.append("NO_EVIDENCE_ON_RECORD_THAT_THE_SOURCE_LACKS_SUPPORT")
        if not applicable:
            debts.add("CANDIDATE_NOT_APPLICABLE_TO_CURRENT_EVIDENCE")
        else:
            debts.update(extra)
        candidates.append(RepairCandidate(
            candidate_id=_id("r4", intent.intent_id, kind),
            intent_id=intent.intent_id,
            kind=kind,
            rank=rank,
            intellectual_cost=cost,
            source_to_claim_relation=relation,
            source_explanation=source_note,
            debt_explanation=(
                "Candidate is a proposal with author_gate PENDING; neither "
                "transport nor a correct DOI establishes V1-V5."),
            scientific_debt=tuple(sorted(debts)),
            evidence_label="|".join(labels),
            applicable=applicable,
            refusal_codes=tuple(refusals),
            text_source=("MACHINE_STRUCTURAL" if kind in MACHINE_RENDERABLE
                         else "AUTHOR_OR_ANALYST_WORDING_REQUIRED"),
            author_gate="PENDING",
            auto_approved=False,
            verification_certified=False,
        ))
    return candidates


# --------------------------------------------------------------------------
# R5
# --------------------------------------------------------------------------

def _operator_text(path: Path | None) -> dict[str, dict[str, Any]]:
    """Read author/analyst wording for R5. The machine never writes it.

    ``suggested_new_text`` is ``None`` when absent and ``""`` when the author
    explicitly asks for an empty replacement; the two are not the same.
    """
    if path is None:
        return {}
    data = _read_json(path)
    if data.get("schema") != CANDIDATE_TEXT_SCHEMA:
        raise RepairRefusal("Unknown candidate-text schema",
                            "UNKNOWN_CANDIDATE_TEXT_SCHEMA")
    entries = data.get("candidates")
    if not isinstance(entries, list) or not entries:
        raise RepairRefusal("Candidate text file has no candidates[]",
                            "EMPTY_CANDIDATE_TEXT")
    out: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("kind"):
            raise RepairRefusal("Candidate text entry is malformed",
                                "MALFORMED_CANDIDATE_TEXT")
        kind = str(entry["kind"])
        if kind in out:
            raise RepairRefusal("Duplicate candidate-text kind: " + kind,
                                "DUPLICATE_CANDIDATE_TEXT")
        if kind not in REPAIR_REPERTOIRE:
            raise RepairRefusal("Unknown candidate kind: " + kind,
                                "UNKNOWN_CANDIDATE_TEXT_KIND")
        new = entry.get("suggested_new_text")
        old = entry.get("old_text")
        if new is not None and not isinstance(new, str):
            raise RepairRefusal("suggested_new_text must be a string",
                                "MALFORMED_CANDIDATE_TEXT")
        if old is not None and not isinstance(old, str):
            raise RepairRefusal("old_text must be a string",
                                "MALFORMED_CANDIDATE_TEXT")
        out[kind] = {"suggested_new_text": new, "old_text": old or ""}
    return out


def _blocked_proposal(intent: IntentReconstruction, intake: dict[str, Any],
                      candidate: RepairCandidate, source_sha: str,
                      applicability: str, debts: tuple[str, ...],
                      old_text: str = "") -> ProposalPatch:
    return ProposalPatch(
        schema=PROPOSAL_SCHEMA,
        patch_id=_id("r5", intent.intent_id, candidate.candidate_id),
        candidate_id=candidate.candidate_id,
        intent_id=intent.intent_id,
        case_id=intent.case_id,
        target_manuscript_sha256=source_sha,
        target_surface=intake["surface"],
        target_locator=intake["anchor"]["locator"],
        anchor=_owned(intake["anchor"]),
        original_fragment=intake["original_fragment"],
        original_fragment_sha256=_text_digest(intake["original_fragment"]),
        old_text=old_text,
        original_text_sha256=_text_digest(old_text),
        suggested_new_text="",
        new_text_sha256=_text_digest(""),
        patched_manuscript_sha256=source_sha,
        diff="",
        diff_sha256=_text_digest(""),
        inverse_diff="",
        inverse_diff_sha256=_text_digest(""),
        applicability=applicability,
        debts=debts,
        text_source=candidate.text_source,
        author_gate="PENDING",
        manuscript_mutated=False,
        applied=False,
    )


def build_proposal(intent: IntentReconstruction, intake: dict[str, Any],
                   candidate: RepairCandidate, old_text: str,
                   new_text: str | None, text: str, source_sha: str,
                   source_name: str, has_bom: bool) -> ProposalPatch:
    """R5: one reversible, PENDING whole-file patch proposal. Writes nothing."""
    is_markdown = source_name.lower().endswith(".md")
    fragment = intake["original_fragment"]
    if candidate.kind == "ABSTAIN_NO_CHANGE":
        return _blocked_proposal(
            intent, intake, candidate, source_sha, "NO_CHANGE_PROPOSED",
            ("ABSTAIN_CARRIES_NO_PATCH",))
    if new_text is None:
        return _blocked_proposal(
            intent, intake, candidate, source_sha,
            "BLOCKED_NO_SUGGESTED_TEXT",
            ("SUGGESTED_TEXT_MUST_COME_FROM_THE_AUTHOR_OR_ANALYST",),
            old_text)
    start, end = resolve_patch_span(text, intent.anchor, old_text,
                                    fragment, is_markdown)
    patched = text[:start] + new_text + text[end:]
    if patched == text:
        return _blocked_proposal(
            intent, intake, candidate, source_sha,
            "BLOCKED_NO_OP_PROPOSAL",
            ("PROPOSED_TEXT_IS_IDENTICAL_TO_THE_ANCHOR",), old_text)
    raw = _encode(patched, has_bom)
    forward = _file_diff(text, patched, source_name)
    inverse = _file_diff(patched, text, source_name)
    return ProposalPatch(
        schema=PROPOSAL_SCHEMA,
        patch_id=_id("r5", intent.intent_id, candidate.candidate_id),
        candidate_id=candidate.candidate_id,
        intent_id=intent.intent_id,
        case_id=intent.case_id,
        target_manuscript_sha256=source_sha,
        target_surface=intake["surface"],
        target_locator=intake["anchor"]["locator"],
        anchor=_owned(intake["anchor"]),
        original_fragment=fragment,
        original_fragment_sha256=_text_digest(fragment),
        old_text=old_text,
        original_text_sha256=_text_digest(old_text),
        suggested_new_text=new_text,
        new_text_sha256=_text_digest(new_text),
        patched_manuscript_sha256=_digest(raw),
        diff=forward,
        diff_sha256=_text_digest(forward),
        inverse_diff=inverse,
        inverse_diff_sha256=_text_digest(inverse),
        applicability="READY_FOR_AUTHOR_REVIEW",
        debts=("AUTHOR_REVIEW_REQUIRED_BEFORE_ANY_APPLY",),
        text_source=candidate.text_source,
        author_gate="PENDING",
        manuscript_mutated=False,
        applied=False,
    )


def plan_repair(audit_path: Path, output_dir: Path, case_id: str,
                manuscript_path: Path,
                prior_states: list[dict[str, Any]] | None = None,
                queue_orders: list[dict[str, Any]] | None = None,
                candidate_text_path: Path | None = None,
                operator_note: str | None = None,
                expected_sha: str | None = None) -> dict[str, Any]:
    """R2 -> R3 -> R4 -> R5 in one read-only pass. Never writes a manuscript."""
    audit_path = Path(audit_path)
    audit = _read_json(audit_path)
    if audit.get("schema_version") != Z0_VERSION:
        raise RepairRefusal("Unknown Z0 audit schema version",
                            "UNKNOWN_Z0_SCHEMA")
    source_sha = audit["source"]["sha256"]
    if expected_sha and source_sha.lower() != expected_sha.lower():
        raise RepairRefusal("Original manuscript SHA mismatch",
                            "MANUSCRIPT_SHA_MISMATCH")
    _safe_component(case_id)

    manuscript_path = Path(manuscript_path).resolve()
    if manuscript_path.suffix.lower() not in READABLE_WRITABLE_SUFFIXES:
        raise RepairRefusal(
            "R5 anchor surfaces are implemented only for UTF-8 .md/.txt line "
            "sections; DOCX/PDF/JSON need a native editor service: BLOCKED",
            "UNSUPPORTED_SURFACE_BLOCKED")
    raw = manuscript_path.read_bytes()
    if _digest(raw) != source_sha:
        raise RepairRefusal(
            "Original manuscript SHA mismatch: the file on disk is not the "
            "audited original", "MANUSCRIPT_SHA_MISMATCH")

    states = prior_states or []
    queue = queue_orders or []
    linked, unlinked = link_prior_states(audit, queue, states)
    intent = reconstruct_intent(audit, case_id, linked, operator_note)
    reentry = plan_reentry(intent, linked, queue)
    intake = next(i for i in audit["intakes"]
                  if i["intake_id"] == intent.intake_id)
    candidates = build_candidates(intent, linked)
    operator = _operator_text(candidate_text_path)
    text, has_bom = _decode(raw)

    proposals: list[ProposalPatch] = []
    for candidate in candidates:
        if not candidate.applicable:
            proposals.append(_blocked_proposal(
                intent, intake, candidate, source_sha,
                "NOT_APPLICABLE_" + (candidate.refusal_codes[0]
                                     if candidate.refusal_codes else "UNKNOWN"),
                tuple(sorted(candidate.scientific_debt))))
            continue
        supplied = operator.get(candidate.kind, {})
        old_text = supplied.get("old_text") or intake["original_fragment"]
        new_text = supplied.get("suggested_new_text")
        if new_text is None and candidate.kind in MACHINE_RENDERABLE:
            # Structural deletion of the verified fragment only. No prose.
            new_text = old_text.replace(intake["original_fragment"], "", 1)
        try:
            proposal = build_proposal(
                intent, intake, candidate, old_text, new_text, text,
                source_sha, manuscript_path.name, has_bom)
        except RepairRefusal as exc:
            proposal = _blocked_proposal(
                intent, intake, candidate, source_sha,
                "BLOCKED_" + exc.code, (str(exc),), old_text)
        proposals.append(proposal)

    bundle = {
        "schema": PLAN_SCHEMA,
        "repair_version": VERSION,
        "r2_schema": INTENT_SCHEMA,
        "r3_schema": REENTRY_SCHEMA,
        "r4_schema": CANDIDATES_SCHEMA,
        "r5_schema": PROPOSAL_SCHEMA,
        "generated_from": {
            "z0_audit_sha256": _digest(audit_path.read_bytes()),
            "z0_version": Z0_VERSION,
            "source_sha256": source_sha,
            "case_id": case_id,
        },
        "r2_intent": intent.to_dict(),
        "r3_reentry": reentry.to_dict() if reentry else None,
        "r4_candidates": [c.to_dict() for c in candidates],
        "r5_proposals": [p.to_dict() for p in proposals],
        "prior_evidence": {
            "linked_state_count": len(linked),
            "unlinked_states_preserved": [s.get("_path") for s in unlinked],
        },
        "verification": dict(NOT_CHECKED),
        "citation_gate": "NOT_PUBLICATION_READY",
        "author_gate": "PENDING",
        "manuscript_mutated": False,
        "applied_to_copy": False,
        "external_search_authorized_by_this_object": False,
        "source_certification": "NONE_TRANSPORT_IS_NOT_CERTIFICATION",
        "work_edition_witness_provenance": {
            "preserved_fields": ("work_id", "edition_id", "witness_id",
                                 "passage_id"),
            "carried_from_prior_states": [
                {
                    "state_path": state.get("_path"),
                    "task_id": state.get("task_id"),
                    "outcome": state.get("outcome"),
                    "identity": {key: value for key, value
                                 in (_witness_descriptors(state)[0]
                                     if _witness_descriptors(state) else {}).items()
                                 if key in ("work_id", "edition_id",
                                            "witness_id", "passage_id")},
                    "witnesses": [
                        {key: value for key, value in witness.items()
                         if key in ("work_id", "edition_id", "witness_id",
                                    "passage_id", "read_depth",
                                    "source_provenance", "ingest_sha256",
                                    "locator")}
                        for witness in _witness_descriptors(state)
                    ],
                }
                for state in linked
            ],
            "operator_declarations_not_independently_proved": True,
        },
    }
    folder = (Path(output_dir).resolve() / "runs" /
              (VERSION + "_" + source_sha[:20]))
    _write_json_immutable(folder / ("plan_" + case_id + ".json"), bundle)
    return bundle


# --------------------------------------------------------------------------
# Decision receipt: author-owned. This module validates; it never mints.
# --------------------------------------------------------------------------

# Every field that decides whether or not a receipt may authorize a write is
# folded into the receipt identity, so editing any of them invalidates the id
# rather than silently re-pointing an existing approval.
_RECEIPT_IDENTITY_FIELDS = (
    "original_manuscript_sha256", "claim_id", "candidate_id", "diff_sha256",
    "original_text_sha256", "new_text_sha256", "decision", "issued_by",
    "issuer_role", "witness_class",
)


def receipt_identity(receipt: dict[str, Any]) -> str:
    """Deterministic id over the whole bound content of a decision receipt."""
    parts = [str(receipt.get(field, "")) for field in _RECEIPT_IDENTITY_FIELDS]
    parts.append(_text_digest(str(receipt.get("user_input", ""))))
    parts.append(_text_digest(json.dumps(bool(receipt.get("synthetic")))))
    return _id("dr", *parts)


def receipt_mac(receipt: dict[str, Any], author_key: bytes) -> str:
    """HMAC-SHA256 over the receipt identity, keyed by the author.

    An author who holds ``author_key`` can compute this; a peer process that
    can only read the repository cannot. It is optional, because this module
    does not manage keys, but it is the only cryptographic provenance signal
    available on a shared machine.
    """
    if not isinstance(author_key, (bytes, bytearray)) or not author_key:
        raise RepairRefusal("Author key must be non-empty bytes",
                            "EMPTY_AUTHOR_KEY")
    return hmac.new(bytes(author_key),
                    receipt_identity(receipt).encode("utf-8"),
                    hashlib.sha256).hexdigest()


def _required(record: dict[str, Any], field: str, owner: str) -> Any:
    if field not in record:
        raise RepairRefusal(f"{owner} is missing required field: {field}",
                            "MISSING_REQUIRED_FIELD")
    return record[field]


# Every field an apply/readback step reads off a proposal. Validated up front so
# a malformed or forged proposal yields a typed refusal, never a raw KeyError
# escaping the fail-closed contract.
_PROPOSAL_REQUIRED_FIELDS = (
    "patch_id", "candidate_id", "intent_id", "case_id",
    "target_manuscript_sha256", "target_surface", "target_locator", "anchor",
    "original_fragment", "original_fragment_sha256", "old_text",
    "original_text_sha256", "suggested_new_text", "new_text_sha256",
    "patched_manuscript_sha256", "diff", "diff_sha256", "inverse_diff",
    "inverse_diff_sha256", "applicability", "author_gate", "applied",
)


def _validate_proposal_shape(proposal: dict[str, Any]) -> None:
    missing = [field for field in _PROPOSAL_REQUIRED_FIELDS
               if field not in proposal]
    if missing:
        raise RepairRefusal(
            "Proposal is missing required fields: " + ", ".join(missing),
            "MISSING_REQUIRED_FIELD")
    if not isinstance(proposal.get("anchor"), dict):
        raise RepairRefusal("Proposal anchor is not an object",
                            "MALFORMED_PROPOSAL")


def validate_decision_receipt(receipt: dict[str, Any], proposal: dict[str, Any],
                              allow_synthetic_test: bool,
                              author_key: bytes | None = None) -> None:
    """Bind an author receipt to one exact patch, or refuse.

    When ``author_key`` is supplied the receipt must also carry a valid keyed
    ``receipt_mac``; without a key this function checks binding and structure
    only, and provenance remains an operator responsibility.
    """
    if receipt.get("schema") != RECEIPT_SCHEMA:
        raise RepairRefusal("Unknown decision receipt schema",
                            "UNKNOWN_RECEIPT_SCHEMA")
    if author_key is not None:
        expected_mac = receipt_mac(receipt, author_key)
        if not hmac.compare_digest(str(receipt.get("receipt_mac", "")),
                                   expected_mac):
            raise RepairRefusal(
                "Decision receipt is not keyed by the author's secret",
                "RECEIPT_MAC_MISMATCH")
    if str(receipt.get("issued_by", "")).upper() != "AUTHOR":
        raise RepairRefusal(
            "Author approval must be issued by a human AUTHOR; an assistant "
            "cannot self-issue an approval", "NON_HUMAN_ISSUER")
    if str(receipt.get("issuer_role", "")).upper() in NON_HUMAN_ISSUERS:
        raise RepairRefusal("Non-human issuer role cannot approve a patch",
                            "NON_HUMAN_ISSUER")
    if receipt.get("witness_class") not in ALLOWED_WITNESS_CLASSES:
        raise RepairRefusal(
            "Unknown decision witness class: "
            + str(receipt.get("witness_class")), "UNKNOWN_WITNESS_CLASS")
    synthetic = (receipt.get("synthetic") is True
                 or receipt.get("witness_class") == "SYNTHETIC_TEST")
    if synthetic and not allow_synthetic_test:
        raise RepairRefusal(
            "Synthetic test receipt cannot authorize a real apply; it is "
            "accepted only through the Python API with "
            "allow_synthetic_test=True", "SYNTHETIC_RECEIPT_OUTSIDE_SANDBOX")
    if receipt.get("decision") not in DECISIONS:
        raise RepairRefusal("Unknown decision: " + str(receipt.get("decision")),
                            "UNKNOWN_DECISION")
    if not str(receipt.get("user_input", "")).strip():
        raise RepairRefusal("Decision receipt carries no verbatim user input",
                            "EMPTY_USER_INPUT")
    if str(receipt.get("receipt_id", "")) != receipt_identity(receipt):
        raise RepairRefusal(
            "Decision receipt id does not match its own content",
            "RECEIPT_ID_MISMATCH")
    bindings = (
        ("original_manuscript_sha256",
         _required(proposal, "target_manuscript_sha256", "Proposal")),
        ("claim_id", _required(proposal, "case_id", "Proposal")),
        ("candidate_id", _required(proposal, "candidate_id", "Proposal")),
        ("diff_sha256", _required(proposal, "diff_sha256", "Proposal")),
        ("original_text_sha256",
         _required(proposal, "original_text_sha256", "Proposal")),
        ("new_text_sha256", _required(proposal, "new_text_sha256", "Proposal")),
    )
    for field, expected in bindings:
        if receipt.get(field) != expected:
            raise RepairRefusal(
                "Decision receipt is not bound to this patch: " + field,
                "RECEIPT_NOT_BOUND")
    if proposal.get("author_gate") != "PENDING" or proposal.get("applied"):
        raise RepairRefusal("Proposal is not in an applicable PENDING state",
                            "PROPOSAL_NOT_PENDING")
    if proposal.get("applicability") != "READY_FOR_AUTHOR_REVIEW":
        raise RepairRefusal("Proposal is not reviewable: "
                            + str(proposal.get("applicability")),
                            "PROPOSAL_NOT_REVIEWABLE")
    if receipt["decision"] != "APPROVE":
        raise RepairRefusal("Decision is not APPROVE; nothing is applied: "
                            + str(receipt["decision"]), "DECISION_NOT_APPROVE")


def _check_proposal_self_consistency(proposal: dict[str, Any]) -> None:
    """A proposal must be internally consistent before anything is trusted."""
    if _id("r5", str(proposal.get("intent_id", "")),
           str(proposal.get("candidate_id", ""))) != proposal.get("patch_id"):
        raise RepairRefusal(
            "Proposal id does not match its own intent and candidate",
            "PROPOSAL_ID_MISMATCH")
    for field, value in (
        ("old_text", proposal.get("old_text")),
        ("original_fragment", proposal.get("original_fragment")),
        ("suggested_new_text", proposal.get("suggested_new_text")),
    ):
        if not isinstance(value, str):
            raise RepairRefusal("Proposal field is not a string: " + field,
                                "MALFORMED_PROPOSAL")
    if _text_digest(str(proposal["old_text"])) != \
            proposal.get("original_text_sha256"):
        raise RepairRefusal("Original text SHA does not match the proposal",
                            "OLD_TEXT_SHA_MISMATCH")
    if _text_digest(str(proposal["original_fragment"])) != \
            proposal.get("original_fragment_sha256"):
        raise RepairRefusal("Original fragment SHA does not match the proposal",
                            "FRAGMENT_SHA_MISMATCH")
    if _text_digest(str(_required(proposal, "suggested_new_text",
                                "Proposal"))) \
            != proposal.get("new_text_sha256"):
        raise RepairRefusal("Suggested new text SHA does not match the proposal",
                            "NEW_TEXT_SHA_MISMATCH")
    if _text_digest(str(_required(proposal, "diff", "Proposal"))) != \
            proposal.get("diff_sha256"):
        raise RepairRefusal("Proposal diff SHA does not match its own diff",
                            "DIFF_SHA_MISMATCH")
    if _text_digest(str(_required(proposal, "inverse_diff", "Proposal"))) != \
            proposal.get("inverse_diff_sha256"):
        raise RepairRefusal(
            "Proposal inverse diff SHA does not match its own inverse diff",
            "INVERSE_DIFF_SHA_MISMATCH")


def apply_patch(manuscript_path: Path, proposal: dict[str, Any],
                receipt: dict[str, Any], copy_path: Path,
                allow_synthetic_test: bool = False,
                author_key: bytes | None = None) -> dict[str, Any]:
    """R5 apply: patch a *fresh copy* atomically and emit the inverse patch.

    The original manuscript is opened read-only and can never be the
    destination. The author's approval covers the exact bytes that are written:
    the diff is recomputed from the manuscript here and must equal the diff the
    author signed, so an approval cannot be replayed against different text.
    """
    if proposal.get("schema") != PROPOSAL_SCHEMA:
        raise RepairRefusal("Unknown R5 proposal schema", "UNKNOWN_PROPOSAL_SCHEMA")
    _validate_proposal_shape(proposal)
    manuscript_path = Path(manuscript_path).resolve()
    copy_path = Path(copy_path).resolve()
    if copy_path == manuscript_path:
        raise RepairRefusal(
            "Refusing to apply a patch onto the original manuscript",
            "TARGET_IS_ORIGINAL")
    if manuscript_path.suffix.lower() not in READABLE_WRITABLE_SUFFIXES:
        raise RepairRefusal(
            "Patch application is implemented only for UTF-8 .md/.txt line "
            "sections: BLOCKED", "UNSUPPORTED_SURFACE_BLOCKED")
    raw = manuscript_path.read_bytes()
    original_sha = _digest(raw)
    if original_sha != proposal["target_manuscript_sha256"]:
        raise RepairRefusal("Original manuscript SHA mismatch",
                            "MANUSCRIPT_SHA_MISMATCH")
    _check_proposal_self_consistency(proposal)
    validate_decision_receipt(receipt, proposal, allow_synthetic_test,
                              author_key)

    text, has_bom = _decode(raw)
    is_markdown = manuscript_path.suffix.lower() == ".md"
    start, end = resolve_patch_span(
        text, _required(proposal, "anchor", "Proposal"),
        proposal["old_text"], proposal["original_fragment"], is_markdown)
    patched = text[:start] + proposal["suggested_new_text"] + text[end:]
    out = _encode(patched, has_bom)

    # The signed diff must be exactly what this manuscript produces.
    forward = _file_diff(text, patched, manuscript_path.name)
    if forward != proposal["diff"]:
        raise RepairRefusal(
            "Recomputed diff does not match the diff the author approved",
            "DIFF_RECOMPUTATION_MISMATCH")
    inverse = _file_diff(patched, text, manuscript_path.name)
    if inverse != proposal["inverse_diff"]:
        raise RepairRefusal(
            "Recomputed inverse diff does not match the recorded inverse diff",
            "INVERSE_DIFF_RECOMPUTATION_MISMATCH")
    if _digest(out) != proposal["patched_manuscript_sha256"]:
        raise RepairRefusal(
            "Recomputed patched SHA does not match the proposal: refusing to "
            "apply an unreproducible patch", "PATCHED_SHA_MISMATCH")

    # Confirm the original is still untouched before anything is written.
    if manuscript_path.read_bytes() != raw:
        raise RepairRefusal(
            "Original manuscript changed while the patch was being prepared",
            "ORIGINAL_DRIFTED")
    _atomic_write_bytes(copy_path, out)
    if manuscript_path.read_bytes() != raw:
        raise RepairRefusal("Original manuscript bytes changed during apply",
                            "ORIGINAL_DRIFTED")

    return {
        "schema": APPLY_SCHEMA,
        "patch_id": proposal["patch_id"],
        "candidate_id": proposal["candidate_id"],
        "case_id": proposal["case_id"],
        "decision_receipt_id": str(receipt["receipt_id"]),
        "decision_receipt_sha256": _digest(_bytes(receipt)),
        "original_manuscript_sha256": original_sha,
        "original_manuscript_path": str(manuscript_path),
        "applied_copy_path": str(copy_path),
        "applied_copy_sha256": _digest(out),
        "old_text_sha256": proposal["original_text_sha256"],
        "new_text_sha256": proposal["new_text_sha256"],
        "diff_sha256": proposal["diff_sha256"],
        "inverse_diff": proposal["inverse_diff"],
        "inverse_diff_sha256": proposal["inverse_diff_sha256"],
        "author_gate": "AUTHOR_APPROVED_THIS_PATCH_ONLY",
        "original_manuscript_mutated": False,
        "original_manuscript_reverified": True,
        "synthetic_test_receipt": (
            receipt.get("synthetic") is True
            or receipt.get("witness_class") == "SYNTHETIC_TEST"),
        "decision_witness_class": receipt.get("witness_class"),
        "verification": dict(NOT_CHECKED),
        "citation_gate": "NOT_PUBLICATION_READY",
    }


def undo_patch(copy_path: Path, apply_receipt: dict[str, Any],
               original_snapshot_path: Path, restored_path: Path) -> dict[str, Any]:
    """Restore the exact original bytes from the Z0 snapshot. Never guesses."""
    if apply_receipt.get("schema") != APPLY_SCHEMA:
        raise RepairRefusal("Unknown apply receipt schema",
                            "UNKNOWN_APPLY_RECEIPT")
    copy_path = Path(copy_path).resolve()
    restored_path = Path(restored_path).resolve()
    if restored_path == copy_path:
        raise RepairRefusal("Refusing to undo onto the patched copy itself",
                            "UNDO_TARGET_IS_COPY")
    applied = _digest(copy_path.read_bytes())
    if applied != apply_receipt.get("applied_copy_sha256"):
        raise RepairRefusal("Applied copy SHA mismatch: refusing to undo",
                            "APPLIED_COPY_SHA_MISMATCH")
    original_snapshot_path = Path(original_snapshot_path).resolve()
    if not original_snapshot_path.is_file():
        raise RepairRefusal(
            "Original snapshot is not readable: " + str(original_snapshot_path),
            "SNAPSHOT_MISSING")
    original = original_snapshot_path.read_bytes()
    expected = _required(apply_receipt, "original_manuscript_sha256",
                        "Apply receipt")
    if _digest(original) != expected:
        raise RepairRefusal("Original snapshot SHA mismatch: refusing to undo",
                            "SNAPSHOT_SHA_MISMATCH")
    _atomic_write_bytes(restored_path, original)
    if _digest(restored_path.read_bytes()) != expected:
        raise RepairRefusal("Undo did not restore the exact original bytes",
                            "UNDO_BYTES_MISMATCH")
    return {
        "schema": UNDO_SCHEMA,
        "patch_id": apply_receipt["patch_id"],
        "restored_from_snapshot": str(original_snapshot_path),
        "restored_path": str(restored_path),
        "restored_sha256": expected,
        "original_sha256_preserved": True,
        "exact_source_bytes_restored": True,
    }


# --------------------------------------------------------------------------
# R6
# --------------------------------------------------------------------------

def post_patch_check(copy_path: Path, proposal: dict[str, Any],
                     apply_receipt: dict[str, Any]) -> dict[str, Any]:
    """R6: re-intake the applied copy through Z0 and report retained debt.

    A clean transport read, a correct DOI or a cleanly applied patch never
    promotes V1-V5. Every key stays explicitly unverified so a downstream
    orchestrator cannot read this object as scientific success. The original
    manuscript is re-verified here, not merely asserted by the apply receipt.
    """
    if apply_receipt.get("schema") != APPLY_SCHEMA:
        raise RepairRefusal("R6 requires a real apply receipt",
                            "UNKNOWN_APPLY_RECEIPT")
    if proposal.get("schema") != PROPOSAL_SCHEMA:
        raise RepairRefusal("R6 requires a real R5 proposal",
                            "UNKNOWN_PROPOSAL_SCHEMA")
    _validate_proposal_shape(proposal)
    if apply_receipt.get("patch_id") != proposal.get("patch_id"):
        raise RepairRefusal(
            "R6 proposal and apply receipt describe different patches",
            "R6_PATCH_ID_MISMATCH")
    _check_proposal_self_consistency(proposal)

    copy_path = Path(copy_path).resolve()
    raw = copy_path.read_bytes()
    copy_sha = _digest(raw)
    if copy_sha != apply_receipt.get("applied_copy_sha256"):
        raise RepairRefusal("Applied copy SHA mismatch: refusing R6 readback",
                            "APPLIED_COPY_SHA_MISMATCH")
    original_sha = _required(apply_receipt, "original_manuscript_sha256",
                             "Apply receipt")
    if copy_sha == original_sha:
        raise RepairRefusal("R6 requires a changed copy; nothing was applied",
                            "NOTHING_WAS_APPLIED")

    # R6 must not be able to skip the original check by omitting the path.
    original_path = apply_receipt.get("original_manuscript_path")
    if not original_path:
        raise RepairRefusal(
            "R6 requires the apply receipt to record the original manuscript "
            "path so the original can be re-verified", "ORIGINAL_PATH_MISSING")
    try:
        original_bytes = Path(original_path).read_bytes()
    except OSError as exc:
        raise RepairRefusal(
            "The original manuscript is not readable during R6",
            "ORIGINAL_MISSING_AFTER_APPLY") from exc
    original_reverified = _digest(original_bytes) == original_sha
    if not original_reverified:
        raise RepairRefusal(
            "The original manuscript changed after apply; R6 cannot certify a "
            "patch applied to a moving target. Re-run from the current original "
            "or restore it from the Z0 snapshot before re-checking.",
            "ORIGINAL_DRIFTED_AFTER_APPLY")

    reread = audit_manuscript(copy_path)
    intake = next((i for i in reread.intakes
                   if i.surface == proposal["target_surface"]
                   and i.anchor["locator"] == proposal["target_locator"]),
                  None)
    verification = dict(NOT_CHECKED)
    check = PostPatchCheck(
        schema=CHECK_SCHEMA,
        check_id=_id("r6", proposal["patch_id"], copy_sha),
        case_id=proposal["case_id"],
        candidate_id=proposal["candidate_id"],
        patch_id=proposal["patch_id"],
        apply_receipt_sha256=_digest(_bytes(apply_receipt)),
        original_manuscript_sha256=original_sha,
        applied_copy_sha256=copy_sha,
        original_manuscript_reverified=original_reverified,
        reread_status="REREAD_VIA_Z0",
        reread_intake_id=intake.intake_id if intake else None,
        citation_present_after_patch=bool(intake),
        fragment_after_patch=intake.original_fragment if intake else None,
        verification=verification,
        journal_style="NOT_CHECKED_NO_VENUE_PROFILE",
        scientific_debts=(
            "SOURCE_SUPPORT_NOT_INDEPENDENTLY_VERIFIED",
            "AUTHORIAL_SCOPE_AND_NORMATIVE_JUDGEMENT_NOT_REVIEWED",
            "VENUE_STYLE_PROFILE_NOT_SUPPLIED",
            "DOCUMENT_EDITOR_SELECTION_AND_CLICKTEST_NOT_PERFORMED",
        ),
        citation_gate="NOT_PUBLICATION_READY",
        author_gate=str(apply_receipt.get("author_gate", "PENDING")),
        scientific_status="DEBT_RETAINED_NO_PUBLICATION_PASS",
        any_verification_passed=any(
            str(value).endswith("PASS") for value in verification.values()),
        z0_coverage_debts=tuple(sorted(set(reread.coverage["debts"]))),
    )
    payload = check.to_dict()
    payload["z0_reread_schema_version"] = reread.schema_version
    payload["synthetic_test_receipt"] = bool(
        apply_receipt.get("synthetic_test_receipt"))
    payload["decision_witness_class"] = apply_receipt.get(
        "decision_witness_class", "UNKNOWN")
    return payload


# --------------------------------------------------------------------------
# CLI: plan is the default and never writes a manuscript.
#
# There is deliberately no command-line switch for synthetic approvals: the
# sandbox is a Python-level keyword only, so no shell user can widen it.
# --------------------------------------------------------------------------

def _add_plan_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--audit", type=Path, required=True,
                        help="Z0 citation_intake.json")
    parser.add_argument("--case", required=True, help="Z0 case_id to repair")
    parser.add_argument("--manuscript", type=Path, required=True,
                        help="Local original manuscript, opened read-only")
    parser.add_argument("--out", type=Path, required=True,
                        help="Fresh private output directory")
    parser.add_argument("--expected-manuscript-sha256")
    parser.add_argument("--prior-state", type=Path, action="append", default=[],
                        help="Existing R1 case state file or directory "
                             "(repeatable); preserved, never rewritten")
    parser.add_argument("--queue", type=Path,
                        help="Z0 citation_work_orders.jsonl, for R3 linkage")
    parser.add_argument("--candidate-text", type=Path,
                        help="Author/analyst wording for the R5 proposals")
    parser.add_argument("--operator-note",
                        help="Optional analyst statement of the author's need")


def _run_plan(args: argparse.Namespace) -> dict[str, Any]:
    audit = _read_json(args.audit)
    return plan_repair(
        args.audit, args.out, args.case, args.manuscript,
        prior_states=load_prior_states(args.prior_state,
                                       audit["source"]["sha256"]),
        queue_orders=_read_jsonl(args.queue) if args.queue else None,
        candidate_text_path=args.candidate_text,
        operator_note=args.operator_note,
        expected_sha=args.expected_manuscript_sha256,
    )


def _run_apply(args: argparse.Namespace) -> dict[str, Any]:
    proposal = _read_json(args.proposal)
    receipt = _read_json(args.receipt)
    # No command line can open the synthetic sandbox.
    author_key = None
    if args.author_key_file:
        try:
            author_key = Path(args.author_key_file).read_bytes().strip()
        except OSError as exc:
            raise RepairRefusal(
                "Author key file is not readable: " + str(args.author_key_file),
                "AUTHOR_KEY_FILE_UNREADABLE") from exc
        if not author_key:
            raise RepairRefusal("Author key file is empty",
                                "EMPTY_AUTHOR_KEY")
    result = apply_patch(args.manuscript, proposal, receipt, args.copy,
                         allow_synthetic_test=False, author_key=author_key)
    _write_json_immutable(args.out / "apply_receipt.json", result)
    return result


def _run_check(args: argparse.Namespace) -> dict[str, Any]:
    proposal = _read_json(args.proposal)
    apply_receipt = _read_json(args.apply_receipt)
    result = post_patch_check(args.copy, proposal, apply_receipt)
    _write_json_immutable(args.out / "post_patch_check.json", result)
    return result


def _run_undo(args: argparse.Namespace) -> dict[str, Any]:
    apply_receipt = _read_json(args.apply_receipt)
    result = undo_patch(args.copy, apply_receipt, args.original_snapshot,
                        args.restored)
    _write_json_immutable(args.out / "undo_receipt.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="kairoskopion cite-repair",
        description="R2-R6 citation repair: plan only by default, never "
                    "certifies a citation, never writes the original "
                    "manuscript.")
    mode = parser.add_subparsers(dest="mode")

    plan_parser = mode.add_parser("plan", help="R2-R5 read-only plan")
    _add_plan_arguments(plan_parser)

    apply_parser = mode.add_parser("apply", help="R5 apply onto a fresh COPY")
    apply_parser.add_argument("--manuscript", type=Path, required=True)
    apply_parser.add_argument("--proposal", type=Path, required=True)
    apply_parser.add_argument("--receipt", type=Path, required=True,
                              help="Author-issued DecisionReceipt")
    apply_parser.add_argument("--copy", type=Path, required=True,
                              help="Fresh destination that must not exist")
    apply_parser.add_argument("--out", type=Path, required=True)
    apply_parser.add_argument(
        "--author-key-file", type=Path,
        help="File holding the author's secret, used to verify receipt_mac. "
             "Omit only when trusting the receipt's provenance operationally.")

    check_parser = mode.add_parser("check", help="R6 readback of an applied copy")
    check_parser.add_argument("--proposal", type=Path, required=True)
    check_parser.add_argument("--apply-receipt", type=Path, required=True)
    check_parser.add_argument("--copy", type=Path, required=True)
    check_parser.add_argument("--out", type=Path, required=True)

    undo_parser = mode.add_parser("undo", help="Restore exact original bytes")
    undo_parser.add_argument("--apply-receipt", type=Path, required=True)
    undo_parser.add_argument("--copy", type=Path, required=True)
    undo_parser.add_argument("--original-snapshot", type=Path, required=True)
    undo_parser.add_argument("--restored", type=Path, required=True)
    undo_parser.add_argument("--out", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.mode is None:
        parser.print_help()
        return 0
    try:
        handler = {"plan": _run_plan, "apply": _run_apply,
                   "check": _run_check, "undo": _run_undo}[args.mode]
        result = handler(args)
    except (RepairRefusal, OSError, ValueError, RuntimeError) as exc:
        print(f"cite-repair {args.mode} refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 3 if args.mode == "check" else 0


if __name__ == "__main__":
    raise SystemExit(main())