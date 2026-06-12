"""Venue Identifier — resolves venue references to structured identity candidates.

Deterministic: normalizes name, ISSN, URL from input. Produces a structured
identity candidate with explicit unknowns. Does NOT invent fields that
were not provided (ISSN, publisher, indexing, country, scope).
"""

from __future__ import annotations

import re
from typing import Any

from ..base_shell import missing_input_output, service_output
from ..contract import AgentInput, AgentOutput, AgentRole
from ...llm.provider import LLMProvider


class VenueIdentifierAgent(AgentRole):
    role_id = "venue_identifier"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        return self.execute_deterministic(inp)

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        venue_ref = inp.entities.get("venue_reference", {})
        name = venue_ref.get("name") or inp.raw_text or ""
        name = name.strip()
        issn = venue_ref.get("issn")
        url = venue_ref.get("url")
        publisher = venue_ref.get("publisher")
        aliases = venue_ref.get("aliases", [])

        if not name and not issn and not url:
            return missing_input_output("VenueIdentification", "venue_reference (name, ISSN, or URL)")

        identity: dict[str, Any] = {}
        unknowns: list[str] = []
        evidence_refs: list[str] = []
        fields_provided = 0

        if name:
            identity["canonical_name"] = name
            fields_provided += 1
        else:
            unknowns.append("canonical_name not provided — needs lookup")

        if issn:
            identity["issn"] = _normalize_issn(issn)
            fields_provided += 1
        else:
            identity["issn"] = None
            unknowns.append("ISSN not provided — needs OpenAlex/Crossref lookup")

        if url:
            identity["official_url"] = url
            fields_provided += 1
        else:
            identity["official_url"] = None

        if publisher:
            identity["publisher_hint"] = publisher
        else:
            identity["publisher"] = None
            unknowns.append("Publisher not provided — needs API lookup")

        identity["aliases"] = aliases if aliases else []
        identity["scope"] = None
        identity["indexing"] = None
        identity["country"] = None

        if fields_provided >= 2:
            identity["resolution_status"] = "identity_partial"
            identity["ambiguity_status"] = "low"
            confidence = "medium"
        elif fields_provided == 1:
            identity["resolution_status"] = "identity_minimal"
            identity["ambiguity_status"] = "medium"
            confidence = "low"
        else:
            identity["resolution_status"] = "needs_sources"
            identity["ambiguity_status"] = "high"
            confidence = "none"

        identity["resolved_venue_id"] = None
        identity["next_lookup_actions"] = _suggest_next_lookups(name, issn, url)

        trace = []
        if name:
            trace.append(f"name='{name}'")
        if issn:
            trace.append(f"issn={issn}")
        if url:
            trace.append(f"url={url}")

        return service_output(
            "VenueIdentification",
            identity,
            unknowns=unknowns,
            evidence_refs=evidence_refs,
            confidence=confidence,
            evidence_status="FACT_FROM_SOURCE" if fields_provided >= 1 else "UNKNOWN",
            trace_notes=[f"identity from provided fields: {', '.join(trace)}"],
        )


def _normalize_issn(issn: str) -> str:
    cleaned = re.sub(r"[^0-9Xx]", "", issn)
    if len(cleaned) == 8:
        return f"{cleaned[:4]}-{cleaned[4:]}"
    return issn.strip()


def _suggest_next_lookups(
    name: str | None, issn: str | None, url: str | None,
) -> list[str]:
    actions = []
    if name and not issn:
        actions.append("lookup_openalex_by_name")
        actions.append("lookup_crossref_by_name")
    if issn and not name:
        actions.append("lookup_openalex_by_issn")
        actions.append("lookup_crossref_by_issn")
    if not url:
        actions.append("find_official_homepage")
    if name or issn:
        actions.append("check_doaj_record")
    return actions
