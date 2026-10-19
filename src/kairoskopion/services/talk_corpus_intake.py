"""TRM-074: bounded talk-source admission into existing Kairoskopion registries.

Consumes an owner-authorized local capture manifest. No network calls, publication
claims, generative article writing, WORLD mutation, or journal submissions.
"""
from __future__ import annotations

from difflib import SequenceMatcher
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from typing import Any

from ..adapters.source_intake import SourceRole, register_local_source
from ..persistence import ensure_registry_root
from ..registry import append, read_all


VALID_KINDS = frozenset({
    "SPEECH_SCRIPT", "SOURCE_TRANSCRIPT", "RECONSTRUCTED_TRANSCRIPT",
    "CONCEPT_BASELINE", "EDITORIAL_COMPARISON", "SLIDES",
    "WORD_WITH_COMMENTS", "RECORDED_PERFORMANCE",
})
AUTHOR_STATES = frozenset({
    "NOT_VERIFIED", "USER_ACCEPTED_CONCEPTS_ONLY",
    "ORIGINAL_TEXT_ONLY_AUDIO_UNVERIFIED", "RECONSTRUCTION_NOT_PERFORMANCE",
    "AI_EDITORIAL_PROPOSAL_NOT_AUTHOR_APPROVAL",
})
_DELTA_LIMIT = 12


def _digest(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def _passage(paragraphs: list[str], pos: int) -> dict[str, Any] | None:
    if pos < 0 or pos >= len(paragraphs):
        return None
    paragraph = paragraphs[pos]
    return {
        "paragraph_index_zero_based": pos,
        "paragraph_sha256": _digest(paragraph),
        "excerpt": paragraph[:360],
    }


def _delta(before: dict[str, Any], after: dict[str, Any],
           before_text: str, after_text: str) -> dict[str, Any]:
    a, b = _paragraphs(before_text), _paragraphs(after_text)
    matcher = SequenceMatcher(None, [_digest(x) for x in a],
                              [_digest(x) for x in b], autojunk=False)
    changes: list[dict[str, Any]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        changes.append({
            "operation": tag.upper(),
            "before_source_id": before["source_id"],
            "after_source_id": after["source_id"],
            "before_span": [i1, i2],
            "after_span": [j1, j2],
            "before_passage": _passage(a, i1) if i1 < i2 else None,
            "after_passage": _passage(b, j1) if j1 < j2 else None,
            "epistemic_status": "TEXTUAL_CHANGE_ONLY_NO_SCIENTIFIC_INFERENCE",
        })
        if len(changes) == _DELTA_LIMIT:
            break
    return {
        "family": before["family"],
        "before_key": before["key"],
        "after_key": after["key"],
        "before_source_id": before["source_id"],
        "after_source_id": after["source_id"],
        "before_paragraph_count": len(a),
        "after_paragraph_count": len(b),
        "changes": changes,
        "delta_status": "DIFFERENT" if changes else "IDENTICAL_TEXT",
    }


def _validate_source_id(source: dict[str, Any]) -> None:
    source_id = str(source["source_id"])
    url = str(source["source_url"])
    if source_id.startswith("drive:"):
        expected = "https://docs.google.com/document/d/" + source_id[6:]
        if not url.startswith(expected + "/"):
            raise ValueError(f"source identity/url mismatch: {source['key']}")
    elif not source_id or not url.startswith("https://"):
        raise ValueError(f"unverified source identity: {source['key']}")


def run_case(manifest_path: Path | str, storage_root: Path | str) -> dict[str, Any]:
    """Admit real local snapshots with original stable Drive IDs and held gates.

    The ledger is byte-stable on cold replay. SourceSnapshot registry writes
    deduplicate by stable (source_id, content_hash), not by human titles.
    """
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if manifest.get("schema") != "TRM074_COLD_CASE_V1":
        raise ValueError("unsupported talk case schema")
    case_id = str(manifest.get("case_id", ""))
    if not re.fullmatch(r"[A-Za-z0-9_-]{3,100}", case_id):
        raise ValueError("invalid case ID")
    if manifest.get("publication_send") != "DISALLOWED":
        raise ValueError("external sends must be disallowed")

    raw_sources = manifest.get("sources", [])
    if not raw_sources or len(raw_sources) > 200:
        raise ValueError("source list must be nonempty and bounded")
    by_key: dict[str, dict[str, Any]] = {}
    by_id: dict[str, dict[str, Any]] = {}
    texts: dict[str, str] = {}
    snapshots: list[dict[str, Any]] = []
    root = Path(storage_root)
    registry_root = ensure_registry_root(root)
    persisted = read_all("source_snapshots", base_dir=registry_root)
    existing_keys = {
        (r.get("source_id"), r.get("content_hash")) for r in persisted
    }
    for source in raw_sources:
        key = str(source["key"])
        if key in by_key:
            raise ValueError(f"duplicate artifact key: {key}")
        if source["kind"] not in VALID_KINDS:
            raise ValueError(f"unknown carrier kind: {key}")
        if source["author_state"] not in AUTHOR_STATES:
            raise ValueError(f"unknown author state: {key}")
        _validate_source_id(source)
        source_id = source["source_id"]
        snap, text = register_local_source(
            Path(source["local_path"]), role=SourceRole.BACKGROUND_RESEARCH,
            source_id=source_id,
        )
        if snap.extraction_status != "extracted":
            raise ValueError(f"source not fully read: {key}: {snap.extraction_status}")
        current = by_id.get(source_id)
        if current is not None:
            raise ValueError(
                f"duplicate source ID in one manifest: {current['key']} / {key}"
            )
        record = {
            "key": key,
            "family": source["family"],
            "kind": source["kind"],
            "version": source["version"],
            "author_state": source["author_state"],
            "source_id": source_id,
            "source_url": source["source_url"],
            "read_coverage": "FULL_FETCHED_TEXT_ONLY",
            "extraction_status": snap.extraction_status,
            "content_sha256": _digest(text),
            "content_characters": len(text),
            "snapshot_id": "snap_trm074_" + _digest(source_id + ":" + _digest(text))[:20],
        }
        texts[key] = text
        by_key[key] = record
        by_id[source_id] = record
        snapshots.append(record)
        r = snap.to_dict()
        r["snapshot_id"] = record["snapshot_id"]
        r["url"] = record["source_url"]
        r["read_coverage"] = record["read_coverage"]
        if (r["source_id"], r.get("content_hash")) not in existing_keys:
            append("source_snapshots", r, base_dir=registry_root)
            existing_keys.add((r["source_id"], r.get("content_hash")))

    edges: list[dict[str, str]] = []
    for e in manifest.get("version_edges", []):
        before, after = str(e["before"]), str(e["after"])
        if before not in by_key or after not in by_key:
            raise ValueError("version edge references unavailable source")
        if before == after or by_key[before]["family"] != by_key[after]["family"]:
            raise ValueError("invalid cross-family or self version edge")
        edges.append({"before": before, "after": after, "relation": str(e["relation"])})
    # Directed cycle check. Version edges are explicitly attested, never
    # reconstructed from timestamps, filenames or modifiedTime.
    adj = {key: [] for key in by_key}
    for edge in edges:
        adj[edge["before"]].append(edge["after"])
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(key: str) -> None:
        if key in visiting:
            raise ValueError("version genealogy contains a cycle")
        if key in visited:
            return
        visiting.add(key)
        for other in adj[key]:
            visit(other)
        visiting.remove(key)
        visited.add(key)

    for key in by_key:
        visit(key)

    deltas: list[dict[str, Any]] = []
    for before, after in manifest.get("delta_pairs", []):
        if before not in by_key or after not in by_key:
            raise ValueError("delta pair references unavailable source")
        if by_key[before]["family"] != by_key[after]["family"]:
            raise ValueError("cross-family textual delta prohibited")
        delta = _delta(by_key[before], by_key[after], texts[before], texts[after])
        if not delta["changes"]:
            raise ValueError(f"required delta missing: {before} -> {after}")
        deltas.append(delta)

    decisions: list[dict[str, Any]] = []
    for event in manifest.get("decision_events", []):
        target = str(event["artifact"])
        if target not in texts:
            raise ValueError("decision event references unavailable source")
        quote = str(event["quote"])
        index = texts[target].find(quote)
        if not quote or index < 0:
            raise ValueError(f"unanchored decision event: {target}")
        if event.get("role") == "USER":
            if target != "B_BASELINE" or by_key[target]["author_state"] != "USER_ACCEPTED_CONCEPTS_ONLY":
                raise ValueError("author approval cannot be broadened")
        decisions.append({
            "source_id": by_key[target]["source_id"],
            "actor_role": event["role"],
            "event_kind": event["kind"],
            "quote_exact": quote,
            "start_character": index,
            "end_character": index + len(quote),
            "authority_scope": event["authority_scope"],
        })
    accepted_ids = {
        x["source_id"] for x in snapshots
        if x["author_state"] == "USER_ACCEPTED_CONCEPTS_ONLY"
    }
    owner_decision_ids = {
        x["source_id"] for x in decisions if x["actor_role"] == "USER"
    }
    if not accepted_ids.issubset(owner_decision_ids):
        raise ValueError("accepted carrier lacks its own anchored author decision")

    families = sorted({s["family"] for s in snapshots if s["family"] != "CROSS"})
    held_candidates = [{
        "family": family,
        "entry_type": "ARTICLE_SEED_CANDIDATE_ENVELOPE",
        "source_ids": sorted(x["source_id"] for x in snapshots if x["family"] == family),
        "gate": "HOLD_ARTIKL_SCIENTIFIC_REVIEW_AND_AUTHOR_APPROVAL",
        "article_seed_created": False,
        "author_approved": False,
    } for family in families]

    ledger = {
        "schema": "TRM074_COLD_CASE_LEDGER_V1",
        "case_id": case_id,
        "source_snapshots": sorted(snapshots, key=lambda x: x["key"]),
        "version_edges": edges,
        "textual_deltas": deltas,
        "discussion_decisions": decisions,
        "missing_carriers": manifest.get("missing_carriers", []),
        "held_article_seed_envelopes": held_candidates,
        "world_ref": manifest.get("world"),
        "publication_send": "DISALLOWED",
        "readiness": "CORPUS_INTAKE_PARTIAL_REVIEW_HOLD",
        "backend": "existing Kairoskopion source_intake + source_snapshots JSONL",
    }
    out_dir = root / "talk_corpora" / case_id
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / "case_ledger.json"
    encoded = json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    tmp = dest.with_suffix(".tmp")
    tmp.write_bytes(encoded.encode("utf-8"))
    os.replace(tmp, dest)
    return {
        "case_id": case_id, "ledger_path": str(dest),
        "ledger_sha256": _digest(encoded),
        "source_count": len(snapshots),
        "new_source_snapshots": len(existing_keys) - len({
            (r.get("source_id"), r.get("content_hash")) for r in persisted
        }),
        "delta_families": sorted({x["family"] for x in deltas}),
        "held_candidates": len(held_candidates),
        "external_send": "DISABLED",
    }
