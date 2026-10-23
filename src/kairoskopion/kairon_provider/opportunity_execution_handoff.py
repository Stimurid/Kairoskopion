"""Read-only boundary: evidence-backed opportunity to Artikl review candidate.

This does NOT make an Article, a manuscript, a QA receipt, or a submission.
The execution runner separately requires an authoritative sibling, bound
artifacts, independent QA and explicit operator approval.
"""
from __future__ import annotations

from typing import Any

from .opportunity_graph import OpportunityGraphStore, _digest, assess_route
from .target_world_catalog import _digest as target_digest


PIN_KINDS = {
    "seed": "ArticleSeed",
    "opportunity": "ArticleOpportunity",
    "journal": "Journal",
    "route": "OpportunityRoute",
    "variant": "TargetVariant",
    "world": "VenueWorld",
}
ACCEPTED_TARGET_STATUSES = frozenset({"PROD_ACCEPTED", "PROD_OBSERVED"})


def prepare_opportunity_execution_handoff(
    store: OpportunityGraphStore,
    *,
    pins: dict[str, dict[str, str]],
    author_selection_event_id: str | None,
    target_world_package: dict[str, Any] | None,
) -> dict[str, Any]:
    """Validate exact revision pins without promoting a supposed latest version.

    The author event is a durable operator-provided claim, not a cryptographic
    signature or automatic authorization for external submission. All successful
    output is a candidate for further Artikl and author review only.
    """
    # Handoff never treats imported provisional owner science as approval.
    consumer = store.consumer_snapshot(include_owner_prior=False)
    consumer_records = consumer["records"]
    consumer_events = consumer["events"]
    blockers: list[str] = []
    found: dict[str, dict[str, Any]] = {}
    normalized_pins: dict[str, dict[str, str]] = {}

    for role, kind in PIN_KINDS.items():
        pin = pins.get(role)
        if not isinstance(pin, dict):
            blockers.append(f"missing_pin:{role}")
            continue
        ident = str(pin.get("id") or "").strip()
        rev = str(pin.get("revision") or "").strip()
        if not ident or not rev:
            blockers.append(f"incomplete_pin:{role}")
            continue
        normalized_pins[role] = {"id": ident, "revision": rev}
        obj = next((row for row in consumer_records
                    if row["kind"] == kind and row["id"] == ident
                    and row["revision"] == rev), None)
        if obj is None:
            blockers.append(f"unknown_pinned_record:{role}")
        else:
            found[role] = obj

    seed = found.get("seed")
    opportunity = found.get("opportunity")
    journal = found.get("journal")
    route = found.get("route")
    variant = found.get("variant")
    world = found.get("world")

    if seed is not None and seed.get("author_authority") != "ARTIKL":
        blockers.append("seed_not_authoritatively_artikl")
    for left, left_field, right, reason in (
        (opportunity, "seed_id", seed, "opportunity_seed_mismatch"),
        (route, "opportunity_id", opportunity, "route_opportunity_mismatch"),
        (route, "journal_id", journal, "route_journal_mismatch"),
        (variant, "seed_id", seed, "variant_seed_mismatch"),
        (variant, "opportunity_id", opportunity, "variant_opportunity_mismatch"),
        (world, "journal_id", journal, "venue_world_journal_mismatch"),
    ):
        if left is not None and right is not None and left.get(left_field) != right["id"]:
            blockers.append(reason)
    if world is not None and variant is not None:
        if variant.get("target_world_version") != world.get("target_world_version"):
            blockers.append("variant_world_version_mismatch")
    if world is not None and route is not None:
        if route.get("target_world_version") != world.get("target_world_version"):
            blockers.append("route_world_version_mismatch")

    # An evidence id may have several revisions. Without exact revision in the
    # selected route/world, a second revision blocks rather than becoming latest.
    evidence_versions: dict[str, list[dict[str, Any]]] = {}
    for item in consumer_records:
        if item["kind"] != "Evidence":
            continue
        evidence_versions.setdefault(item["id"], []).append(item)
    required_evidence: set[str] = set()
    if route:
        policy_ids = route.get("policy_evidence_ids") or []
        if not isinstance(policy_ids, list):
            blockers.append("invalid_policy_evidence_ids")
        else:
            required_evidence.update(policy_ids)
    if world:
        example_ids = world.get("published_example_evidence_ids") or []
        if not isinstance(example_ids, list):
            blockers.append("invalid_example_evidence_ids")
        else:
            required_evidence.update(example_ids)
    evidence: dict[str, dict[str, Any]] = {}
    for evidence_id in sorted(required_evidence):
        versions = evidence_versions.get(evidence_id, [])
        if len(versions) != 1:
            blockers.append(
                ("ambiguous_evidence_revision:" if versions else "evidence_missing:")
                + evidence_id
            )
        else:
            evidence[evidence_id] = versions[0]

    author_ref = str((seed or {}).get("author_ref") or "").strip()
    if not author_ref:
        blockers.append("author_identity_not_pinned")
    selection_event = None
    if not author_selection_event_id:
        blockers.append("author_selection_event_missing")
    else:
        events = [
            item for item in consumer_events
            if item["event_id"] == author_selection_event_id
        ]
        if len(events) == 1:
            selection_event = events[0]
        else:
            blockers.append("author_selection_event_missing")

    if selection_event:
        expected = {
            "kind": "AUTHOR_DECISION",
            "actor_role": "AUTHOR",
            "author_ref": author_ref,
            "subject_id": (opportunity or {}).get("id"),
            "opportunity_revision": (opportunity or {}).get("revision"),
            "route_id": (route or {}).get("id"),
            "route_revision": (route or {}).get("revision"),
            "variant_id": (variant or {}).get("id"),
            "variant_revision": (variant or {}).get("revision"),
            "decision": "ACCEPT",
        }
        if any(selection_event.get(key) != value for key, value in expected.items()):
            blockers.append("author_selection_lineage_or_authority_mismatch")

    if route is not None:
        consent_needed = bool((seed or {}).get("coauthor_consent_required"))
        consent_verified = bool((seed or {}).get("coauthor_consent_verified"))
        decision = (
            "ACCEPT" if selection_event and
            "author_selection_lineage_or_authority_mismatch" not in blockers
            else "HOLD"
        )
        assessment = assess_route(
            route, evidence, world, author_decision=decision,
            coauthor_consent=(not consent_needed or consent_verified),
        )
        blockers.extend(assessment["blockers"])

    # The venue research model is not automatically the immutable exchange
    # package required by the publication runner. Do not synthesize one.
    target_pin: dict[str, str] | None = None
    if not isinstance(target_world_package, dict):
        blockers.append("frozen_target_world_package_missing")
    else:
        package_id = str(target_world_package.get("package_id") or "").strip()
        digest = str(target_world_package.get("content_digest") or "").strip()
        snapshot = target_world_package.get("snapshot")
        status = str(
            target_world_package.get("catalog_status")
            or target_world_package.get("status") or ""
        ).strip()
        if not package_id or not digest or not isinstance(snapshot, dict):
            blockers.append("target_world_package_unversioned")
        elif digest != target_digest(snapshot):
            blockers.append("target_world_digest_mismatch")
        elif status not in ACCEPTED_TARGET_STATUSES:
            blockers.append("target_world_not_prod_accepted")
        elif world and snapshot.get("snapshot_id") != world.get("target_world_version"):
            blockers.append("target_world_snapshot_version_mismatch")
        else:
            target_pin = {"package_id": package_id, "content_digest": digest}
        if route and route.get("target_world_package_id") != package_id:
            blockers.append("route_target_world_package_unpinned")
        if variant and variant.get("target_world_package_id") != package_id:
            blockers.append("variant_target_world_package_unpinned")

    blockers = sorted(set(blockers))
    handoff_id = "opportunity-handoff:" + _digest({
        "pins": normalized_pins,
        "author_event_id": author_selection_event_id,
        "target_world": target_pin,
        "evidence_versions": sorted(
            (item["id"], item["revision"]) for item in evidence.values()
        ),
    })[:24]
    ready = len(blockers) == 0
    return {
        "schema_version": "opportunity-execution-handoff-v1",
        "handoff_id": handoff_id,
        "status": "CANDIDATE_FOR_ARTIKL_REVIEW" if ready else "BLOCKED",
        "blockers": blockers,
        "pinned_objects": normalized_pins,
        "author_selection_event_id": author_selection_event_id,
        "frozen_target_world": target_pin,
        "evidence_pins": {
            key: record["revision"] for key, record in sorted(evidence.items())
        },
        "next_actor": "ARTIKL_REVIEW" if ready else "EVIDENCE_OR_AUTHOR_REPAIR",
        "semantic_authority": "ARTIKL",
        "external_submission": "FORBIDDEN",
        "article_created": False,
        "authoritative_sibling": None,
        "publication_runner_manifest": None,
        "finalization_request": None,
        "qa_pass_claim": False,
    }
