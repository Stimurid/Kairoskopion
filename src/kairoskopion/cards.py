"""Markdown card generation for Vault projections (spec Wave 3 §18)."""

from __future__ import annotations

from typing import Any


def _frontmatter(pairs: list[tuple[str, Any]]) -> str:
    lines = ["---"]
    for key, val in pairs:
        if val is not None:
            lines.append(f"{key}: {val}")
    lines.append("---")
    return "\n".join(lines)


def _section(title: str, items: list[str] | str | None) -> str:
    if not items:
        return ""
    if isinstance(items, str):
        return f"\n## {title}\n\n{items}\n"
    body = "\n".join(f"- {i}" for i in items if i)
    if not body:
        return ""
    return f"\n## {title}\n\n{body}\n"


def article_model_card(data: dict[str, Any]) -> str:
    fm = _frontmatter([
        ("id", data.get("article_model_id")),
        ("type", "ArticleModel"),
        ("stage", data.get("article_stage")),
        ("genre", data.get("genre_current")),
        ("lifecycle", data.get("lifecycle_status")),
    ])
    title = data.get("title_current") or "Untitled Article"
    body = f"# {title}\n"
    body += _section("Problem", data.get("problem_statement"))
    body += _section("Object of inquiry", data.get("object_of_inquiry"))
    body += _section("Core claims", data.get("core_claims"))
    body += _section("Method", data.get("method_description") or data.get("method_status"))
    body += _section("Protected core", data.get("protected_core"))
    body += _section("Unknowns", data.get("unknowns"))
    body += _section("Sources", data.get("source_refs"))
    return fm + "\n" + body


def venue_model_card(data: dict[str, Any]) -> str:
    fm = _frontmatter([
        ("id", data.get("venue_model_id")),
        ("type", "VenueModel"),
        ("venue_type", data.get("venue_type")),
        ("lifecycle", data.get("lifecycle_status")),
    ])
    name = data.get("canonical_name") or "Unknown Venue"
    body = f"# {name}\n"
    body += _section("Scope", data.get("scope_summary"))
    body += _section("Publisher", data.get("publisher_or_owner"))
    body += _section("Article types", data.get("article_types_supported"))
    body += _section("Language policy", data.get("language_policy"))
    body += _section("URLs", data.get("official_urls"))
    body += _section("Unknowns", data.get("unknowns"))
    return fm + "\n" + body


def fit_assessment_card(data: dict[str, Any]) -> str:
    fm = _frontmatter([
        ("id", data.get("fit_assessment_id")),
        ("type", "FitAssessment"),
        ("label", data.get("overall_label")),
        ("level", data.get("assessment_level")),
        ("lifecycle", data.get("lifecycle_status")),
    ])
    body = f"# Fit Assessment: {data.get('overall_label', '?')}\n"
    body += _section("Recommendation", data.get("recommendation"))
    axes = data.get("axes", [])
    if axes:
        body += "\n## Axes\n\n"
        body += "| Axis | Value | Notes |\n|------|-------|-------|\n"
        for ax in axes:
            body += f"| {ax.get('axis', '?')} | {ax.get('value', '?')} | {ax.get('notes', '')} |\n"
    body += _section("Unknowns", data.get("unknowns"))
    return fm + "\n" + body


def risk_report_card(data: dict[str, Any]) -> str:
    fm = _frontmatter([
        ("id", data.get("risk_report_id")),
        ("type", "RiskReport"),
        ("overall_risk", data.get("overall_risk_label")),
    ])
    body = "# Risk Report\n"
    body += _section("Blocking risks", data.get("blocking_risks"))
    body += _section("Warnings", data.get("warnings"))
    items = data.get("risk_items", [])
    if items:
        body += "\n## Risk items\n\n"
        for ri in items:
            body += f"- **{ri.get('risk_type', '?')}** ({ri.get('severity', '?')}): {ri.get('description', '')}\n"
    body += _section("Unknowns", data.get("unknowns"))
    return fm + "\n" + body


def submission_pack_card(data: dict[str, Any]) -> str:
    fm = _frontmatter([
        ("id", data.get("submission_pack_id")),
        ("type", "SubmissionPack"),
        ("ready_status", data.get("ready_status")),
    ])
    body = "# Submission Pack\n"
    body += _section("Files", data.get("files"))
    body += _section("Missing items", data.get("missing_items"))
    body += _section("Blocking issues", data.get("blocking_issues"))
    body += _section("Warnings", data.get("warnings"))
    body += _section("Cover letter", data.get("cover_letter"))
    return fm + "\n" + body


CARD_GENERATORS: dict[str, Any] = {
    "ArticleModel": article_model_card,
    "VenueModel": venue_model_card,
    "FitAssessment": fit_assessment_card,
    "RiskReport": risk_report_card,
    "SubmissionPack": submission_pack_card,
}


def generate_card(entity_type: str, data: dict[str, Any]) -> str | None:
    gen = CARD_GENERATORS.get(entity_type)
    if gen:
        return gen(data)
    return None
