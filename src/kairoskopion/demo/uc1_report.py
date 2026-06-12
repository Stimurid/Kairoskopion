"""Generate the UC-1 Demo Report (Markdown) from a demo run result."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .uc1_runner import UC1DemoResult


def generate_uc1_demo_report(result: UC1DemoResult) -> str:
    """Generate a Markdown report summarizing the UC-1 demo run."""
    lines: list[str] = []
    _header(lines, result)
    _pack_summary(lines, result)
    _workflow_summary(lines, result)
    _step_details(lines, result)
    _entity_summary(lines, result)
    _evidence_gaps(lines, result)
    _footer(lines, result)
    return "\n".join(lines)


def _header(lines: list[str], result: UC1DemoResult) -> None:
    lines.append("# UC-1 Demo Report")
    lines.append("")
    status_emoji = "PASS" if result.is_success else "FAIL"
    lines.append(f"**Status:** {status_emoji} ({result.workflow_status})")
    lines.append(f"**Started:** {result.started_at}")
    lines.append(f"**Finished:** {result.finished_at}")
    lines.append("")


def _pack_summary(lines: list[str], result: UC1DemoResult) -> None:
    lines.append("## Demo Pack")
    lines.append("")
    pack = result.pack
    lines.append(f"- **Draft:** {len(pack.draft_text)} characters")
    lines.append(f"- **Venues:** {len(pack.venue_seeds)} seeds")
    for v in pack.venue_seeds:
        lines.append(f"  - {v.get('name', '?')}")
    lines.append(f"- **Guidelines:** {len(pack.venue_guidelines)} files")
    lines.append(f"- **Corpus files:** {len(pack.corpus)} files, "
                 f"{sum(len(v) for v in pack.corpus.values())} articles total")
    lines.append(f"- **Pack valid:** {pack.is_valid}")
    if pack.errors:
        lines.append(f"- **Pack errors:** {pack.errors}")
    lines.append("")


def _workflow_summary(lines: list[str], result: UC1DemoResult) -> None:
    lines.append("## Workflow Execution")
    lines.append("")
    completed = sum(1 for s in result.step_results if s.get("status") == "completed")
    skipped = sum(1 for s in result.step_results if s.get("status") == "skipped")
    failed = sum(1 for s in result.step_results if s.get("status") == "failed")
    total = len(result.step_results)
    lines.append(f"- **Total steps:** {total}")
    lines.append(f"- **Completed:** {completed}")
    lines.append(f"- **Skipped:** {skipped}")
    lines.append(f"- **Failed:** {failed}")
    lines.append(f"- **Final status:** {result.workflow_status}")
    lines.append("")


def _step_details(lines: list[str], result: UC1DemoResult) -> None:
    lines.append("## Step Results")
    lines.append("")
    lines.append("| Step | Agent | Status | Details |")
    lines.append("|------|-------|--------|---------|")
    for sr in result.step_results:
        idx = sr.get("step_index", "?")
        agent = sr.get("agent_role_id", "?")
        status = sr.get("status", "?")
        detail = ""
        if status == "skipped":
            detail = sr.get("reason", "")
        elif status == "failed":
            detail = sr.get("error", "")
        elif status == "completed":
            conf = sr.get("confidence", "")
            ev = sr.get("evidence_status", "")
            parts = []
            if conf:
                parts.append(f"confidence={conf}")
            if ev:
                parts.append(f"evidence={ev}")
            detail = ", ".join(parts)
        lines.append(f"| {idx} | {agent} | {status} | {detail} |")
    lines.append("")


def _entity_summary(lines: list[str], result: UC1DemoResult) -> None:
    lines.append("## Entities Produced")
    lines.append("")
    if not result.entities:
        lines.append("No entities produced.")
        lines.append("")
        return

    for key, entity in result.entities.items():
        lines.append(f"### {key}")
        lines.append("")
        if isinstance(entity, dict):
            _dict_summary(lines, entity)
        elif isinstance(entity, list):
            lines.append(f"List with {len(entity)} items.")
        else:
            lines.append(f"Type: {type(entity).__name__}")
        lines.append("")


def _dict_summary(lines: list[str], d: dict[str, Any], max_keys: int = 12) -> None:
    keys = list(d.keys())
    shown = keys[:max_keys]
    for k in shown:
        v = d[k]
        if isinstance(v, str) and len(v) > 120:
            v = v[:120] + "..."
        elif isinstance(v, (list, dict)):
            v = f"{type(v).__name__}({len(v)} items)"
        lines.append(f"- **{k}:** {v}")
    if len(keys) > max_keys:
        lines.append(f"- ... and {len(keys) - max_keys} more fields")


def _evidence_gaps(lines: list[str], result: UC1DemoResult) -> None:
    lines.append("## Evidence Gaps")
    lines.append("")
    lines.append("The following evidence levels are not covered in this demo:")
    lines.append("")
    lines.append("- **L5 (Review Process Dynamics):** No reviewer behavior data available offline")
    lines.append("- **L6 (Outcome Statistics):** No acceptance/rejection statistics without live data")
    lines.append("- **L7 (User Memory & Outcomes):** No prior submission experience data")
    lines.append("")
    lines.append("These gaps are expected in an offline demo and are explicitly reported,")
    lines.append("not silently filled with fabricated data.")
    lines.append("")


def _footer(lines: list[str], result: UC1DemoResult) -> None:
    lines.append("---")
    lines.append("")
    lines.append("*Generated by Kairoskopion UC-1 Demo Pack v0. Offline, deterministic, no LLM.*")
    lines.append("")
    if result.trace_log:
        lines.append("<details>")
        lines.append("<summary>Workflow Trace Log</summary>")
        lines.append("")
        lines.append("```")
        for entry in result.trace_log:
            lines.append(entry)
        lines.append("```")
        lines.append("")
        lines.append("</details>")
        lines.append("")
