"""Self-seeding registry workflow (P7 Bootstrap).

Orchestrates existing Kairoskopion primitives to populate a registry
from an article + domain scope target. No manual Claude-curated facts.
Every record is source-backed or marked unknown/provisional/acquisition_needed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from ..agents.article_modeler import ArticleModelerAgent
from ..agents.contract import AgentInput
from ..ids import pipeline_run_id as _new_run_id
from ..registry.models import (
    SourceAcquisitionTask,
    SourcePacket,
)
from ..registry.services import RegistryHub
from .external_source_adapters import ExternalAdapterRegistry
from .source_authority_registry import (
    SourceAuthorityDiscoveryTask,
    SourceAuthorityStore,
    SourceAuthoritySufficiencyEvaluator,
    SufficiencyResult,
)


# ---------------------------------------------------------------------------
# Config / Result
# ---------------------------------------------------------------------------

@dataclass
class SeedWorkflowConfig:
    article_text: str
    article_source_ref: str = "local_file"
    domain_target: str = "education_ai_russia"
    target_language: str = "ru"
    target_country: str = "RU"
    target_zones: list[str] = field(default_factory=list)
    target_archetypes: list[str] = field(default_factory=list)
    no_live_llm: bool = True
    no_paid_api: bool = True
    output_dir: Path | None = None


@dataclass
class SeedWorkflowResult:
    run_id: str = field(default_factory=_new_run_id)
    authority_coverage: dict[str, Any] | None = None
    source_authority_tasks: list[dict[str, Any]] = field(default_factory=list)
    article_archetype: dict[str, Any] | None = None
    discipline_lookups: list[dict[str, Any]] = field(default_factory=list)
    acquisition_tasks_created: list[dict[str, Any]] = field(default_factory=list)
    blocked_on_authority: list[dict[str, Any]] = field(default_factory=list)
    source_packets_created: list[dict[str, Any]] = field(default_factory=list)
    provisional_records: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    venue_universe: list[dict[str, Any]] = field(default_factory=list)
    shortlist: list[dict[str, Any]] = field(default_factory=list)
    deep_venue_tasks: list[dict[str, Any]] = field(default_factory=list)
    available_adapters: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------

class SeedRegistryWorkflow:
    """Registry-first self-seeding workflow.

    Uses existing RegistryHub, agents, and stores.  Creates only
    provisional records backed by source evidence or acquisition tasks
    for missing data.
    """

    def __init__(
        self,
        hub: RegistryHub,
        authority_store: SourceAuthorityStore | None = None,
        adapter_registry: ExternalAdapterRegistry | None = None,
    ) -> None:
        self._hub = hub
        self._authority_store = authority_store or SourceAuthorityStore()
        self._adapter_registry = adapter_registry or ExternalAdapterRegistry()

    def run(self, config: SeedWorkflowConfig) -> SeedWorkflowResult:
        result = SeedWorkflowResult()

        # Stage 0: Authority sufficiency evaluation
        self._evaluate_authority(config, result)

        # Stage 0b: Record available adapters
        result.available_adapters = [
            a.adapter_id for a in self._adapter_registry.list_enabled()
        ]

        # Stage 1: Article archetype from deterministic ArticleModeler
        result.article_archetype = self._build_article_archetype(
            config.article_text,
            config.article_source_ref,
            result,
        )

        # Stage 2: Discipline/zone lookup
        self._lookup_disciplines(config, result)

        # Stage 3: Framework lookup
        self._lookup_frameworks(config, result)

        # Stage 4: Venue search (authority-aware)
        self._search_venues(config, result)

        # Stage 5-6: Source packet ingestion + provisional record creation
        # (Driven by source files if available — no auto-invention)

        # Stage 7: Venue universe assembly
        self._assemble_venue_universe(result)

        # Stage 8: Metric/classification check
        self._check_metrics(result)

        # Stage 9: Shortlist generation
        self._build_shortlist(config, result)

        # Stage 10: Deep venue model tasks
        self._create_deep_venue_tasks(result)

        # Stage 11: Gap report
        self._compile_gaps(config, result)

        # Persist
        if config.output_dir:
            self._write_outputs(config.output_dir, result)

        return result

    # -- Stage 0 --------------------------------------------------------

    def _evaluate_authority(
        self,
        config: SeedWorkflowConfig,
        result: SeedWorkflowResult,
    ) -> None:
        evaluator = SourceAuthoritySufficiencyEvaluator(self._authority_store)
        suff = evaluator.evaluate(
            target_country=config.target_country,
            target_domain=config.domain_target,
            publication_task_type="venue_discovery",
            desired_outputs=["metrics", "deep_model"],
        )
        result.authority_coverage = suff.to_dict()

        for task_info in suff.tasks_to_create:
            available = self._adapter_registry.suggest_for_authority_type(
                task_info["missing_authority_type"],
            )
            task = SourceAuthorityDiscoveryTask(
                target_country=config.target_country,
                target_domain=config.domain_target,
                missing_authority_type=task_info["missing_authority_type"],
                reason=task_info["reason"],
                search_queries=task_info.get("search_queries", []),
                suggested_connectors=available or task_info.get("suggested_connectors", []),
            )
            result.source_authority_tasks.append(task.to_dict())

        result.warnings.extend(suff.warnings)

    # -- Stage 1 --------------------------------------------------------

    def _build_article_archetype(
        self,
        text: str,
        source_ref: str,
        result: SeedWorkflowResult,
    ) -> dict[str, Any]:
        agent = ArticleModelerAgent()
        inp = AgentInput(
            operation_id=result.run_id,
            agent_role_id="article_modeler",
            source_refs=[source_ref],
            raw_text=text,
        )
        out = agent.execute_deterministic(inp)
        article_dict = out.output_entity

        archetype = {
            "archetype_id": f"archetype_{result.run_id[:8]}",
            "title_family": article_dict.get("title", "unknown"),
            "article_object": article_dict.get("research_object", "unknown"),
            "claim_family": article_dict.get("main_claims", []),
            "genre": article_dict.get("genre", "unknown"),
            "method_evidence_regime": article_dict.get("methods", []),
            "citation_ecology": {
                "references_detected": bool(article_dict.get("references", [])),
            },
            "likely_zones": [],
            "unlikely_zones": [],
            "fit_risks": [],
            "rewrite_requirements": [],
            "source_article_ref": source_ref,
            "provenance": "deterministic_article_modeler",
            "confidence": out.confidence or "low",
            "status": "draft",
        }

        if out.unknowns:
            archetype["unknowns"] = out.unknowns
        if out.warnings:
            archetype["warnings"] = out.warnings

        needs_llm = []
        if archetype["genre"] == "unknown":
            needs_llm.append("genre_detection")
        if not archetype["claim_family"]:
            needs_llm.append("claim_extraction")
        if not archetype["method_evidence_regime"]:
            needs_llm.append("method_detection")
        if needs_llm:
            archetype["needs_llm_for"] = needs_llm
            result.gaps.append(
                f"Article archetype incomplete — needs LLM for: {', '.join(needs_llm)}"
            )

        return archetype

    # -- Stage 2 --------------------------------------------------------

    def _lookup_disciplines(
        self,
        config: SeedWorkflowConfig,
        result: SeedWorkflowResult,
    ) -> None:
        queries = list(config.target_zones) if config.target_zones else []
        if not queries:
            archetype = result.article_archetype or {}
            title = archetype.get("title_family", "")
            if title and title != "unknown":
                queries.append(title[:80])

        if not queries:
            result.gaps.append("No discipline queries available — no zones specified, no title extracted")
            return

        for q in queries:
            reg = self._hub.disciplines()
            hits = reg.search(q)
            lookup_result = {
                "query": q,
                "hits": len(hits),
                "status": "found" if hits else "miss",
            }
            if hits:
                lookup_result["records"] = [
                    {"discipline_id": h.discipline_id, "display_names": h.display_names}
                    for h in hits[:5]
                ]
            else:
                task = SourceAcquisitionTask(
                    task_type="discipline_lookup",
                    query=q,
                    reason=f"No discipline record found for '{q}'",
                    target_sources=["vak", "oecd_ford", "openalex"],
                    created_by_agent="seed_workflow",
                )
                self._hub.tasks.add(task)
                result.acquisition_tasks_created.append(task.to_dict())
                lookup_result["task_id"] = task.task_id

            result.discipline_lookups.append(lookup_result)

    # -- Stage 3 --------------------------------------------------------

    def _lookup_frameworks(
        self,
        config: SeedWorkflowConfig,
        result: SeedWorkflowResult,
    ) -> None:
        archetype = result.article_archetype or {}
        title = archetype.get("title_family", "")
        if not title or title == "unknown":
            return

        reg = self._hub.epistemic_frameworks()
        hits = reg.search(title[:60])
        if not hits:
            result.gaps.append("No epistemic framework records found for article domain")

    # -- Stage 4 --------------------------------------------------------

    def _search_venues(
        self,
        config: SeedWorkflowConfig,
        result: SeedWorkflowResult,
    ) -> None:
        reg = self._hub.venues()

        queries = list(config.target_zones) if config.target_zones else []
        if not queries:
            queries = [config.domain_target]

        total_hits = 0
        for q in queries:
            hits = reg.search(q)
            total_hits += len(hits)
            for h in hits:
                result.venue_universe.append({
                    "venue_id": h.venue_id,
                    "canonical_name": h.canonical_name,
                    "source_status": h.source_status,
                    "found_by": "registry_search",
                    "query": q,
                })

        if total_hits == 0:
            for q in queries:
                task = SourceAcquisitionTask(
                    task_type="venue_discovery",
                    query=q,
                    reason=f"No venue records for domain '{q}' — registry empty",
                    target_sources=[
                        "elibrary_ru", "vak_list", "openalex",
                        "crossref", "doaj", "scopus_sjr",
                    ],
                    created_by_agent="seed_workflow",
                    priority="high",
                )
                self._hub.tasks.add(task)
                result.acquisition_tasks_created.append(task.to_dict())

            result.gaps.append(
                f"Venue registry empty for domain '{config.domain_target}' — "
                f"{len(queries)} acquisition tasks created"
            )

    # -- Stage 7 --------------------------------------------------------

    def _assemble_venue_universe(self, result: SeedWorkflowResult) -> None:
        if not result.venue_universe:
            result.warnings.append(
                "Venue universe is empty — only acquisition tasks exist. "
                "Populate registry with source-backed records first."
            )

    # -- Stage 8 --------------------------------------------------------

    def _has_authority(self, authority_type: str) -> bool:
        cov = getattr(self, "_authority_coverage_types", None)
        if cov is None:
            usable = self._authority_store.list_all()
            self._authority_coverage_types = {
                a.authority_type for a in usable
                if a.source_status in ("accepted", "provisional")
            }
            cov = self._authority_coverage_types
        return authority_type in cov

    def _check_metrics(self, result: SeedWorkflowResult) -> None:
        metrics_reg = self._hub.venue_metrics()
        all_metrics = metrics_reg.list_all()
        if not all_metrics:
            if not self._has_authority("metric_source"):
                result.blocked_on_authority.append({
                    "task_type": "venue_metrics",
                    "reason": "No metric source authority — cannot create metric acquisition tasks",
                    "blocked_on": "metric_source",
                })
            result.gaps.append(
                "No VenueMetricRecords in registry — "
                "Q1/Q2 ranking not possible without source-backed metrics"
            )

    # -- Stage 9 --------------------------------------------------------

    def _build_shortlist(
        self,
        config: SeedWorkflowConfig,
        result: SeedWorkflowResult,
    ) -> None:
        accepted_venues = [
            v for v in result.venue_universe
            if v.get("source_status") in ("canonical", "accepted")
        ]
        provisional_venues = [
            v for v in result.venue_universe
            if v.get("source_status") in ("provisional", "provisional_with_warning")
        ]

        for v in accepted_venues:
            result.shortlist.append({
                **v,
                "shortlist_reason": "accepted_in_registry",
                "evidence_strength": "registry_accepted",
            })

        for v in provisional_venues:
            result.shortlist.append({
                **v,
                "shortlist_reason": "provisional_in_registry",
                "evidence_strength": "provisional",
                "warning": "Not yet reviewed — evidence may be insufficient",
            })

        if len(result.shortlist) < 5:
            shortage = 5 - len(result.shortlist)
            result.gaps.append(
                f"Shortlist has {len(result.shortlist)} venues — "
                f"shortage of {shortage} vs minimum 5. "
                f"Populate registry with source-backed venue records."
            )

    # -- Stage 10 -------------------------------------------------------

    def _create_deep_venue_tasks(self, result: SeedWorkflowResult) -> None:
        has_editorial = self._has_authority("editorial_board_source")
        has_archive = self._has_authority("journal_archive_source")

        for v in result.shortlist:
            vid = v.get("venue_id", "unknown")
            task = SourceAcquisitionTask(
                task_type="deep_venue_model",
                query=v.get("canonical_name", vid),
                reason=f"Build deep VenueModel for shortlisted venue '{vid}'",
                target_sources=[
                    "official_site", "author_guidelines",
                    "editorial_board", "archive",
                    "elibrary_ru", "scopus_sjr",
                ],
                created_by_agent="seed_workflow",
                related_record_id=vid,
            )
            self._hub.tasks.add(task)
            task_dict = task.to_dict()
            result.deep_venue_tasks.append(task_dict)

            if not has_editorial:
                result.blocked_on_authority.append({
                    "task_type": "editor_background",
                    "venue_id": vid,
                    "reason": "No editorial_board_source authority",
                    "blocked_on": "editorial_board_source",
                })
            if not has_archive:
                result.blocked_on_authority.append({
                    "task_type": "corpus_analysis",
                    "venue_id": vid,
                    "reason": "No journal_archive_source authority",
                    "blocked_on": "journal_archive_source",
                })

    # -- Stage 11 -------------------------------------------------------

    def _compile_gaps(
        self,
        config: SeedWorkflowConfig,
        result: SeedWorkflowResult,
    ) -> None:
        if config.no_live_llm:
            result.warnings.append(
                "Running in no-live-LLM mode — semantic analysis deferred"
            )

        archetype = result.article_archetype or {}
        if archetype.get("needs_llm_for"):
            result.gaps.append(
                "Article archetype needs LLM for full semantic extraction"
            )

        if result.source_authority_tasks:
            result.gaps.append(
                f"{len(result.source_authority_tasks)} source authority discovery "
                f"tasks — resolve before factual acquisition"
            )

        if result.blocked_on_authority:
            result.warnings.append(
                f"{len(result.blocked_on_authority)} factual tasks blocked on "
                f"missing source authorities"
            )

        open_tasks = self._hub.tasks.list_open()
        if open_tasks:
            result.warnings.append(
                f"{len(open_tasks)} open acquisition tasks — "
                f"resolve to populate registry"
            )

    # -- Persistence ----------------------------------------------------

    def _write_outputs(self, output_dir: Path, result: SeedWorkflowResult) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        reports_dir = output_dir / "reports"
        reports_dir.mkdir(exist_ok=True)

        if result.article_archetype:
            arch_dir = output_dir / "article_archetypes"
            arch_dir.mkdir(exist_ok=True)
            (arch_dir / f"{result.article_archetype['archetype_id']}.json").write_text(
                json.dumps(result.article_archetype, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        if result.acquisition_tasks_created:
            tasks_dir = output_dir / "acquisition_tasks"
            tasks_dir.mkdir(exist_ok=True)
            (tasks_dir / "open_tasks.json").write_text(
                json.dumps(result.acquisition_tasks_created, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        if result.shortlist:
            sl_dir = output_dir / "shortlists"
            sl_dir.mkdir(exist_ok=True)
            (sl_dir / "top_q1_q2_by_zone.json").write_text(
                json.dumps(result.shortlist, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        if result.authority_coverage:
            (reports_dir / "authority_coverage.json").write_text(
                json.dumps(result.authority_coverage, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        if result.source_authority_tasks:
            tasks_dir = output_dir / "acquisition_tasks"
            tasks_dir.mkdir(exist_ok=True)
            (tasks_dir / "authority_discovery_tasks.json").write_text(
                json.dumps(result.source_authority_tasks, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        if result.blocked_on_authority:
            (reports_dir / "blocked_on_authority.json").write_text(
                json.dumps(result.blocked_on_authority, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        # Gap report
        gap_lines = ["# Seed Workflow — Gaps Report\n"]
        gap_lines.append(f"**Run ID:** {result.run_id}\n")
        if result.gaps:
            gap_lines.append("## Gaps\n")
            for g in result.gaps:
                gap_lines.append(f"- {g}")
        else:
            gap_lines.append("No gaps detected.\n")
        if result.warnings:
            gap_lines.append("\n## Warnings\n")
            for w in result.warnings:
                gap_lines.append(f"- {w}")
        (reports_dir / "gaps.md").write_text(
            "\n".join(gap_lines), encoding="utf-8",
        )

        # Full result
        (reports_dir / "workflow_run_report.json").write_text(
            json.dumps(result.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# Convenience: ingest a local text file as source packet
# ---------------------------------------------------------------------------

def ingest_local_file_as_packet(
    hub: RegistryHub,
    file_path: Path,
    *,
    packet_type: str = "article_text",
    source_type: str = "local_file",
) -> SourcePacket:
    """Create a SourcePacket from a local file (text excerpt)."""
    text = file_path.read_text(encoding="utf-8")
    excerpt = text[:2000] if len(text) > 2000 else text
    packet = SourcePacket(
        packet_type=packet_type,
        source_type=source_type,
        source_id=str(file_path),
        title=file_path.stem,
        excerpt=excerpt,
        adapter_name="local_file_ingest",
        confidence="high",
        evidence_status="user_provided",
    )
    hub.packets.add(packet)
    return packet
