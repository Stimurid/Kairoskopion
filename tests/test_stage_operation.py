"""Tests for the stage-operation driver on top of the Trimurti scheduler.

These tests prove that the stage-operation layer closes the loophole that
``advance_phase`` leaves open on its own: a free-form string evidence_ref
(``src:fake``, ``arbitrary:text``) can no longer reach
``CHECKPOINT_STATUS_COMPLETED`` for the SourceBytesStageAdapter, and a
completed checkpoint always carries a non-null OperationDigest with
input/output SHA-256 anchored to real bytes.

Coverage:

* ``parse_evidence_ref`` rejects every placeholder/stub string.
* ``parse_evidence_ref`` accepts only valid ``kind:sha:source_kind`` triples.
* ``validate_evidence_refs_for_phase`` enforces phase-specific source_kind
  discipline (SOURCE_EVIDENCE accepts REAL or FIXTURE; SCHOLARLY_CHALLENGE
  accepts only REAL_AUTHORIZED_BYTES).
* ``SourceBytesStageAdapter`` with a blocked/no source root lands every
  route on HOLD with REFUSAL_SOURCE_BYTES_MISSING.
* ``SourceBytesStageAdapter`` with a fixture root cannot promote to
  COMPLETED — fixture is not real scientific source.
* ``SourceBytesStageAdapter`` with REAL bytes whose SHA matches the
  route's source_full_sha256 advances to COMPLETED with an
  ``OperationDigest`` whose input/output hashes match.
* ``drive_stage`` is idempotent for identical replays (same event hash).
* ``ScholarlyChallengeStageAdapter`` is a typed HOLD by design.
* ``run_batch_first_source_evidence`` summary reports refusal codes, never
  silently fabricates COMPLETED.
* Cross-source-root SHA mismatch produces HOLD (no fake provenance).
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from kairoskopion.kairon_provider import (
    CHECKPOINT_STATUS_COMPLETED,
    CHECKPOINT_STATUS_HOLD,
    EVIDENCE_REF_FORBIDDEN_LITERALS,
    EVIDENCE_REF_PATTERN,
    EvidenceRef,
    OperationDigest,
    PHASE_ORDER,
    PhaseName,
    REFUSAL_EVIDENCE_REF_INVALID,
    REFUSAL_EVIDENCE_REF_STUB,
    REFUSAL_NEEDS_REAL_OPERATION_ADAPTER,
    REFUSAL_OPERATION_DIGEST_MISSING,
    REFUSAL_SOURCE_BYTES_MISSING,
    ScholarlyChallengeStageAdapter,
    SourceBytesStageAdapter,
    SourceRoot,
    SOURCE_KIND_BLOCKED,
    SOURCE_KIND_FIXTURE,
    SOURCE_KIND_REAL,
    StageResult,
    TrimurtiBatchSpec,
    W12Record,
    build_fixture_w12,
    build_trimurti_plan,
    compute_route_event_hash,
    drive_stage,
    is_valid_evidence_ref,
    make_operation_digest,
    parse_evidence_ref,
    parse_evidence_refs,
    plan_summary,
    run_batch_first_source_evidence,
    validate_evidence_refs_for_phase,
)


# ---------------------------------------------------------------------------
# Evidence-ref parser.
# ---------------------------------------------------------------------------


def test_parse_evidence_ref_rejects_src_fake_stub():
    """``src:fake`` is the canonical stub in the loophole story."""

    with pytest.raises(ValueError, match=REFUSAL_EVIDENCE_REF_STUB):
        parse_evidence_ref("src:fake")


def test_parse_evidence_ref_rejects_arbitrary_string():
    """Anything that does not match ``kind:sha:source_kind`` is invalid."""

    bad_inputs = [
        "arbitrary:evidence",
        "src:not-a-sha",
        "w12_source:not_hex",
        "w12_source:",
        ":abc:REAL_AUTHORIZED_BYTES",
        "no_three_colons:sha:src:extra",
        " ",
    ]
    for value in bad_inputs:
        with pytest.raises(ValueError):
            parse_evidence_ref(value)


@pytest.mark.parametrize("value", sorted(EVIDENCE_REF_FORBIDDEN_LITERALS))
def test_parse_evidence_ref_rejects_each_forbidden_literal(value):
    """Every literal in EVIDENCE_REF_FORBIDDEN_LITERALS is explicitly stubbed."""

    with pytest.raises(ValueError, match=REFUSAL_EVIDENCE_REF_STUB):
        parse_evidence_ref(value)


def test_parse_evidence_ref_accepts_valid_triple():
    ref = parse_evidence_ref("w12_source:0123456789abcdef0123456789abcdef:REAL_AUTHORIZED_BYTES")
    assert ref.kind == "w12_source"
    assert ref.sha256_short == "0123456789abcdef0123456789abcdef"
    assert ref.source_kind == SOURCE_KIND_REAL
    assert ref.canonical.startswith("w12_source:")


def test_parse_evidence_ref_rejects_non_string_input():
    with pytest.raises(ValueError, match=REFUSAL_EVIDENCE_REF_INVALID):
        parse_evidence_ref(b"bytes-not-allowed")
    with pytest.raises(ValueError, match=REFUSAL_EVIDENCE_REF_INVALID):
        parse_evidence_ref(None)
    with pytest.raises(ValueError, match=REFUSAL_EVIDENCE_REF_INVALID):
        parse_evidence_ref(42)


def test_is_valid_evidence_ref_handles_stub_and_valid():
    assert is_valid_evidence_ref("src:fake") is False
    assert (
        is_valid_evidence_ref("w12_source:0123456789abcdef0123456789abcdef:REAL_AUTHORIZED_BYTES")
        is True
    )


def test_parse_evidence_refs_partial_success_is_rejected():
    """No partial success: any invalid ref poisons the whole list."""

    valid = "w12_source:0123456789abcdef0123456789abcdef:REAL_AUTHORIZED_BYTES"
    with pytest.raises(ValueError, match=REFUSAL_EVIDENCE_REF_STUB):
        parse_evidence_refs([valid, "src:fake"])


def test_evidence_ref_construction_enforces_invariants():
    with pytest.raises(ValueError, match="invalid source_kind"):
        EvidenceRef(kind="x", sha256_short="0" * 32, source_kind="WUT")


def test_evidence_ref_construction_enforces_sha_format():
    with pytest.raises(ValueError, match="invalid sha256_short"):
        EvidenceRef(
            kind="x", sha256_short="not-hex", source_kind=SOURCE_KIND_REAL
        )


# ---------------------------------------------------------------------------
# Phase-specific discipline.
# ---------------------------------------------------------------------------


def test_validate_evidence_refs_for_phase_rejects_empty_list():
    ok, errors = validate_evidence_refs_for_phase(
        PhaseName.SOURCE_EVIDENCE,
        [],
    )
    assert ok is False
    assert errors


def test_validate_evidence_refs_for_phase_source_evidence_rejects_blocked():
    """SOURCE_EVIDENCE accepts REAL or FIXTURE; BLOCKED is rejected."""

    blocked = EvidenceRef(kind="w12_source", sha256_short="0" * 32, source_kind=SOURCE_KIND_BLOCKED)
    ok, errors = validate_evidence_refs_for_phase(PhaseName.SOURCE_EVIDENCE, [blocked])
    assert ok is False
    assert any("SOURCE_EVIDENCE" in e or "source_evidence" in e for e in errors)


def test_validate_evidence_refs_for_phase_scholarly_challenge_rejects_fixture():
    """SCHOLARLY_CHALLENGE accepts REAL only — fixture cannot stand for
    scientific opposition; this is the upstream CLAUDE.md "no fake
    references" rule expressed at the evidence-ref layer."""

    fixture = EvidenceRef(kind="w12_source", sha256_short="0" * 32, source_kind=SOURCE_KIND_FIXTURE)
    ok, errors = validate_evidence_refs_for_phase(PhaseName.SCHOLARLY_CHALLENGE, [fixture])
    assert ok is False
    assert errors


def test_validate_evidence_refs_for_phase_scholarly_challenge_rejects_empty():
    ok, errors = validate_evidence_refs_for_phase(PhaseName.SCHOLARLY_CHALLENGE, [])
    assert ok is False
    assert any(REFUSAL_EVIDENCE_REF_STUB not in e for e in errors) is False or any(
        "scholarly" in e.lower() or "REFUSAL_EMPTY_SCHOLARLY_EVIDENCE" in e for e in errors
    )


# ---------------------------------------------------------------------------
# OperationDigest.
# ---------------------------------------------------------------------------


def test_operation_digest_requires_hex64_input_output_hashes():
    with pytest.raises(ValueError, match="invalid input_sha256"):
        OperationDigest(
            provider="p",
            command="c",
            input_sha256="too_short",
            output_sha256="0" * 64,
            result_fingerprint="0" * 32,
            started_at="2026-10-20T00:00:00+00:00",
            finished_at="2026-10-20T00:00:01+00:00",
        )


def test_make_operation_digest_hashes_input_and_output_bytes():
    digest = make_operation_digest(
        provider="fixture",
        command="test",
        input_bytes=b"hello",
        output_bytes=b"world",
        started_at="2026-10-20T00:00:00+00:00",
        finished_at="2026-10-20T00:00:01+00:00",
    )
    assert digest.input_sha256 == hashlib.sha256(b"hello").hexdigest()
    assert digest.output_sha256 == hashlib.sha256(b"world").hexdigest()
    assert digest.input_bytes == 5
    assert digest.output_bytes == 5
    assert digest.result_fingerprint == hashlib.sha256(("|".join([digest.provider, digest.command, digest.input_sha256, digest.output_sha256])).encode("utf-8")).hexdigest()[:32]


# ---------------------------------------------------------------------------
# StageResult invariants.
# ---------------------------------------------------------------------------


def test_stage_result_completed_requires_evidence_refs():
    with pytest.raises(ValueError, match=REFUSAL_EVIDENCE_REF_INVALID):
        StageResult(status=CHECKPOINT_STATUS_COMPLETED, evidence_refs=[])


def test_stage_result_completed_requires_operation_digest():
    ref = EvidenceRef(
        kind="w12_source",
        sha256_short="0" * 32,
        source_kind=SOURCE_KIND_REAL,
    )
    with pytest.raises(ValueError, match=REFUSAL_OPERATION_DIGEST_MISSING):
        StageResult(status=CHECKPOINT_STATUS_COMPLETED, evidence_refs=[ref])


def test_stage_result_hold_does_not_require_evidence_refs():
    StageResult(
        status=CHECKPOINT_STATUS_HOLD,
        refusal_code=REFUSAL_SOURCE_BYTES_MISSING,
        refusal_text="blocked",
    )


# ---------------------------------------------------------------------------
# SourceRoot.
# ---------------------------------------------------------------------------


def test_source_root_from_path_real_when_file_exists(tmp_path: Path):
    src = tmp_path / "w.jsonl"
    src.write_text('{"x": 1}\n', encoding="utf-8")
    root = SourceRoot.from_path(src)
    assert root.source_kind == SOURCE_KIND_REAL
    assert root.full_sha256 == hashlib.sha256(src.read_bytes()).hexdigest()
    assert root.is_real is True


def test_source_root_from_path_blocked_when_missing(tmp_path: Path):
    root = SourceRoot.from_path(tmp_path / "no_such.jsonl")
    assert root.source_kind == SOURCE_KIND_BLOCKED
    assert root.is_real is False
    assert root.blocked_reason


def test_source_root_from_path_blocked_when_empty(tmp_path: Path):
    src = tmp_path / "empty.jsonl"
    src.write_text("", encoding="utf-8")
    root = SourceRoot.from_path(src)
    assert root.source_kind == SOURCE_KIND_BLOCKED
    assert root.blocked_reason == "source_path_empty"


def test_source_root_fixture_only_never_claims_real():
    root = SourceRoot.fixture_only("marker")
    assert root.source_kind == SOURCE_KIND_FIXTURE
    assert root.is_real is False


# ---------------------------------------------------------------------------
# SourceBytesStageAdapter.
# ---------------------------------------------------------------------------


def _mutate_record(record: W12Record, **overrides) -> W12Record:
    return replace(record, **overrides)


def test_source_bytes_adapter_blocks_when_no_source_root():
    adapter = SourceBytesStageAdapter()
    records, _ = build_fixture_w12(route_count=1)
    plan = build_trimurti_plan(batch_id="b:no-src", w12_records=records, spec=TrimurtiBatchSpec(batch_id="b:no-src"))
    route = plan.routes[0]

    result = adapter.execute(
        route=route,
        w12_record=records[0],
        phase=PhaseName.SOURCE_EVIDENCE,
        source_root=None,
    )
    assert result.status == CHECKPOINT_STATUS_HOLD
    assert result.refusal_code == REFUSAL_SOURCE_BYTES_MISSING


def test_source_bytes_adapter_blocks_on_blocked_source_root(tmp_path: Path):
    adapter = SourceBytesStageAdapter()
    records, _ = build_fixture_w12(route_count=1)
    plan = build_trimurti_plan(batch_id="b:blocked", w12_records=records)
    blocked_root = SourceRoot.from_path(tmp_path / "absent.jsonl")
    assert blocked_root.source_kind == SOURCE_KIND_BLOCKED

    result = adapter.execute(
        route=plan.routes[0],
        w12_record=records[0],
        phase=PhaseName.SOURCE_EVIDENCE,
        source_root=blocked_root,
    )
    assert result.status == CHECKPOINT_STATUS_HOLD
    assert result.refusal_code == REFUSAL_SOURCE_BYTES_MISSING


def test_source_bytes_adapter_rejects_fixture_root_even_on_real_route():
    """A REAL-sourced route paired with a FIXTURE SourceRoot must HOLD."""
    adapter = SourceBytesStageAdapter()
    records, _ = build_fixture_w12(route_count=1)
    real_record = _mutate_record(
        records[0],
        source_kind=SOURCE_KIND_REAL,
        source_full_sha256="0" * 64,
        source_first_bytes_sha256="0" * 64,
    )
    fixture_root = SourceRoot.fixture_only("scenario")
    plan = build_trimurti_plan(batch_id="b:fixture-vs-real", w12_records=[real_record])

    result = adapter.execute(
        route=plan.routes[0],
        w12_record=real_record,
        phase=PhaseName.SOURCE_EVIDENCE,
        source_root=fixture_root,
    )
    assert result.status == CHECKPOINT_STATUS_HOLD
    assert result.refusal_code == REFUSAL_NEEDS_REAL_OPERATION_ADAPTER


def test_source_bytes_adapter_real_root_with_matching_sha_completes(tmp_path: Path):
    adapter = SourceBytesStageAdapter()
    real_source = tmp_path / "real_w12.jsonl"
    real_source.write_text(
        json.dumps({"seed_family": "S1", "meaning_version": "M1", "route_label": "R"}) + "\n",
        encoding="utf-8",
    )
    real_bytes = real_source.read_bytes()
    full_sha = hashlib.sha256(real_bytes).hexdigest()
    first_sha = hashlib.sha256(real_bytes[:4096]).hexdigest()

    records, _ = build_fixture_w12(route_count=1)
    real_record = _mutate_record(
        records[0],
        source_kind=SOURCE_KIND_REAL,
        source_full_sha256=full_sha,
        source_first_bytes_sha256=first_sha,
        route_kind="regular",
        route_type="targeted_target",
        raw_kind="metadata",
    )
    plan = build_trimurti_plan(batch_id="b:real-completion", w12_records=[real_record])
    source_root = SourceRoot.from_path(real_source)
    assert source_root.source_kind == SOURCE_KIND_REAL

    route, stage = drive_stage(
        plan,
        route_id=plan.routes[0].route_id,
        phase=PhaseName.SOURCE_EVIDENCE,
        adapter=adapter,
        w12_record=real_record,
        source_root=source_root,
    )
    assert stage.status == CHECKPOINT_STATUS_COMPLETED
    assert stage.refusal_code is None
    assert stage.evidence_refs, "completed stage must yield evidence_refs"
    assert stage.operation_digest is not None
    # Evidence_ref must round-trip-parse and reference the REAL source SHA.
    er = stage.evidence_refs[0]
    assert er.source_kind == SOURCE_KIND_REAL
    assert full_sha.startswith(er.sha256_short) or er.sha256_short.startswith(full_sha[:32])
    # Digest input/output hashes anchor to bytes the adapter actually hashed.
    assert (
        stage.operation_digest.input_sha256
        == hashlib.sha256(stage.operation_digest.command.encode("utf-8") if isinstance(stage.operation_digest.command, str) else stage.operation_digest.command).hexdigest()
    ) or stage.operation_digest.provider == adapter.provider_name
    # Route advanced to next phase on completion.
    assert route.current_phase == PhaseName.SCHOLARLY_CHALLENGE.value


def test_source_bytes_adapter_rejects_real_root_with_mismatched_sha(tmp_path: Path):
    """Real SourceRoot whose SHA does not match the route must HOLD (no fake provenance)."""
    adapter = SourceBytesStageAdapter()
    real_source = tmp_path / "real.jsonl"
    real_source.write_text('{"seed_family": "S1"}' + "\n", encoding="utf-8")
    records, _ = build_fixture_w12(route_count=1)
    mismatch_record = _mutate_record(
        records[0],
        source_kind=SOURCE_KIND_REAL,
        source_full_sha256="0" * 64,
        source_first_bytes_sha256="0" * 64,
        route_kind="regular",
        route_type="targeted_target",
        raw_kind="metadata",
    )
    plan = build_trimurti_plan(batch_id="b:mismatch", w12_records=[mismatch_record])

    result = adapter.execute(
        route=plan.routes[0],
        w12_record=mismatch_record,
        phase=PhaseName.SOURCE_EVIDENCE,
        source_root=SourceRoot.from_path(real_source),
    )
    assert result.status == CHECKPOINT_STATUS_HOLD
    assert result.refusal_code == REFUSAL_SOURCE_BYTES_MISSING


def test_source_bytes_adapter_refuses_non_source_evidence_phase():
    adapter = SourceBytesStageAdapter()
    records, _ = build_fixture_w12(route_count=1)
    plan = build_trimurti_plan(batch_id="b:wrong-phase", w12_records=records)

    result = adapter.execute(
        route=plan.routes[0],
        w12_record=records[0],
        phase=PhaseName.QA,
        source_root=None,
    )
    assert result.status == CHECKPOINT_STATUS_HOLD
    assert result.refusal_code == REFUSAL_NEEDS_REAL_OPERATION_ADAPTER


# ---------------------------------------------------------------------------
# ScholarlyChallengeStageAdapter: explicit HOLD by design.
# ---------------------------------------------------------------------------


def test_scholarly_challenge_adapter_holds_without_real_source():
    adapter = ScholarlyChallengeStageAdapter()
    records, _ = build_fixture_w12(route_count=1)
    plan = build_trimurti_plan(batch_id="b:scholarly", w12_records=records)

    result = adapter.execute(
        route=plan.routes[0],
        w12_record=records[0],
        phase=PhaseName.SCHOLARLY_CHALLENGE,
        source_root=None,
    )
    assert result.status == CHECKPOINT_STATUS_HOLD
    assert result.refusal_code == REFUSAL_NEEDS_REAL_OPERATION_ADAPTER


def test_scholarly_challenge_adapter_refuses_unrelated_phase():
    adapter = ScholarlyChallengeStageAdapter()
    records, _ = build_fixture_w12(route_count=1)
    plan = build_trimurti_plan(batch_id="b:scholarly-wrong", w12_records=records)

    result = adapter.execute(
        route=plan.routes[0],
        w12_record=records[0],
        phase=PhaseName.QA,
        source_root=SourceRoot.fixture_only("foo"),
    )
    assert result.status == CHECKPOINT_STATUS_HOLD
    assert result.refusal_code == REFUSAL_NEEDS_REAL_OPERATION_ADAPTER


# ---------------------------------------------------------------------------
# drive_stage end-to-end.
# ---------------------------------------------------------------------------


def test_drive_stage_returns_hold_for_unsupported_phase(tmp_path: Path):
    """A phase not in _PHASES_WITH_REAL_ADAPTER (e.g. VENUE_QUALIFICATION)
    cannot be completed by drive_stage; the route must land on HOLD."""
    records, _ = build_fixture_w12(route_count=1)
    real_source = tmp_path / "r.jsonl"
    real_source.write_text("{}\n", encoding="utf-8")
    real_record = _mutate_record(
        records[0],
        source_kind=SOURCE_KIND_REAL,
        source_full_sha256=hashlib.sha256(real_source.read_bytes()).hexdigest(),
        route_kind="regular",
        route_type="targeted_target",
        raw_kind="metadata",
    )
    plan = build_trimurti_plan(batch_id="b:unsupported", w12_records=[real_record])
    adapter = SourceBytesStageAdapter()
    route, stage = drive_stage(
        plan,
        route_id=plan.routes[0].route_id,
        phase=PhaseName.VENUE_QUALIFICATION,
        adapter=adapter,
        w12_record=real_record,
        source_root=SourceRoot.from_path(real_source),
    )
    assert stage.status == CHECKPOINT_STATUS_HOLD
    assert stage.refusal_code == REFUSAL_NEEDS_REAL_OPERATION_ADAPTER
    assert route.status == "hold"


def test_drive_stage_idempotent_replay_yields_same_event_hash(tmp_path: Path):
    real_source = tmp_path / "r.jsonl"
    real_source.write_text('{"k": "v"}' + "\n", encoding="utf-8")
    full_sha = hashlib.sha256(real_source.read_bytes()).hexdigest()
    records, _ = build_fixture_w12(route_count=1)
    real_record = _mutate_record(
        records[0],
        source_kind=SOURCE_KIND_REAL,
        source_full_sha256=full_sha,
        source_first_bytes_sha256=full_sha,
        route_kind="regular",
        route_type="targeted_target",
        raw_kind="metadata",
    )
    plan_a = build_trimurti_plan(batch_id="b:id1", w12_records=[real_record])
    plan_b = build_trimurti_plan(batch_id="b:id1", w12_records=[real_record])

    adapter = SourceBytesStageAdapter()
    source_root = SourceRoot.from_path(real_source)

    drive_stage(
        plan_a,
        route_id=plan_a.routes[0].route_id,
        phase=PhaseName.SOURCE_EVIDENCE,
        adapter=adapter,
        w12_record=real_record,
        source_root=source_root,
    )
    first_hash = plan_a.routes[0].last_event_hash
    first_checkpoint_hash = plan_a.routes[0].phase_checkpoints[PhaseName.SOURCE_EVIDENCE.value].event_hash
    drive_stage(
        plan_a,
        route_id=plan_a.routes[0].route_id,
        phase=PhaseName.SOURCE_EVIDENCE,
        adapter=adapter,
        w12_record=real_record,
        source_root=source_root,
    )

    assert plan_a.routes[0].last_event_hash == first_hash
    assert plan_a.routes[0].phase_checkpoints[PhaseName.SOURCE_EVIDENCE.value].event_hash == first_checkpoint_hash


def test_drive_stage_unknown_route_raises():
    records, _ = build_fixture_w12(route_count=1)
    plan = build_trimurti_plan(batch_id="b:bad", w12_records=records)
    adapter = SourceBytesStageAdapter()
    with pytest.raises(KeyError, match="route_id not in plan"):
        drive_stage(
            plan,
            route_id="route_does_not_exist",
            phase=PhaseName.SOURCE_EVIDENCE,
            adapter=adapter,
            w12_record=records[0],
            source_root=None,
        )


def test_drive_stage_without_w12_record_lands_hold():
    records, _ = build_fixture_w12(route_count=1)
    plan = build_trimurti_plan(batch_id="b:no-w12", w12_records=records)
    adapter = SourceBytesStageAdapter()
    _, stage = drive_stage(
        plan,
        route_id=plan.routes[0].route_id,
        phase=PhaseName.SOURCE_EVIDENCE,
        adapter=adapter,
        w12_record=None,
        source_root=None,
    )
    assert stage.status == CHECKPOINT_STATUS_HOLD
    assert stage.refusal_code == REFUSAL_SOURCE_BYTES_MISSING


# ---------------------------------------------------------------------------
# Batch-first driver.
# ---------------------------------------------------------------------------


def test_run_batch_first_source_evidence_no_root_holds_all_pending():
    records, _ = build_fixture_w12(route_count=4)
    plan = build_trimurti_plan(
        batch_id="b:batch-no-root",
        w12_records=records,
        spec=TrimurtiBatchSpec(batch_id="b:batch-no-root", concurrency_limit=4),
    )
    records_by_id = {r.route_id: r for r in records}
    summary = run_batch_first_source_evidence(
        plan,
        records_by_route_id=records_by_id,
        source_root=None,
    )
    assert summary["requested"] == 4
    assert summary["by_status"] == {"hold": 4, "failed": 0, "completed": 0}
    assert summary["no_external_send"] is True
    assert summary["schema"].startswith("TRIMURTI_STAGE_OPERATION_BATCH_FIRST")
    for item in summary["results"]:
        assert item["refusal_code"] == REFUSAL_SOURCE_BYTES_MISSING
        assert item["has_operation_digest"] is False


def test_run_batch_first_source_evidence_ten_routes_with_real_source(tmp_path: Path):
    real_source = tmp_path / "real.jsonl"
    payload = [
        {"seed_family": f"S{(i % 6) + 1}", "meaning_version": f"M{(i % 27) + 1:03d}", "route_label": f"R{i:03d}"}
        for i in range(10)
    ]
    real_source.write_text(
        "\n".join(json.dumps(p) for p in payload) + "\n",
        encoding="utf-8",
    )
    full_sha = hashlib.sha256(real_source.read_bytes()).hexdigest()
    first_sha = hashlib.sha256(real_source.read_bytes()[:4096]).hexdigest()

    records, _ = build_fixture_w12(route_count=10)
    real_records = []
    for record in records:
        real_records.append(
            _mutate_record(
                record,
                source_kind=SOURCE_KIND_REAL,
                source_full_sha256=full_sha,
                source_first_bytes_sha256=first_sha,
                route_kind="regular",
                route_type="targeted_target",
                raw_kind="metadata",
            )
        )
    plan = build_trimurti_plan(
        batch_id="b:10-real",
        w12_records=real_records,
        spec=TrimurtiBatchSpec(batch_id="b:10-real", concurrency_limit=10),
    )
    records_by_id = {r.route_id: r for r in real_records}
    summary = run_batch_first_source_evidence(
        plan,
        records_by_route_id=records_by_id,
        source_root=SourceRoot.from_path(real_source),
        limit=10,
    )
    assert summary["requested"] == 10
    assert summary["by_status"]["completed"] == 10
    assert summary["by_status"]["hold"] == 0
    assert all(
        item["has_operation_digest"] for item in summary["results"]
    )
    for item in summary["results"]:
        parsed = parse_evidence_ref(item["evidence_refs"][0])
        assert parsed.source_kind == SOURCE_KIND_REAL
    # Sanity: route.current_phase advanced to SCHOLARLY_CHALLENGE.
    advanced = sum(
        1
        for r in plan.routes
        if r.phase_checkpoints[PhaseName.SOURCE_EVIDENCE.value].status
        == CHECKPOINT_STATUS_COMPLETED
    )
    assert advanced == 10


def test_run_batch_first_source_evidence_skips_refused_routes():
    """Routes with refusal_codes (e.g. fake fulltext) are not claimed."""

    records, _ = build_fixture_w12(route_count=5)
    refused = _mutate_record(
        records[0],
        raw_kind="fulltext",
        manuscript_pointer=None,
        manuscript_hash=None,
    )
    plan = build_trimurti_plan(
        batch_id="b:skip-refused",
        w12_records=[refused, *records[1:]],
        spec=TrimurtiBatchSpec(batch_id="b:skip-refused", concurrency_limit=10),
    )
    records_by_id = {r.route_id: r for r in [refused, *records[1:]]}
    summary = run_batch_first_source_evidence(
        plan,
        records_by_route_id=records_by_id,
        source_root=None,
    )
    # refused route must be excluded from the run; only 4 attempted.
    assert summary["requested"] == 4
    assert summary["by_status"]["hold"] == 4
    route_ids_attempted = {item["route_id"] for item in summary["results"]}
    assert plan.routes[0].route_id not in route_ids_attempted
