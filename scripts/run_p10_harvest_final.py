#!/usr/bin/env python3
"""P10 Operational Harvest — Final Pass.

Re-runs the verification gate and review-packet export on the existing
P10 harvest data (87 provisional venue records from OpenAlex + DOAJ).
Produces:
  - acquisition tasks for unresolved source needs
  - verification decisions with explicit verdicts
  - review packets for owner inspection
  - provisional candidate export (schema-valid, not accepted truth)
  - operator smoke report data

Does NOT re-query live adapters (uses existing results).
Does NOT auto-promote records.
Does NOT fabricate sources.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kairoskopion.registry.models import VenueRegistryRecord, EvidenceRef
from kairoskopion.registry.services import RegistryHub
from kairoskopion.services.verification_gate import (
    verify_registry, verify_record, summarize_verification,
)
from kairoskopion.services.review_packet_exporter import (
    build_review_packet, export_markdown, export_jsonl, export_tsv,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


HARVEST_DIR = Path("data/seed_registry/education_ai_russia/p10_harvest")
OUTPUT_DIR = HARVEST_DIR


DOMAIN_KEYWORDS = {
    "tier1_ru_education": [
        "образовани", "педагог", "высш", "россий",
        "vysshee", "pedagogical", "education in russia",
        "rudn", "professional education", "higher education in russia",
    ],
    "tier2_ai_education": [
        "artificial intelligence", "ai in education", "ai education",
        "machine learning education", "intelligent tutoring",
    ],
    "tier3_edtech": [
        "educational technology", "edtech", "e-learning",
        "digital education", "online learning", "blended learning",
        "technology pedagogy", "internet and higher education",
    ],
    "tier4_higher_ed": [
        "higher education", "university", "studies in higher",
        "research in higher", "journal of higher",
    ],
}

NOISE_KEYWORDS = [
    "clinical", "medical", "кавказолог", "здравоохран",
    "graduate medical", "sport pedagogy", "physical education",
    "phenomenology", "internal medicine",
]


def classify_venue(name: str) -> str:
    name_lower = name.lower()
    for kw in NOISE_KEYWORDS:
        if kw.lower() in name_lower:
            return "noise"
    for tier, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in name_lower:
                return tier
    return "unclassified"


def load_provisional_records() -> list[dict]:
    path = HARVEST_DIR / "provisional_venue_records.jsonl"
    if not path.exists():
        print(f"ERROR: {path} not found")
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def build_acquisition_tasks() -> list[dict]:
    tasks = []
    task_defs = [
        {
            "task_id": "at_p10_sn02_crossref_issn",
            "source_need": "SN-02",
            "description": "Verify ISSNs of Tier 1/2 venues via Crossref lookup",
            "target_authority": "crossref",
            "acquisition_route": "crossref_venue_adapter.lookup_venue(issn)",
            "expected_provenance": "crossref_api",
            "access_status": "free_api",
            "priority": "high",
            "completion_criterion": "Each Tier 1/2 venue ISSN checked against Crossref",
            "status": "open",
        },
        {
            "task_id": "at_p10_sn03_vak_pedagogy",
            "source_need": "SN-03",
            "description": "Corroborate ru-vak-pedagogy seed against VAK passport list",
            "target_authority": "vak_journal_list",
            "acquisition_route": "manual_web_lookup",
            "expected_provenance": "vak_passport_web",
            "access_status": "public_web",
            "priority": "high",
            "completion_criterion": "VAK code 5.8.1 confirmed in official passport",
            "status": "open",
        },
        {
            "task_id": "at_p10_sn03_vak_ped_psych",
            "source_need": "SN-03",
            "description": "Corroborate ru-pedagogical-psychology seed against VAK passport list",
            "target_authority": "vak_journal_list",
            "acquisition_route": "manual_web_lookup",
            "expected_provenance": "vak_passport_web",
            "access_status": "public_web",
            "priority": "high",
            "completion_criterion": "VAK code 5.3.4 confirmed in official passport",
            "status": "open",
        },
        {
            "task_id": "at_p10_sn04_scimago",
            "source_need": "SN-04",
            "description": "Retrieve SJR rankings for Tier 1-3 venues from ScimagoJR",
            "target_authority": "scimago_jr",
            "acquisition_route": "manual_web_scraping",
            "expected_provenance": "scimagojr_web",
            "access_status": "public_web",
            "priority": "medium",
            "completion_criterion": "SJR quartile for each Tier 1-3 venue with Scopus indexing",
            "status": "blocked_manual_only",
        },
        {
            "task_id": "at_p10_sn04_elibrary",
            "source_need": "SN-04",
            "description": "Retrieve RSCI impact factors from eLibrary.ru",
            "target_authority": "elibrary_ru",
            "acquisition_route": "elibrary_api",
            "expected_provenance": "elibrary_api",
            "access_status": "blocked_needs_key",
            "priority": "medium",
            "completion_criterion": "RSCI IF for each Tier 1 venue",
            "status": "blocked_needs_key",
        },
        {
            "task_id": "at_p10_sn05_cyberleninka",
            "source_need": "SN-05",
            "description": "Search CyberLeninka for RU education journals missing from OpenAlex/DOAJ",
            "target_authority": "cyberleninka",
            "acquisition_route": "manual_url_search",
            "expected_provenance": "cyberleninka_web",
            "access_status": "public_web",
            "priority": "medium",
            "completion_criterion": "3 core education terms searched, results compared to existing records",
            "status": "open",
        },
    ]
    for t in task_defs:
        t["created_at"] = _now_iso()
        tasks.append(t)
    return tasks


def run_verification_on_records(records: list[dict], tmp_dir: Path) -> tuple[list, dict]:
    hub = RegistryHub(data_dir=tmp_dir)
    venue_reg = hub._get_registry("venue")

    for rec_dict in records:
        evidence_refs = []
        for er in rec_dict.get("evidence_refs", []):
            evidence_refs.append(EvidenceRef(
                source_type=er.get("source_type", "unknown"),
                source_id=er.get("source_id", ""),
                evidence_status=er.get("evidence_status", "UNKNOWN"),
                retrieval_date=er.get("retrieval_date", ""),
                notes=er.get("notes", ""),
            ))
        rec = VenueRegistryRecord(
            venue_id=rec_dict.get("venue_id", ""),
            canonical_name=rec_dict.get("canonical_name", ""),
            aliases=rec_dict.get("aliases", []),
            issn=rec_dict.get("issn"),
            publisher=rec_dict.get("publisher"),
            official_urls=rec_dict.get("official_urls", []),
            source_status="provisional",
            review_status="pending",
            evidence_refs=evidence_refs,
            provenance=rec_dict.get("provenance", ""),
        )
        venue_reg.add_provisional(rec, evidence_refs=evidence_refs)

    decisions = verify_registry(hub, no_paid_api=True)
    summary = summarize_verification(decisions)
    return decisions, summary


def main():
    print("=" * 60)
    print("P10 OPERATIONAL HARVEST — FINAL PASS")
    print(f"Date: {_now_iso()}")
    print("=" * 60)

    # 1. Load existing records
    print("\n[1] Loading existing provisional records...")
    records = load_provisional_records()
    print(f"  Loaded: {len(records)} records")

    # 2. Classify by domain relevance
    print("\n[2] Classifying by domain relevance...")
    classifications = {}
    tier_counts = {}
    for rec in records:
        name = rec.get("canonical_name", "")
        tier = classify_venue(name)
        classifications[rec.get("venue_id", name)] = {
            "canonical_name": name,
            "issn": rec.get("issn"),
            "tier": tier,
        }
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    for tier, count in sorted(tier_counts.items()):
        print(f"  {tier}: {count}")

    # 3. Generate acquisition tasks
    print("\n[3] Generating acquisition tasks...")
    tasks = build_acquisition_tasks()
    tasks_path = OUTPUT_DIR / "acquisition_tasks_final.json"
    with open(tasks_path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)
    print(f"  Generated: {len(tasks)} tasks -> {tasks_path}")

    task_counts = {"total": len(tasks), "open": 0, "blocked": 0}
    for t in tasks:
        if "blocked" in t.get("status", ""):
            task_counts["blocked"] += 1
        else:
            task_counts["open"] += 1
    print(f"  Open: {task_counts['open']}, Blocked: {task_counts['blocked']}")

    # 4. Run verification gate
    print("\n[4] Running verification gate...")
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        decisions, summary = run_verification_on_records(records, Path(tmp))

    print(f"  Total decisions: {summary['total']}")
    for v, c in summary["verdicts"].items():
        if c > 0:
            print(f"    {v}: {c}")

    vdec_path = OUTPUT_DIR / "verification_decisions_final.jsonl"
    with open(vdec_path, "w", encoding="utf-8") as f:
        for d in decisions:
            f.write(json.dumps(d.to_dict(), ensure_ascii=False) + "\n")
    print(f"  Saved: {vdec_path}")

    # 5. Build review packet
    print("\n[5] Building review packet...")
    import tempfile as tf2
    with tf2.TemporaryDirectory() as tmp2:
        hub2 = RegistryHub(data_dir=Path(tmp2))
        venue_reg2 = hub2._get_registry("venue")
        for rec_dict in records:
            evidence_refs = []
            for er in rec_dict.get("evidence_refs", []):
                evidence_refs.append(EvidenceRef(
                    source_type=er.get("source_type", "unknown"),
                    source_id=er.get("source_id", ""),
                    evidence_status=er.get("evidence_status", "UNKNOWN"),
                    retrieval_date=er.get("retrieval_date", ""),
                ))
            rec = VenueRegistryRecord(
                venue_id=rec_dict.get("venue_id", ""),
                canonical_name=rec_dict.get("canonical_name", ""),
                issn=rec_dict.get("issn"),
                publisher=rec_dict.get("publisher"),
                source_status="provisional",
                review_status="pending",
                evidence_refs=evidence_refs,
                provenance=rec_dict.get("provenance", ""),
            )
            venue_reg2.add_provisional(rec, evidence_refs=evidence_refs)

        gaps = [
            "Education/AI venue universe bootstrapped from free adapter queries only — no eLibrary.ru, no RSCI, no Scopus/WoS",
            "ISSN cross-verification via Crossref not yet executed (SN-02)",
            "Discipline seeds remain llm_draft — VAK corroboration pending (SN-03)",
            "Venue metrics entirely absent — requires Scopus/ScimagoJR/WoS (SN-04, blocked)",
            "Russian-language venue gap — CyberLeninka search not yet executed (SN-05)",
            "Venue sections not analyzed — requires per-venue evidence packs (SN-06, deferred)",
        ]
        packet = build_review_packet(hub2, gaps=gaps, no_paid_api=True)
        packet.verification_decisions = [d.to_dict() for d in decisions]
        packet.verification_summary = summary

    md_path = OUTPUT_DIR / "review_packet_final.md"
    jsonl_path = OUTPUT_DIR / "review_packet_final.jsonl"
    tsv_path = OUTPUT_DIR / "review_packet_final.tsv"

    md_path.write_text(export_markdown(packet), encoding="utf-8")
    jsonl_path.write_text(export_jsonl(packet), encoding="utf-8")
    tsv_path.write_text(export_tsv(packet), encoding="utf-8")
    print(f"  Review packet exported: MD + JSONL + TSV")

    # 6. Produce provisional candidate export
    print("\n[6] Producing provisional candidate export...")
    registry_output = []
    for rec in records:
        tier = classifications.get(rec.get("venue_id"), {}).get("tier", "unclassified")
        entry = {
            "venue_id": rec.get("venue_id"),
            "canonical_name": rec.get("canonical_name"),
            "issn": rec.get("issn"),
            "publisher": rec.get("publisher"),
            "source_status": "provisional",
            "review_status": "pending",
            "domain_tier": tier,
            "evidence_refs": rec.get("evidence_refs", []),
            "provenance": rec.get("provenance"),
            "harvest_pass": "p10_final_2026-07-09",
        }
        registry_output.append(entry)

    registry_path = OUTPUT_DIR / "provisional_candidate_export.jsonl"
    with open(registry_path, "w", encoding="utf-8") as f:
        for entry in registry_output:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    accepted = sum(1 for r in registry_output if r["source_status"] == "accepted")
    provisional = sum(1 for r in registry_output if r["source_status"] == "provisional")
    print(f"  Provisional candidates: {len(registry_output)} records")
    print(f"    Accepted: {accepted}")
    print(f"    Provisional: {provisional}")

    # 7. Classification report
    class_path = OUTPUT_DIR / "domain_classification.json"
    with open(class_path, "w", encoding="utf-8") as f:
        json.dump({
            "date": _now_iso(),
            "tier_counts": tier_counts,
            "classifications": classifications,
        }, f, indent=2, ensure_ascii=False)
    print(f"  Classification: {class_path}")

    # 8. Summary
    harvest_final = {
        "harvest_id": "p10_education_ai_final_2026-07-09",
        "date": _now_iso(),
        "base_commit": "5ebbe1a",
        "original_harvest": "p10_education_ai_2026-06-27",
        "provisional_records": len(records),
        "domain_classification": tier_counts,
        "acquisition_tasks": task_counts,
        "verification_summary": summary,
        "provisional_candidate_export": {
            "total": len(registry_output),
            "accepted": accepted,
            "provisional": provisional,
        },
        "review_packets_exported": ["MD", "JSONL", "TSV"],
        "gaps": gaps,
        "constraints": {
            "no_paid_api": True,
            "no_llm_promotion": True,
            "no_auto_promote": True,
            "no_fabricated_sources": True,
        },
    }

    summary_path = OUTPUT_DIR / "harvest_summary_final.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(harvest_final, f, indent=2, ensure_ascii=False)
    print(f"\n  Final summary: {summary_path}")

    print("\n" + "=" * 60)
    print("P10 FINAL PASS COMPLETE")
    print("=" * 60)

    return harvest_final


if __name__ == "__main__":
    main()
