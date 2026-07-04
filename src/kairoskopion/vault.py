"""Enhanced vault: indexes, cross-linking, manifest, link validation.

The vault is a local projection of Kairoskopion state into human-readable
markdown cards. Registries remain the source of structured truth.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .persistence import ensure_storage_root, read_registry, list_registries

_MD_LINK_RE = re.compile(r'\[([^\]]+)\]\(([^)]+\.md)\)')

_VAULT_DIR = "vault"
_VAULT_SUBDIRS = (
    "articles", "venues", "fits", "risks", "compliance",
    "mismatches", "citations", "adapters", "submissions", "traces",
)


def _ensure_vault_root(storage_root: Path | str | None = None) -> Path:
    root = ensure_storage_root(storage_root) / _VAULT_DIR
    root.mkdir(parents=True, exist_ok=True)
    for sub in _VAULT_SUBDIRS:
        (root / sub).mkdir(exist_ok=True)
    return root


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _link(subdir: str, entity_id: str) -> str:
    return f"[{entity_id}]({subdir}/{entity_id}.md)"


def _safe_get(record: dict, *keys: str) -> str:
    for k in keys:
        v = record.get(k)
        if v:
            return str(v)
    return "?"


# ---------------------------------------------------------------------------
# Index generation
# ---------------------------------------------------------------------------

def _index_header(title: str, count: int) -> str:
    return (
        f"---\ntype: index\ngenerated_at: {_now_iso()}\n---\n\n"
        f"# {title}\n\n"
        f"**{count}** record(s)\n\n"
    )


def generate_articles_index(records: list[dict]) -> str:
    parts = [_index_header("Articles", len(records))]
    if records:
        parts.append("| ID | Title | Stage | Lifecycle | Unknowns |\n")
        parts.append("|-----|-------|-------|-----------|----------|\n")
        for r in records:
            aid = r.get("article_model_id", "?")
            parts.append(
                f"| {_link('articles', aid)} "
                f"| {_safe_get(r, 'title_current')} "
                f"| {_safe_get(r, 'article_stage')} "
                f"| {_safe_get(r, 'lifecycle_status')} "
                f"| {len(r.get('unknowns', []))} |\n"
            )
    return "".join(parts)


def generate_venues_index(records: list[dict]) -> str:
    parts = [_index_header("Venues", len(records))]
    if records:
        parts.append("| ID | Name | Type | Lifecycle | Unknowns |\n")
        parts.append("|-----|------|------|-----------|----------|\n")
        for r in records:
            vid = r.get("venue_model_id", "?")
            parts.append(
                f"| {_link('venues', vid)} "
                f"| {_safe_get(r, 'canonical_name')} "
                f"| {_safe_get(r, 'venue_type')} "
                f"| {_safe_get(r, 'lifecycle_status')} "
                f"| {len(r.get('unknowns', []))} |\n"
            )
    return "".join(parts)


def generate_fits_index(records: list[dict]) -> str:
    parts = [_index_header("Fit Assessments", len(records))]
    if records:
        parts.append("| ID | Label | Level | Article | Venue |\n")
        parts.append("|-----|-------|-------|---------|-------|\n")
        for r in records:
            fid = r.get("fit_assessment_id", "?")
            art_id = r.get("article_model_id", "?")
            ven_id = r.get("venue_model_id", "?")
            parts.append(
                f"| {_link('fits', fid)} "
                f"| {_safe_get(r, 'overall_label')} "
                f"| {_safe_get(r, 'assessment_level')} "
                f"| {_link('articles', art_id)} "
                f"| {_link('venues', ven_id)} |\n"
            )
    return "".join(parts)


def generate_citations_index(records: list[dict]) -> str:
    parts = [_index_header("Citation Ecology Reports", len(records))]
    if records:
        parts.append("| ID | Article | Venue | Gaps | Tasks | Lifecycle |\n")
        parts.append("|-----|---------|-------|------|-------|-----------|\n")
        for r in records:
            cid = r.get("citation_ecology_report_id", "?")
            parts.append(
                f"| {_link('citations', cid)} "
                f"| {_safe_get(r, 'article_model_id')} "
                f"| {_safe_get(r, 'venue_model_id')} "
                f"| {len(r.get('gaps', []))} "
                f"| {len(r.get('tasks', []))} "
                f"| {_safe_get(r, 'lifecycle_status')} |\n"
            )
    return "".join(parts)


def generate_traces_index(records: list[dict]) -> str:
    parts = [_index_header("Pipeline Runs", len(records))]
    if records:
        parts.append("| ID | Status | Started | Entities created |\n")
        parts.append("|-----|--------|---------|------------------|\n")
        for r in records:
            pid = r.get("pipeline_run_id", "?")
            parts.append(
                f"| {_link('traces', pid)} "
                f"| {_safe_get(r, 'status')} "
                f"| {_safe_get(r, 'started_at')} "
                f"| {len(r.get('created_entity_ids', []))} |\n"
            )
    return "".join(parts)


def generate_adapters_index(records: list[dict]) -> str:
    parts = [_index_header("Adapter Results", len(records))]
    if records:
        parts.append("| ID | Adapter | Query | Status | Records | Mock |\n")
        parts.append("|-----|---------|-------|--------|---------|------|\n")
        for r in records:
            aid = r.get("adapter_result_id", "?")
            parts.append(
                f"| `{aid}` "
                f"| {_safe_get(r, 'adapter_name')} "
                f"| {_safe_get(r, 'query')} "
                f"| {_safe_get(r, 'status')} "
                f"| {len(r.get('records', []))} "
                f"| {r.get('is_mock', True)} |\n"
            )
    return "".join(parts)


_INDEX_GENERATORS = {
    "articles": ("article_models", generate_articles_index),
    "venues": ("venue_models", generate_venues_index),
    "fits": ("fit_assessments", generate_fits_index),
    "citations": ("citation_ecology_reports", generate_citations_index),
    "traces": ("pipeline_runs", generate_traces_index),
    "adapters": ("adapter_results", generate_adapters_index),
}


def generate_root_index(counts: dict[str, int]) -> str:
    parts = [
        f"---\ntype: vault_root_index\ngenerated_at: {_now_iso()}\n---\n\n",
        "# Kairoskopion Vault\n\n",
        "Local projection of Kairoskopion state. Registries are the source of truth.\n\n",
        "## Sections\n\n",
    ]
    for subdir, count in sorted(counts.items()):
        if count > 0:
            parts.append(f"- [{subdir}]({subdir}/INDEX.md) — {count} record(s)\n")
        else:
            parts.append(f"- {subdir} — empty\n")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Cross-linking helpers for card generation
# ---------------------------------------------------------------------------

def _cross_links_section(title: str, links: list[tuple[str, str, str]]) -> str:
    """Generate a cross-links section. Each link is (subdir, entity_id, label)."""
    if not links:
        return ""
    md = f"\n## {title}\n\n"
    for subdir, eid, label in links:
        if eid and eid != "?" and eid != "None":
            md += f"- {label}: [{eid}](../{subdir}/{eid}.md)\n"
    return md


def enrich_article_card(card_md: str, data: dict) -> str:
    links = []
    ms_id = data.get("manuscript_id") or data.get("article_model_id")
    if ms_id:
        links.append(("articles", ms_id, "Manuscript"))
    return card_md + _cross_links_section("Related", links)


def enrich_fit_card(card_md: str, data: dict) -> str:
    links = [
        ("articles", data.get("article_model_id", ""), "Article"),
        ("venues", data.get("venue_model_id", ""), "Venue"),
        ("mismatches", data.get("mismatch_map_id", ""), "Mismatch Map"),
    ]
    return card_md + _cross_links_section("Related", links)


def enrich_citation_card(card_md: str, data: dict) -> str:
    links = [
        ("articles", data.get("article_model_id", ""), "Article"),
        ("venues", data.get("venue_model_id", ""), "Venue"),
    ]
    return card_md + _cross_links_section("Related", links)


def enrich_mismatch_card(card_md: str, data: dict) -> str:
    links = [
        ("fits", data.get("fit_assessment_id", ""), "Fit Assessment"),
    ]
    return card_md + _cross_links_section("Related", links)


def enrich_risk_card(card_md: str, data: dict) -> str:
    links = [
        ("articles", data.get("article_model_id", ""), "Article"),
        ("venues", data.get("venue_model_id", ""), "Venue"),
    ]
    return card_md + _cross_links_section("Related", links)


def enrich_compliance_card(card_md: str, data: dict) -> str:
    links = [
        ("articles", data.get("article_model_id", ""), "Article"),
        ("venues", data.get("venue_model_id", ""), "Venue"),
    ]
    return card_md + _cross_links_section("Related", links)


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

def generate_manifest(
    vault_root: Path,
    storage_root: Path,
) -> dict[str, Any]:
    """Generate machine-readable vault manifest."""
    cards: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    warnings: list[str] = []

    for subdir in vault_root.iterdir():
        if not subdir.is_dir():
            continue
        name = subdir.name
        md_files = list(subdir.glob("*.md"))
        non_index = [f for f in md_files if f.name != "INDEX.md"]
        counts[name] = len(non_index)
        for f in non_index:
            entity_id = f.stem
            cards.append({
                "path": str(f.relative_to(vault_root)),
                "entity_id": entity_id,
                "entity_type": name,
            })

    return {
        "generated_at": _now_iso(),
        "storage_root": str(storage_root),
        "vault_root": str(vault_root),
        "counts": counts,
        "cards": cards,
        "total_cards": len(cards),
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Link validation
# ---------------------------------------------------------------------------

def validate_vault_links(vault_root: Path) -> list[dict[str, Any]]:
    """Validate internal markdown links in vault cards.

    Returns a list of warning dicts for broken links.
    Does not crash on missing targets — reports as warnings.
    """
    warnings: list[dict[str, Any]] = []
    md_files = list(vault_root.rglob("*.md"))

    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        for match in _MD_LINK_RE.finditer(content):
            link_text, link_target = match.group(1), match.group(2)
            if link_target.startswith("http"):
                continue
            target_path = (md_file.parent / link_target).resolve()
            if not target_path.exists():
                warnings.append({
                    "source_file": str(md_file.relative_to(vault_root)),
                    "link_text": link_text,
                    "link_target": link_target,
                    "issue": "target_not_found",
                })

    return warnings


# ---------------------------------------------------------------------------
# Full vault generation
# ---------------------------------------------------------------------------

def write_vault_indexes(storage_root: Path | str) -> dict[str, Path]:
    """Generate and write all vault index files and manifest."""
    storage = Path(storage_root)
    vault_root = _ensure_vault_root(storage)
    written: dict[str, Path] = {}

    # Ensure adapters subdir exists
    adapters_dir = vault_root / "adapters"
    adapters_dir.mkdir(exist_ok=True)

    counts: dict[str, int] = {}

    for subdir_name, (registry_name, generator) in _INDEX_GENERATORS.items():
        records = read_registry(registry_name, storage_root=storage)
        index_md = generator(records)
        index_path = vault_root / subdir_name / "INDEX.md"
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(index_md, encoding="utf-8")
        written[f"{subdir_name}_index"] = index_path
        counts[subdir_name] = len(records)

    # Subdirs without indexes
    for sub in ("risks", "compliance", "mismatches", "submissions"):
        sub_path = vault_root / sub
        sub_path.mkdir(exist_ok=True)
        card_count = len([f for f in sub_path.glob("*.md") if f.name != "INDEX.md"])
        counts[sub] = card_count

    # Root index
    root_md = generate_root_index(counts)
    root_path = vault_root / "INDEX.md"
    root_path.write_text(root_md, encoding="utf-8")
    written["root_index"] = root_path

    # Manifest
    manifest = generate_manifest(vault_root, storage)
    manifest_path = vault_root / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    written["manifest"] = manifest_path

    return written
