# Evidence Conflict and Reconciliation v0

## Problem

Different sources give different answers about the same venue, article, or
entity field. Without explicit conflict tracking, the system silently picks
one value and presents it as fact.

## Solution

### EvidenceConflict

When two or more claims about the same entity field have different values,
the system creates an `EvidenceConflict` object:

- `conflict_id` — unique identifier
- `entity_id` — which entity is affected
- `field_name` — which field conflicts
- `conflicting_claims` — list of claim dicts with their sources
- `conflict_type` — value_mismatch, status_mismatch, freshness_mismatch, authority_mismatch
- `severity` — blocking (if any authoritative claim involved), warning, informational
- `resolution_status` — unresolved, resolved_by_authority, resolved_by_user, resolved_by_freshness, deferred

### EvidenceReconciliationResult

After running claims through the authority checker and conflict detector:

- `resolved_claims` — claims that passed authority validation
- `unresolved_conflicts` — conflicts that remain open
- `downgraded_claims` — claims whose authority was reduced or prohibited
- `authority_notes` — human-readable explanations of decisions
- `unknowns` — things that remain unknown

### Key behavior

1. Conflicts are never silently resolved. They remain unresolved until explicitly addressed.
2. Prohibited authority claims are downgraded, not silently accepted.
3. Unresolved conflicts flow through to the EvidenceAuditor as warnings or blocking issues.
4. The number of unresolved conflicts is tracked in unknowns.

## Current state (v0)

- Detection: `detect_conflicts()` — compares claim values for same entity/field
- Reconciliation: `reconcile_evidence()` — validates claims, collects conflicts
- Integration: EvidenceAuditor accepts optional conflict list
- No agent-driven reconciliation flow yet
- No user confirmation UI yet

## Future

- Agent that presents conflicts to user for resolution
- Freshness-based auto-resolution (newer source wins if both authoritative)
- Cross-entity conflict propagation (venue name conflict affects all dependent entities)
