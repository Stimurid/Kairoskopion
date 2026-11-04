"""F4 review-to-Artikl return within the existing Trimurti manuscript Factory.

Uses an exact M117 independent review and C04 v0.6; the registered Artikl
chooses how to proceed. Only its REVISION_CANDIDATE outcome creates a new
working manuscript and calls an independent reader. No new hunt or journal
send is silently launched. D27 is a candidate, not canonical release.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

from .publication_runner import EvidenceBlocked, sha256
from .manuscript_draft_intake import ingest
from .native_editorial_cycle import (
    read, readsha, save, emit, native_call, cli_app, _verify_review,
)

SCHEMA = "trimurti-native-artikl-review-return-v1"
CHOICES = {"REVISION_CANDIDATE", "MORE_RESEARCH", "KEEP_WORKING_DRAFT", "PARK"}


def preflight(m: dict) -> dict:
    if m.get("schema") != SCHEMA or m.get("case_id") != "T3-TALK-20261019":
        raise EvidenceBlocked("review_return_manifest_invalid")
    if m.get("author_gate") != "HOLD" or m.get("send") is not False or m.get("world_mutation") is not False:
        raise EvidenceBlocked("review_return_owner_boundary_invalid")
    files = {}
    for name in ("source", "baseline", "review", "science", "whitecrow", "m117_provenance"):
        row = m.get(name) or {}
        expected = row.get("sha256") or ""
        if not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise EvidenceBlocked("missing_sha_pin:" + name)
        path = Path(row.get("path") or "")
        files[name] = {"path": path, "sha256": expected, "bytes": readsha(path, expected)}
    if files["source"]["sha256"] != "807df2a6d8f0f2eef0ef7052f8653c41727566a54693a5333be4c9414b2a54da":
        raise EvidenceBlocked("unexpected_C04_source")
    provenance = read(files["m117_provenance"]["path"])
    if (provenance.get("actual_new_working_manuscript_sha256") != files["baseline"]["sha256"]
        or provenance.get("independent_review_sha256") != files["review"]["sha256"]
        or provenance.get("author_gate") != "HOLD"
        or provenance.get("journal_send") is not False):
        raise EvidenceBlocked("M117_source_review_identity_conflict")
    review = read(files["review"]["path"])
    _verify_review(review, files["baseline"]["path"])
    if (review.get("reviewer") != "CODEX_DISTINCT_PROCESS"
        or review.get("verdict") not in ("SCOPED_PASS", "REVISION_REQUIRED", "PARK")):
        raise EvidenceBlocked("untrusted_M117_independent_review")
    science = read(files["science"]["path"])
    if (science.get("author_gate") != "HOLD"
        or science.get("original_source_sha256") != files["source"]["sha256"]):
        raise EvidenceBlocked("science_original_source_changed")
    source_root = Path(m.get("artikl_source_root") or "")
    names = ("ENTRY_MANIFEST.md", "RELEASE_MANIFEST.md", "BASE_COLD_REENTER.md",
             "GATEWAY.md", "LIVE_CORE.md", "CAPABILITY_REGISTRY.md")
    for name in names:
        p = source_root/name
        if not p.is_file() or p.stat().st_size < 900:
            raise EvidenceBlocked("canonical_artikl_body_missing:" + name)
    entry = (source_root/"ENTRY_MANIFEST.md").read_text(encoding="utf-8-sig")
    release = (source_root/"RELEASE_MANIFEST.md").read_text(encoding="utf-8-sig")
    if ("RC9 POST-MERGE ACCEPTANCE CLOSURE" not in entry
        or "CURRENT_RELEASE = ARTIKL 1.0.0-rc9" not in entry
        or "CURRENT ARTIKL RELEASE remains rc9" not in release):
        raise EvidenceBlocked("artikl_release_not_resolved_rc9")
    return files


def _decision_prompt(m: dict, f: dict) -> str:
    """One bounded incremental return: host supplies full verified text in-band.

    The previous M117 native Artikl already performed canonical rc9 reads.
    The host preflight verified current six rc9 carriers and SHA-pinned files.
    Repeating full-body exploration inside a short editorial decision can
    exhaust the OpenClaw run budget without ever reaching a decision.
    """
    baseline = f["baseline"]["bytes"].decode("utf-8-sig")
    review = f["review"]["bytes"].decode("utf-8-sig")
    science = f["science"]["bytes"].decode("utf-8-sig")
    provenance = f["m117_provenance"]["bytes"].decode("utf-8-sig")
    header = (
        "TRIMURTI F4 / registered ARTIKL rc9 / INCREMENTAL REVIEW RETURN.\n"
        "The Factory host has verified all six current SOURCE_ARTIKL rc9 carriers "
        "and the exact source, science, manuscript, M117 review and provenance SHA. "
        "This is a continuation after M117's documented native Artikl rc9 invocation, "
        "NOT a new cold entry, not a canonical release promotion.\n"
        "The complete current manuscript, complete independent review and current "
        "science/provenance material are EMBEDDED below. Do not spend this decision "
        "stage searching for tools or rereading the same carriers. NO TOOL CALLS "
        "are needed or authorized in this DECISION stage. Do not run a hunt, "
        "write a manuscript, change files or modify Git here.\n"
        "Source identity (prior author C04) SHA256: "
        + f["source"]["sha256"] + ". Manuscript SHA256: "
        + f["baseline"]["sha256"] + ". Review SHA256: "
        + f["review"]["sha256"] + ".\n"
        "Honor rc9 D14/D15/D18/D21 and D24 evidence characterization, "
        "D25 author approval as separate authority. D27 is only a candidate. "
        "Preserve the five protected conceptual nuclei and real author decisions; "
        "do not drown organogenesis in defensive prose. The original author "
        "carrier and WhiteCrow source-depth record were fully SHA-verified by "
        "the host; do not pretend to have reread their complete contents in "
        "this turn. WhiteCrow source quality is evidence information, NOT as permission to write.\n"
        "The three remaining M117 scientific findings are fulltext nearest "
        "competitor comparison, unexecuted empirical design, and exact "
        "author-source passage/version citation. SCOPED_PASS is neither a novelty "
        "certificate nor an author/publication decision.\n"
        "Freely choose one next intellectual operation: REVISION_CANDIDATE, "
        "MORE_RESEARCH, KEEP_WORKING_DRAFT, or PARK. No external source-depth "
        "gate authorizes or forbids a working revision. Give actual intellectual "
        "reasons, concrete changes/research needs and exactly which M117 findings "
        "matter. Do not fabricate empirical validation, fulltext reads, data or claims of fixes.\n"
        "Return ONLY one JSON object, no fences or explanatory text, with keys: "
        "schema='trimurti-artikl-review-return-decision-v1', agent_id='artikl', "
        "current_release='ARTIKL 1.0.0-rc9', "
        "baseline_sha256='" + f["baseline"]["sha256"] + "', "
        "independent_review_sha256='" + f["review"]["sha256"] + "', "
        "decision=(one of the four exact choice strings), "
        "reason=(specific substantive rationale at least 30 chars), "
        "planned_changes=(array of strings), research_needs=(array of strings), "
        "review_findings_used=(array of issue.kind values), "
        "author_gate='HOLD', send=false, world_mutation=false, "
        "d25_manuscript_go=false.\n"
        "=== BEGIN COMPLETE BASELINE MANUSCRIPT C04 v0.6 ===\n"
    )
    return (header + baseline
            + "\n=== END COMPLETE BASELINE; BEGIN COMPLETE M117 REVIEW ===\n"
            + review
            + "\n=== END M117 REVIEW; BEGIN PREVIOUS SCIENCE PACKET ===\n"
            + science
            + "\n=== END SCIENCE; BEGIN M117 PROVENANCE ===\n"
            + provenance
            + "\n=== END VERIFIED MATERIAL ===\n"
            "Your immediate next message MUST be the single decision JSON, "
            "without tool discovery or calls. Preserve AUTHOR HOLD.")

def _writer_prompt(m: dict, f: dict, choice: dict, target: Path) -> str:
    return (
      "TRIMURTI F4 ARTIKL rc9. You independently chose REVISION_CANDIDATE; "
      "execute your exact editorial choice, not an externally forced revision. "
      "Read current six SOURCE_ARTIKL files " + str(m["artikl_source_root"]) + ". "
      "Read the COMPLETE baseline manuscript " + str(f["baseline"]["path"]) + ", "
      "the COMPLETE independent M117 review " + str(f["review"]["path"]) + ", "
      "the original author source " + str(f["source"]["path"]) + ", and "
      "the scientific packet " + str(f["science"]["path"]) + ". "
      "Your decision was " + json.dumps(choice,ensure_ascii=False) + ". "
      "Write ONE COMPLETE substantively improved Russian scholarly working "
      "manuscript, more than 3100 words and at least seven genuine sections. "
      "Retain all protected conceptual nuclei and previous accepted decisions. "
      "Repair exactly what you chose to repair; allow honest named scientific "
      "gaps without inventing source content or empirical results. "
      "Do not turn the argument into a compliance checklist. "
      "Use your authorized local file tool to WRITE UTF-8 Markdown EXACTLY "
      "to this new file: " + str(target) + ". "
      "Do not modify original files, previous versions, WORLD, or Git. "
      "Read back the complete written file and its SHA256. "
      "Return JSON only: schema='trimurti-artikl-native-review-return-writer-v1', "
      "sha256=(actual SHA of file), author_gate='HOLD', send=false, "
      "sections_written=(array), critical_repairs=(array), "
      "remaining_science_debt=(array). The actual full file is obligatory."
    )


def _writer_file_after_gateway_timeout(root: Path, path: Path) -> dict:
    """Recover only a physically completed same-session native write; never repay."""
    gateway = root/"return_writer.gateway.json"
    started = root/"return_writer.started"
    if not (gateway.is_file() and started.is_file() and path.is_file()):
        raise EvidenceBlocked("return_writer_incomplete_or_unreceipted")
    outer = read(gateway)
    meta = ((outer.get("result") or {}).get("meta") or {})
    agent = meta.get("agentMeta") or {}
    session_marker = started.read_text(encoding="ascii").strip()
    if not session_marker.startswith("NATIVE_ARTIKL_CALL "):
        raise EvidenceBlocked("return_writer_bad_session_marker")
    sid = session_marker.split(" ", 1)[1]
    receipt = agent.get("terminalReceipt") or {}
    if (outer.get("status") != "timeout"
        or outer.get("timeoutPhase") != "provider" or outer.get("providerStarted") is not True
        or agent.get("sessionId") != sid or receipt.get("runId") != outer.get("runId")
        or receipt.get("sessionId") != sid or "write" not in (receipt.get("successfulToolNames") or [])
        or agent.get("aborted") is True):
        raise EvidenceBlocked("return_writer_native_same_run_write_not_attested")
    data = path.read_bytes()
    text = data.decode("utf-8")
    if (not text.startswith("# ") or len(text.split()) < 3100
        or text.count("\n## ") < 7 or len(data) < 20000):
        raise EvidenceBlocked("return_writer_native_file_incomplete")
    info = {"schema": "T3_F4_NATIVE_WRITER_FILE_RECOVERY_V1",
            "run_id": outer["runId"], "session_id": sid,
            "gateway_sha256": sha256(gateway.read_bytes()),
            "file_sha256": sha256(data), "final_model_reply_received": False,
            "new_model_calls": 0, "author_gate": "HOLD", "send": False}
    emit(root/"return_writer_file_recovery_receipt.json", info)
    return {"sha256": sha256(data), "author_gate": "HOLD", "send": False,
            "file_recovered_without_final_model_reply": True}


def _independent_next_review(root: Path, m: dict, f: dict, target: Path,
                             latest_whitecrow: Path | None = None,
                             latest_evidence: Path | None = None,
                             latest_decision: dict | None = None) -> dict:
    out = root/"review.json"
    if out.exists():
        return read(out)
    if (root/"review.started").exists():
        raise EvidenceBlocked("unreceipted_second_independent_review")
    instructions = (
      "INDEPENDENT FULL-TEXT EDITORIAL REVIEW of C04. Read the COMPLETE "
      "prior working draft " + str(f["baseline"]["path"]) + ", COMPLETE "
      "M117 independent review " + str(f["review"]["path"]) + ", and COMPLETE "
      "new working manuscript " + str(target) + " pinned SHA256 "
      + sha256(target.read_bytes()) + ". "
      "Work in a distinct model process, not the registered Artikl. "
      "Check before/after against all M117 issue kinds, preservation of "
      "the scientific and conceptual core, exact author-source claims, "
      "and absence of invented empirical results. Do not award source "
      "novelty or author acceptance. Record negative results. "
      "Every issue must include an ACTUAL line number and short verbatim "
      "quote from that exact line; do not invent anchors. "
      "Return ONLY a JSON object with schema="
      "'trimurti-independent-C04-rewrite-review-v1', "
      "draft_sha256='" + sha256(target.read_bytes()) + "', "
      "reviewer='CODEX_DISTINCT_PROCESS', "
      "verdict='SCOPED_PASS|REVISION_REQUIRED|PARK', "
      "issues=(list of {kind,line,literal_quote,explanation,action}), "
      "M117_items=(list of {issue,status,delta}), "
      "next_action=(string), author_gate='HOLD', send=false."
    )
    if latest_whitecrow is not None or latest_evidence is not None:
        if latest_whitecrow is None or latest_evidence is None or not isinstance(latest_decision,dict):
            raise EvidenceBlocked("F4_latest_science_review_context_incomplete")
        if (latest_decision.get("decision")!="REVISION_CANDIDATE"
            or latest_decision.get("whitecrow_report_sha256")!=sha256(latest_whitecrow.read_bytes())
            or latest_decision.get("real_indago_evidence_sha256")!=sha256(latest_evidence.read_bytes())
            or latest_decision.get("author_gate")!="HOLD"):
            raise EvidenceBlocked("F4_latest_science_review_context_mismatch")
        instructions += (
            "\nPOST-RESEARCH SOURCE CONTEXT: Read the COMPLETE actual WhiteCrow "
            "FieldCore D24 report at "+str(latest_whitecrow)
            +" SHA256 "+sha256(latest_whitecrow.read_bytes())+". "
            "Read the COMPLETE native Indago EvidenceReturn at "+str(latest_evidence)
            +" SHA256 "+sha256(latest_evidence.read_bytes())+". "
            "These are real executor results, NOT science saturation or proven primary "
            "source depth. Distinguish candidates and metadata from full-source claims. "
            "The registered Artikl rc9 explicitly selected REVISION_CANDIDATE, "
            "not manuscript approval: "+json.dumps(latest_decision,ensure_ascii=False)
            +". Check every new empirical assertion and named-source attribution "
            "against verified passages; if unavailable mark UNVERIFIED. "
            "Pay special attention to prospective eligibility vs retrospective "
            "confirmation, W versus E0-E3 variables, rival mechanisms, failed "
            "cases, and independent coding reliability. No fabricated novelty, "
            "no D25 GO, no author acceptance.\n"
        )
    save(root/"review.prompt.txt", instructions.encode("utf-8"))
    save(root/"review.started", b"ONE_CODEX_INDEPENDENT_REVIEW\n")
    command = [cli_app("codex"), "exec", "-C", str(Path(m["scientific_repo"])),
               "--sandbox", "read-only", "-o", str(out), "-"]
    try:
        cp = subprocess.run(command, input=instructions, encoding="utf-8",
                            errors="replace", capture_output=True,
                            cwd=Path(m["scientific_repo"]), timeout=600, check=False,
                            env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
    except subprocess.TimeoutExpired as ex:
        if ex.stdout:
            save(root/"review.timeout_stdout", ex.stdout if isinstance(ex.stdout, bytes) else ex.stdout.encode("utf-8"))
        raise EvidenceBlocked("independent_F4_reviewer_timeout_no_retry") from ex
    save(root/"review.stdout.log", cp.stdout.encode("utf-8"))
    save(root/"review.stderr.log", cp.stderr.encode("utf-8"))
    if cp.returncode != 0 or not out.is_file():
        raise EvidenceBlocked("independent_F4_reviewer_failed_no_second_call")
    return read(out)


def _intake(root: Path, f: dict, target: Path) -> str:
    inp = root/"factory_intake_inputs"
    inp.mkdir(exist_ok=True)
    for name, content in (("source", f["source"]["bytes"]),
                          ("science", f["science"]["bytes"]),
                          ("draft", target.read_bytes())):
        save(inp/(name+".txt"), content)
    artifacts = {n: {"path": n+".txt", "sha256": sha256((inp/(n+".txt")).read_bytes())}
                 for n in ("source", "science", "draft")}
    manifest = {
      "schema": "trimurti-manuscript-draft-intake-v1",
      "case_id": "T3-TALK-20261019",
      "claim_id": "KC-C04-GUARMEAS-JIBE-CRESTI",
      "route_id": "C-GUARMEAS-JIBE-CRESTI",
      "producer_ref": "NATIVE_ARTIKL_RC9_F4_REVIEW_RETURN",
      "evidence_mode": "REAL", "author_gate": "HOLD", "submission_enabled": False,
      "scientific_novelty_accepted": False, "article_seed_author_approved": False,
      "source_original_sha256": f["source"]["sha256"],
      "artifacts": artifacts
    }
    emit(inp/"manifest.json", manifest)
    ingest(manifest_path=inp/"manifest.json", input_root=inp,
           output_root=root/"factory_intake",
           trusted_source_sha256=f["source"]["sha256"],
           trusted_science_sha256=f["science"]["sha256"])
    return sha256((root/"factory_intake"/"draft-intake-receipt.json").read_bytes())


def run(manifest: Path, expected_manifest_sha: str, root: Path) -> dict:
    readsha(manifest, expected_manifest_sha)
    m = read(manifest)
    f = preflight(m)
    root.mkdir(parents=True, exist_ok=True)
    receipt = root/"review_return_receipt.json"
    if receipt.exists():
        old = read(receipt)
        if old.get("manifest_sha256") != expected_manifest_sha or old.get("author_gate") != "HOLD":
            raise EvidenceBlocked("review_return_previous_identity_conflict")
        if old.get("candidate_sha256"):
            p = root/"draft_v0_7.md"
            if sha256(p.read_bytes()) != old["candidate_sha256"]:
                raise EvidenceBlocked("review_return_draft_changed")
            if sha256((root/"review.json").read_bytes()) != old["independent_review_sha256"]:
                raise EvidenceBlocked("review_return_review_changed")
        return {**old, "replay": "IDENTICAL_NO_NEW_MODEL_CALLS"}
    lock = root/"review_return.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as ex:
        raise EvidenceBlocked("review_return_already_running_or_interrupted") from ex
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write("RUNNING\n")
        choice = native_call(root, "return_decision", _decision_prompt(m, f), timeout=240)
        if (choice.get("schema") != "trimurti-artikl-review-return-decision-v1"
            or choice.get("agent_id") != "artikl"
            or choice.get("current_release") != "ARTIKL 1.0.0-rc9"
            or choice.get("decision") not in CHOICES
            or choice.get("baseline_sha256") != f["baseline"]["sha256"]
            or choice.get("independent_review_sha256") != f["review"]["sha256"]
            or not isinstance(choice.get("reason"), str) or len(choice["reason"]) < 30
            or choice.get("author_gate") != "HOLD"
            or choice.get("send") is not False
            or choice.get("world_mutation") is not False
            or choice.get("d25_manuscript_go") is not False):
            raise EvidenceBlocked("Artikl_review_return_choice_invalid")
        emit(root/"decision.json", choice)
        output = {"schema": SCHEMA, "manifest_sha256": expected_manifest_sha,
                  "source_sha256": f["source"]["sha256"],
                  "baseline_sha256": f["baseline"]["sha256"],
                  "M117_review_sha256": f["review"]["sha256"],
                  "previous_M117_provenance_sha256": f["m117_provenance"]["sha256"],
                  "decision": choice["decision"],
                  "decision_gateway_sha256": sha256((root/"return_decision.gateway.json").read_bytes()),
                  "decision_sha256": sha256((root/"decision.json").read_bytes()),
                  "author_gate": "HOLD", "send": False, "world_mutation": False,
                  "new_indago_hunts": 0, "new_w12_routes": 0, "publication_ready": False,
                  "D27_canonical_mounted": False}
        if choice["decision"] != "REVISION_CANDIDATE":
            output["status"] = "REVIEW_RETURN_" + choice["decision"] + "_AUTHOR_HOLD"
            output["new_manuscripts"] = 0
            emit(receipt, output)
            return output
        target = root/"draft_v0_7.md"
        try:
            writer = native_call(root, "return_writer",
                                 _writer_prompt(m, f, choice, target), timeout=480)
        except EvidenceBlocked:
            writer = _writer_file_after_gateway_timeout(root, target)
        if not target.is_file():
            raise EvidenceBlocked("F4_writer_did_not_produce_full_file")
        draft = target.read_bytes()
        text = draft.decode("utf-8")
        if (not text.startswith("# ") or len(text.split()) < 3100
            or len(text.split()) > 11000 or text.count("\n## ") < 7
            or len(draft) < 20000):
            raise EvidenceBlocked("F4_artikl_not_full_manuscript")
        if writer.get("sha256") != sha256(draft) or writer.get("author_gate") != "HOLD":
            raise EvidenceBlocked("F4_writer_sha_or_author_mismatch")
        output["intake_sha256"] = _intake(root, f, target)
        review = _independent_next_review(root, m, f, target)
        _verify_review(review, target)
        if (review.get("reviewer") != "CODEX_DISTINCT_PROCESS"
            or review.get("verdict") not in ("SCOPED_PASS", "REVISION_REQUIRED", "PARK")):
            raise EvidenceBlocked("F4_independent_reviewer_invalid")
        output.update({
            "status": "REVIEW_RETURN_FULL_REVISION_AND_REVIEW_AUTHOR_HOLD",
            "candidate_sha256": sha256(draft),
            "candidate_words": len(text.split()),
            "candidate_path": str(target),
            "independent_review_sha256": sha256((root/"review.json").read_bytes()),
            "independent_review_verdict": review["verdict"],
            "new_manuscripts": 1,
            "independent_reviews": 1,
        })
        emit(receipt, output)
        return output
    finally:
        lock.unlink(missing_ok=True)



def prepare_more_research_handoff(
    *, manifest: Path, expected_manifest_sha: str, root: Path,
    whitecrow_root: Path, trusted_whitecrow_commit: str,
    trusted_whitecrow_module_sha: str,
) -> dict:
    """No model calls: ARTIKL's verified choice -> canonical D24 -> ONE pending Indago request.

    D24 describes the source gap; it DOES NOT veto Artikl's writing authority.
    ResearchNeed != ResearchRequest != actual ResearchRun. Nothing is dispatched
    from this operation, and the native Perpetuum hunt is not silently shortened.
    """
    import importlib
    import sys
    from .native_whitecrow_stage import _validate_source, WHITE_CROW_SOURCE

    readsha(manifest, expected_manifest_sha)
    m = read(manifest)
    f = preflight(m)
    root = root.resolve()
    terminal_path = root/"review_return_receipt.json"
    choice_path = root/"decision.json"
    if not (terminal_path.is_file() and choice_path.is_file()):
        raise EvidenceBlocked("no_completed_native_review_return_decision")
    result = read(terminal_path)
    choice = read(choice_path)
    decision_sha = sha256(choice_path.read_bytes())
    if (result.get("status") != "REVIEW_RETURN_MORE_RESEARCH_AUTHOR_HOLD"
        or result.get("decision") != "MORE_RESEARCH"
        or result.get("decision_sha256") != decision_sha
        or result.get("manifest_sha256") != expected_manifest_sha
        or result.get("M117_review_sha256") != f["review"]["sha256"]
        or result.get("baseline_sha256") != f["baseline"]["sha256"]
        or choice.get("decision") != "MORE_RESEARCH"
        or choice.get("author_gate") != "HOLD"
        or choice.get("send") is not False
        or choice.get("world_mutation") is not False):
        raise EvidenceBlocked("native_artikl_research_choice_not_authorized")
    needs = choice.get("research_needs")
    if (not isinstance(needs, list) or not 1 <= len(needs) <= 8
        or any(not isinstance(q, str) or not 30 <= len(q.strip()) <= 1200 for q in needs)):
        raise EvidenceBlocked("native_artikl_research_needs_missing")

    # Validate the actual canonical WhiteCrow code, not a synthetic proxy.
    pinned = _validate_source(
        whitecrow_root, trusted_whitecrow_commit, trusted_whitecrow_module_sha)
    module_root = str(whitecrow_root.resolve())
    if module_root not in sys.path:
        sys.path.insert(0, module_root)
    wc = importlib.import_module("fieldcore.academic_due_diligence")
    if Path(wc.__file__).resolve() != (
        whitecrow_root.resolve()/WHITE_CROW_SOURCE).resolve():
        raise EvidenceBlocked("whitecrow_runtime_source_not_pinned")

    question = (
        "Which published scientific mechanisms directly anticipate or refute "
        "C04 v0.6's temporary organogenesis of an absent productive capability, "
        "and which original-source citations and empirical conditions remain ungrounded?")
    base = {
        "question": question,
        "read_bodies": [],
        "primary_passages": [],
        "locator_hits": [{
            "source": "M117_INDEPENDENT_REVIEW",
            "source_sha256": f["review"]["sha256"],
            "read_depth": "FULL_MANUSCRIPT_REVIEW_NOT_PRIMARY_HUNT"}],
        "coverage_evidence": {},
        "known_unknowns": [str(q) for q in needs],
        "open_research_needs": [{
            "need_type": "SOURCE",
            "question_or_gap": str(q),
            "required_evidence_or_action":
                "Check full original scholarly bodies and exact passage/page anchors; "
                "return contrary results, limits and unknowns; do not certify novelty.",
            "routing_target": "INDAGO",
            "fallback_routing_target": "LITOPS",
            "priority": "RESEARCH_REQUESTED_BY_ARTIKL",
            "provenance": [{
                "source": "NATIVE_ARTIKL_M117_REVIEW_RETURN",
                "decision_sha256": decision_sha,
                "baseline_sha256": f["baseline"]["sha256"],
                "review_sha256": f["review"]["sha256"]}],
        } for q in needs],
    }
    report = wc.build_disciplinary_positioning_report(
        base, semantic_action_mode="CRITIQUE", trigger_ref="F4:"+decision_sha)
    all_needs = report.get("open_research_needs") or []
    if (report.get("research_readiness") != "BLOCKED_ON_DUE_DILIGENCE"
        or len(all_needs) < len(needs)):
        raise EvidenceBlocked("whitecrow_no_native_research_gap")

    # Keep WhiteCrow's complete diagnostic; route only the EXACT four specific
    # research needs from native Artikl, not three extra generic duplicates.
    selected = dict(report)
    selected["open_research_needs"] = all_needs[-len(needs):]
    for q, item in zip(needs, selected["open_research_needs"]):
        if item.get("question_or_gap") != q:
            raise EvidenceBlocked("whitecrow_artikl_research_need_identity_lost")
    request_prefix = (
        "T3-F4-"+f["source"]["sha256"][:12]+"-"+decision_sha[:12])
    request = wc.build_research_handoff(
        selected, request_id=request_prefix)
    if (not request
        or request.get("execution_target") != "INDAGO"
        or request.get("semantic_owner") != "ARTIKL_WHITECROW"
        or request.get("semantic_action_mode") != "CRITIQUE"
        or request.get("research_run_id") is not None
        or len(request.get("research_needs") or []) != len(needs)):
        raise EvidenceBlocked("whitecrow_request_did_not_preserve_artikl_choice")
    transport = wc.render_indago_direct_hunt_task(
        request, task_label="TRIMURTI_F4_M117_ARTIKL_REVIEW_RETURN")
    handoff_dir = root/"more_research_handoff"
    handoff_dir.mkdir(exist_ok=True)
    report_sha = emit(handoff_dir/"whitecrow_report.json", report)
    request_sha = emit(handoff_dir/"research_request_PENDING.json", request)
    body = (transport.rstrip("\n")+"\n").encode("utf-8")
    save(handoff_dir/"indago_task_PENDING.txt", body)
    task_sha = sha256(body)
    receipt = {
        "schema": "T3_F4_M117_CANONICAL_D24_TO_INDAGO_HANDOFF_V1",
        "case_id": m["case_id"],
        "source_sha256": f["source"]["sha256"],
        "baseline_sha256": f["baseline"]["sha256"],
        "M117_review_sha256": f["review"]["sha256"],
        "native_artikl_decision_sha256": decision_sha,
        "whitecrow_code": pinned,
        "whitecrow_report_sha256": report_sha,
        "request_sha256": request_sha,
        "research_request_id": request["research_request_id"],
        "dispatch_event_id": request["dispatch_event_id"],
        "indago_transport_sha256": task_sha,
        "research_needs_count": len(needs),
        "status": "PENDING_NOT_DISPATCHED",
        "indago_deep_hunt_execution": "NOT_STARTED",
        "new_native_hunts": 0,
        "new_W12_routes": 0,
        "author_gate": "HOLD",
        "send": False,
        "world_mutation": False,
        "not_a_science_approval": True,
    }
    emit(handoff_dir/"handoff_receipt.json", receipt)
    return receipt



def main(argv: list[str] | None = None) -> int:
    import sys
    args = list(sys.argv[1:] if argv is None else argv)
    handoff = bool(args and args[0] == "handoff")
    if handoff:
        args.pop(0)
    parser = argparse.ArgumentParser(prog="manuscript_cycle_runner editorial-return")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    if handoff:
        parser.add_argument("--whitecrow-root", type=Path, required=True)
        parser.add_argument("--trusted-whitecrow-commit", required=True)
        parser.add_argument("--trusted-whitecrow-module-sha", required=True)
    a = parser.parse_args(args)
    try:
        result = (prepare_more_research_handoff(
            manifest=a.manifest, expected_manifest_sha=a.expected_manifest_sha,
            root=a.output_root, whitecrow_root=a.whitecrow_root,
            trusted_whitecrow_commit=a.trusted_whitecrow_commit,
            trusted_whitecrow_module_sha=a.trusted_whitecrow_module_sha)
            if handoff else run(a.manifest, a.expected_manifest_sha, a.output_root))
    except (OSError, ValueError, KeyError, EvidenceBlocked, subprocess.TimeoutExpired) as ex:
        print(json.dumps({"status": "HOLD_RUNTIME_OR_EDITORIAL",
                          "reason": str(ex)[:300], "author_gate": "HOLD",
                          "send": False, "new_w12_routes": 0}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
