"""Read-only, evidence-bound Russian portfolio projection for Indago W12.

No XLSX bytes, no inferred source reads, no new article identity, no sending.
Research lineage and negative discoveries are data, not success counters.
"""
from __future__ import annotations

from typing import Any

from .opportunity_graph import OpportunityGraphStore, assess_route


def _unique_count(records: list[dict[str, Any]]) -> int:
    return len({str(record["id"]) for record in records})


def _evidence_depth(record: dict[str, Any]) -> bool:
    return bool(
        (record.get("source_kind") or record.get("kind")) == "PUBLISHED_ARTICLE"
        and record.get("read_depth") == "FULL_TEXT"
        and record.get("passage_anchors")
    )


def _events_for_display(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for event in events:
        out.append({
            "eventId": event["event_id"],
            "kind": event.get("kind", ""),
            "subjectId": event.get("subject_id", ""),
            "sourceRef": event.get("source_ref", ""),
            "at": event.get("at", ""),
            "result": event.get("result", ""),
            "intellectualConsequence": event.get("intellectual_consequence", ""),
            "reopenLevel": event.get("reopen_level"),
            "nextAction": event.get("next_action", ""),
            "reason": event.get("reason", ""),
        })
    return out


def build_portfolio(
    store: OpportunityGraphStore, *, include_owner_prior: bool = False,
) -> dict[str, Any]:
    """Project only durable objects, without treating W12 advertised counts as rows.

    Every record revision stays visible. A route with no unambiguous target world
    shows blockers, never silently borrows an unrelated journal snapshot.
    """
    consumer = store.consumer_snapshot(include_owner_prior=include_owner_prior)
    all_records = consumer["records"]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in all_records:
        grouped.setdefault(record["kind"], []).append(record)

    def index(kind: str) -> dict[str, dict[str, Any]]:
        # Only unambiguous IDs can be mapped; multiple revisions without a
        # pinned revision never masquerade as one canonical current object.
        result = {}
        for record in grouped.get(kind, []):
            records = [x for x in grouped[kind] if x["id"] == record["id"]]
            if len(records) == 1:
                result[record["id"]] = record
        return result

    seeds = index("ArticleSeed")
    opportunities = index("ArticleOpportunity")
    journals = index("Journal")
    evidence = index("Evidence")
    worlds = grouped.get("VenueWorld", [])
    routes = grouped.get("OpportunityRoute", [])

    rows = []
    for route in routes:
        op = opportunities.get(str(route.get("opportunity_id", "")))
        seed = seeds.get(str((op or {}).get("seed_id", "")))
        journal = journals.get(str(route.get("journal_id", "")))
        matching_worlds = [
            world for world in worlds
            if world.get("journal_id") == route.get("journal_id")
            and route.get("target_world_version")
            and world.get("target_world_version") == route["target_world_version"]
        ]
        world = matching_worlds[0] if len(matching_worlds) == 1 else None

        decision = (op or {}).get("author_decision", "HOLD")
        consent_required = bool((seed or {}).get("coauthor_consent_required", False))
        consent_verified = bool((seed or {}).get("coauthor_consent_verified", False))
        assessment = assess_route(
            route, evidence, world,
            author_decision=decision,
            coauthor_consent=(not consent_required or consent_verified),
        )

        ids = (world or {}).get("published_example_evidence_ids") or []
        anchored_fulltext_count = len({
            ref for ref in ids
            if ref in evidence and _evidence_depth(evidence[ref])
        })
        blockers = list(assessment["blockers"])
        if op is None:
            blockers.append("article_opportunity_not_admitted_or_ambiguous")
        if seed is None:
            blockers.append("article_seed_not_admitted_or_ambiguous")
        if journal is None:
            blockers.append("journal_identity_not_admitted_or_ambiguous")
        if world is None:
            blockers.append("venue_world_revision_unpinned_or_ambiguous")

        raw_fit = str(route.get("fit") or "UNKNOWN")
        fit = raw_fit if raw_fit in {"FIT", "CONDITIONAL", "REJECT", "UNKNOWN"} else "UNKNOWN"
        if blockers and fit == "FIT":
            fit = "CONDITIONAL"

        record_id = str(route["id"]) + "@" + str(route["revision"])
        lineage = [
            item for item in (
                (seed or {}).get("source_ref"),
                (seed or {}).get("id"),
                (op or {}).get("id"),
                (world or {}).get("id"),
                route.get("id"),
            ) if item
        ]
        rows.append({
            "id": record_id,
            "seedId": str((seed or {}).get("id") or ""),
            "opportunityId": str((op or {}).get("id") or route.get("opportunity_id") or ""),
            "claim": str((op or {}).get("independent_claim") or ""),
            "scholarlyDialogue": str((op or {}).get("scholarly_problem") or ""),
            "venueId": str(route.get("journal_id") or ""),
            "journalName": str((journal or {}).get("canonical_name") or "Журнал не подтверждён"),
            "routeKind": route["route_type"],
            "fit": fit,
            "transformationCost": str(route.get("transformation_cost") or "Не оценена"),
            "requiredEvidence": list((op or {}).get("required_evidence") or []) + sorted(set(blockers)),
            "readDepth": "FULL_TEXT" if anchored_fulltext_count >= 3 else "UNKNOWN",
            "fullTextExampleCount": anchored_fulltext_count,
            "deadline": route.get("deadline"),
            "deadlineStage": route.get("deadline_stage"),
            "officialRouteRef": route.get("submission_channel_ref"),
            "authorDecision": decision,
            "evidenceRefs": list(route.get("policy_evidence_ids") or []),
            "lineage": lineage,
            "gateStatus": assessment["status"],
            "blockers": sorted(set(blockers)),
        })
    return {
        "schemaVersion": "opportunity-portfolio-v1",
        # The authenticated W12 importer does not exist; the presence of
        # manually constructed records cannot certify a W12 import.
        "importStatus": "BLOCKED_SOURCE_BYTES_UNAVAILABLE",
        "importReceipt": None,
        "seedCount": _unique_count(grouped.get("ArticleSeed", [])),
        "independentOpportunityCount": _unique_count(grouped.get("ArticleOpportunity", [])),
        "variantCount": _unique_count(grouped.get("TargetVariant", [])),
        "distinctVenueCount": _unique_count(grouped.get("Journal", [])),
        "rows": rows,
        "events": _events_for_display(consumer["events"]),
        "ownerPriorScienceVisibility": consumer["status"],
    }
