[Reading 73 lines from start (total: 73 lines, 0 remaining)]

"""D25 source-completeness projection consumed by Kairon qualification."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any
from ..schema import ArticleModel

BIBLIOGRAPHY_STATUSES = {
    "VERIFIED_COMPLETE", "VERIFIED_BOUNDED", "PRESENT_UNVERIFIED",
    "SOURCE_MAP_ONLY", "SOURCE_TRACES_ONLY", "ABSENT", "UNKNOWN",
}
REFERENCE_COUNT_STATUSES = {"VERIFIED", "BOUNDED", "UNVERIFIED", "UNAVAILABLE"}

@dataclass
class SourceCompletenessReport:
    report_id: str
    article_id: str
    manuscript_revision: str
    bibliography_status: str
    reference_count_status: str
    reference_count: int | None = None
    carriers: list[str] = field(default_factory=list)
    source_map_refs: list[str] = field(default_factory=list)
    source_trace_refs: list[str] = field(default_factory=list)
    unresolved_source_needs: list[str] = field(default_factory=list)
    unresolved_locator_needs: list[str] = field(default_factory=list)
    provenance: list[str] = field(default_factory=list)
    decision: str = "KEEP_UNKNOWN"
    rationale: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.bibliography_status not in BIBLIOGRAPHY_STATUSES:
            raise ValueError("unsupported bibliography_status")
        if self.reference_count_status not in REFERENCE_COUNT_STATUSES:
            raise ValueError("unsupported reference_count_status")
        if self.reference_count is not None and self.reference_count < 0:
            raise ValueError("reference_count must be >= 0")
        if self.reference_count_status == "VERIFIED" and self.reference_count is None:
            raise ValueError("VERIFIED reference_count requires a count")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

def project_verified_reference_count(
    article: ArticleModel,
    report: SourceCompletenessReport,
    *,
    current_manuscript_revision: str,
) -> ArticleModel:
    """Project only exact verified current-revision bibliography evidence."""
    if report.article_id == "":
        raise ValueError("report article_id must be non-empty")
    if report.manuscript_revision != current_manuscript_revision:
        return article
    if report.reference_count_status != "VERIFIED":
        return article
    if report.bibliography_status != "VERIFIED_COMPLETE":
        return article
    article.reference_count = report.reference_count
    evidence_ref = f"source_completeness:{report.report_id}"
    if evidence_ref not in article.evidence_refs:
        article.evidence_refs.append(evidence_ref)
    article.unknowns = [x for x in article.unknowns if x != "article:reference_count"]
    return article


def source_completeness_debt(report: SourceCompletenessReport) -> list[str]:
    """Return explicit debt without converting unknown bibliography evidence to zero."""
    if (
        report.bibliography_status == "VERIFIED_COMPLETE"
        and report.reference_count_status == "VERIFIED"
    ):
        return []
    return ["article:reference_count"]