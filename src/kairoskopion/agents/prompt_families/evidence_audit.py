"""Evidence Audit prompt family (spec §69.14).

Audits evidence coverage: which claims are supported, which are
inferences, which are unknown, which sources are stale.
"""

from __future__ import annotations

FAMILY_ID = "evidence_audit_v1"
FAMILY_NAME = "Evidence Audit"
VERSION = "1.0.0"
PURPOSE = (
    "Audit the evidence backing of all claims in a pipeline run: "
    "identify unsupported claims, stale sources, missing evidence, "
    "and evidence quality issues. Produce a quality gate verdict."
)

INPUT_CONTRACT = {
    "pipeline_entities": "Dict of all entities produced in the pipeline run",
    "source_refs": "List of source references used",
}
OUTPUT_CONTRACT = {
    "audit_result": "Evidence audit result with per-entity coverage",
    "quality_gate": "PASS / PASS_WITH_WARNINGS / FAIL",
    "gaps": "List of evidence gaps",
}

SYSTEM_PROMPT = """\
You are Evidence Auditor — a specialized role within Kairoskopion.

Your task: audit the evidence backing of all claims produced in a \
pipeline run. Every entity field that makes a factual claim must \
trace to a source or be explicitly marked as inference/unknown.

## Audit dimensions

1. **source_coverage** — what % of claims trace to sources?
2. **inference_count** — how many claims are marked as inference?
3. **unknown_count** — how many fields are unknown?
4. **stale_sources** — any sources that may be outdated?
5. **conflicting_evidence** — any contradictory claims?
6. **fabrication_risk** — any claims that look fabricated?

## Quality gate rules

- **PASS** — >80% source coverage, no fabrication risk, <5 unknowns
- **PASS_WITH_WARNINGS** — 50-80% coverage, or 5-15 unknowns
- **FAIL** — <50% coverage, fabrication risk, or >15 critical unknowns

## Rules

- Audit the EVIDENCE STATUS, not the content quality.
- An inference is not a failure — it's an honest assessment.
- Unknown is not a failure — it's transparent incompleteness.
- A vendor claim is not a fact — flag the distinction.
- Fabrication = claim presented as fact without any source.
"""

USER_TEMPLATE = """\
Audit evidence coverage for this pipeline run.

## Pipeline entities
```json
{entities_json}
```

## Source references
```json
{sources_json}
```

Return a JSON object with evidence audit results.
"""

OUTPUT_SCHEMA: dict = {
    "title": "EvidenceAuditResult",
    "type": "object",
    "properties": {
        "quality_gate": {
            "type": "string",
            "enum": ["PASS", "PASS_WITH_WARNINGS", "FAIL"],
        },
        "source_coverage_pct": {"type": "number"},
        "inference_count": {"type": "integer"},
        "unknown_count": {"type": "integer"},
        "total_claims": {"type": "integer"},
        "gaps": {"type": "array", "items": {"type": "string"}},
        "stale_sources": {"type": "array", "items": {"type": "string"}},
        "fabrication_risks": {"type": "array", "items": {"type": "string"}},
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["quality_gate", "unknowns", "confidence"],
    "additionalProperties": False,
}

FORBIDDEN_BEHAVIORS = [
    "Do not PASS an audit with fabrication risks",
    "Do not count inferences as failures",
    "Do not count unknowns as failures if acknowledged",
]

EVIDENCE_REQUIREMENTS = [
    "Audit must cover all entities in the pipeline run",
]

UNKNOWN_HANDLING = "count_and_report"
VALIDATION_NOTES = "quality_gate must match coverage thresholds"


def validate_evidence_audit(data: dict) -> list[str]:
    warnings: list[str] = []
    if data.get("fabrication_risks") and data.get("quality_gate") == "PASS":
        warnings.append("Fabrication risks present but gate is PASS")
    return warnings


EVIDENCE_AUDIT_FAMILY = {
    "family_id": FAMILY_ID,
    "agent_role_id": "evidence_auditor",
    "version": VERSION,
    "system_prompt": SYSTEM_PROMPT,
    "user_prompt_template": USER_TEMPLATE,
    "output_schema": OUTPUT_SCHEMA,
    "validator": validate_evidence_audit,
}
