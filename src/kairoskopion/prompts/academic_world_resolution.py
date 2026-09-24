"""Academic-world resolution prompt family — regional/publication ecology router."""

from __future__ import annotations

ACADEMIC_WORLD_RESOLUTION_SYSTEM = """\
You are Academic World Resolver in Kairoskopion.

Resolve publication trajectories between disciplinary pathway mapping and venue-family discovery.
Use only article evidence, user constraints, local AcademicWorldNode records, discipline/pathway
records, and source packets supplied in the input.

Hard rules:
1. Regional/publication ecology is a routing coordinate, never a proxy for quality, worldview,
   nationality, ethnicity, or a civilizational essence.
2. Language, country, indexing regime, institution network, disciplinary lineage and citation
   ecology are separate axes. Do not collapse them.
3. Select node_ids only from local_nodes. If the local graph is insufficient, return acquisition
   debt; do not invent a world, school, tribe, or venue from model memory.
4. Multiple trajectories are normal. Preserve parallel legitimate routes.
5. routing_scaffold nodes may organize search but cannot support substantive claims about norms.
6. Never infer an author's school or tribe from geography alone.
7. No venue names from model memory.
8. Unknown stays unknown.

Return JSON only.
"""

ACADEMIC_WORLD_RESOLUTION_USER_TEMPLATE = """\
Resolve academic-world trajectories for this article.

Article evidence:
{article_evidence}

Disciplinary pathways:
{disciplinary_pathways}

Local AcademicWorld nodes:
{local_nodes}

User region/language/indexing constraints:
{user_constraints}

Source packets / local evidence:
{source_packets}

Return trajectories, unresolved coverage, acquisition tasks, unknowns and confidence.
"""

ACADEMIC_WORLD_RESOLUTION_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "trajectories": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "path_node_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "disciplinary_pathway_ref": {"type": ["string", "null"]},
                    "fit_status": {
                        "type": "string",
                        "enum": ["supported", "plausible", "exploratory", "unknown"],
                    },
                    "evidence_refs": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "routing_scaffold_only": {"type": "boolean"},
                    "reasoning": {"type": "string"},
                },
                "required": [
                    "path_node_ids", "fit_status", "evidence_refs",
                    "routing_scaffold_only", "reasoning",
                ],
                "additionalProperties": False,
            },
        },
        "coverage_gaps": {"type": "array", "items": {"type": "string"}},
        "acquisition_tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "gap": {"type": "string"},
                    "query_hints": {"type": "array", "items": {"type": "string"}},
                    "target_sources": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["gap", "query_hints", "target_sources"],
                "additionalProperties": False,
            },
        },
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "confidence": {
            "type": "string",
            "enum": ["high", "medium", "low", "none"],
        },
        "reasoning": {"type": "string"},
    },
    "required": [
        "trajectories", "coverage_gaps", "acquisition_tasks",
        "unknowns", "confidence", "reasoning",
    ],
    "additionalProperties": False,
}


def validate_academic_world_resolution(data: dict, local_node_ids: set[str] | None = None) -> list[str]:
    warnings: list[str] = []
    local_node_ids = local_node_ids or set()
    for i, traj in enumerate(data.get("trajectories") or []):
        for node_id in traj.get("path_node_ids") or []:
            if local_node_ids and node_id not in local_node_ids:
                warnings.append(
                    f"trajectory[{i}] references non-local academic-world node {node_id!r}"
                )
        if traj.get("routing_scaffold_only") and traj.get("fit_status") == "supported":
            warnings.append(
                f"trajectory[{i}] cannot be supported by routing scaffold alone"
            )
    if not data.get("trajectories") and not data.get("coverage_gaps"):
        warnings.append("no trajectories and no coverage gaps")
    return warnings


ACADEMIC_WORLD_RESOLUTION_FAMILY = {
    "family_id": "academic_world_resolution_v1",
    "agent_role_id": "academic_world_resolver",
    "version": "1.0.0",
    "system_prompt": ACADEMIC_WORLD_RESOLUTION_SYSTEM,
    "user_prompt_template": ACADEMIC_WORLD_RESOLUTION_USER_TEMPLATE,
    "output_schema": ACADEMIC_WORLD_RESOLUTION_OUTPUT_SCHEMA,
    "validator": validate_academic_world_resolution,
}