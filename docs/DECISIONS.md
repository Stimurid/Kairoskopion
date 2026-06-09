# Architectural Decisions — Kairoskopion

Each decision is a deliberate choice with rationale.

## ADR-01: Separate repository, not Litops fork

**Decision:** Kairoskopion lives in its own repo, not as a submodule or directory inside Litops.

**Rationale:** Kairoskopion is a bounded context with its own domain model, persistence,
and release cadence. Coupling it to Litops's repo would create false dependencies
and merge conflicts. Integration happens through well-defined interface contracts
(stub dataclasses now, API calls later).

## ADR-02: Remote branch safety

**Decision:** Never force-push. Never push to `main` without explicit user command.
Never delete remote branches. Never auto-merge/rebase remote main.

**Rationale:** The user works across multiple machines and sessions. Destructive
git operations risk losing work that exists only on the remote. Safety first.

## ADR-03: Evidence-first architecture

**Decision:** Every claim in the system must trace to a source or be marked UNKNOWN.
11 evidence statuses: FACT_FROM_SOURCE, VENDOR_CLAIM, CORPUS_OBSERVATION,
INFERENCE, TACIT_SIGNAL, USER_NOTE, PRIOR_OUTCOME, UNKNOWN, INACCESSIBLE,
STALE, CONFLICTING_EVIDENCE.

**Rationale:** Publication positioning is high-stakes for researchers. An unsourced
claim is worse than an explicit "unknown" — it creates false confidence.
The evidence layer makes provenance auditable and forces the system to be
honest about what it knows and doesn't know.

## ADR-04: Multi-axis fit, no single score

**Decision:** FitAssessment uses 8 qualitative axes (topic, discipline, genre,
method, citation_ecology, language_register, formal_compliance, publication_regime)
with values strong/medium/weak/bad/unknown. No numeric "fit score".

**Rationale:** A single score (e.g. "78% match") hides the structure of the
mismatch. A paper might be a perfect topical fit but completely wrong in
methodology expectations. The researcher needs to see which axes are weak
to make an informed decision, not a misleading average.

## ADR-05: Unknowns preserved, never silently absent

**Decision:** When data is missing, the system marks it UNKNOWN or INACCESSIBLE.
It never silently drops fields, axes, or evidence items.

**Rationale:** In academic publishing, what you don't know matters as much as
what you know. A venue with unknown AI disclosure policy is a real risk.
Silent omission would hide actionable uncertainty from the user.

## ADR-06: No external API as required dependency

**Decision:** The system must work fully offline with local files. External APIs
(OpenAlex, Crossref, etc.) will be optional enrichment adapters, never
required for the core pipeline.

**Rationale:** Researchers may work offline, on restricted networks, or not
want to expose their manuscript metadata to third parties. The core
value — structured fit analysis — must not depend on API availability.

## ADR-07: No fake references

**Decision:** Never fabricate citation data, DOIs, journal names, or source
entries. If reference data is unavailable, mark it UNKNOWN.

**Rationale:** Fabricated references are an integrity violation in academic
context. The system must not produce data that could mislead a
researcher about the bibliographic landscape.

## ADR-08: No submission automation

**Decision:** Kairoskopion analyzes fit and produces plans/reports. It does not
automate the submission process itself — no portal scraping, no auto-fill,
no automated email to editors.

**Rationale:** Submission is a deliberate human act with ethical and contractual
implications (dual submission policies, author agreements). Automating it
would shift responsibility from the researcher to the tool.

## ADR-09: JSONL append-only registries

**Decision:** Persistence uses JSONL files with append-only semantics.
No SQL, no ORM, no migration framework.

**Rationale:** Simplest possible persistence that supports auditability
(append-only = full history), is human-readable, works offline,
requires no database server, and is trivially portable. Registries
can later be exported to Litops's more sophisticated storage.

## ADR-10: Deterministic pipeline, no LLM until stable

**Decision:** All services use regex/heuristic extraction. No LLM calls
until the source/evidence/persistence layer is proven stable.

**Rationale:** LLM extraction is non-deterministic, expensive, and hard
to test. Building on a deterministic foundation means we can verify
pipeline correctness, add LLM as an optional enhancement later,
and always have a fallback path that works without API access.

## ADR-11: Vault cards as markdown with YAML frontmatter

**Decision:** Human-readable output goes to markdown files with YAML
frontmatter, organized in a vault directory structure compatible
with Obsidian.

**Rationale:** Researchers should be able to browse results without
special tools. Markdown + YAML is universally readable, version-controllable,
and compatible with Litops's Obsidian vault when integration is built.

## ADR-12: Protected core requires user acceptance

**Decision:** When the system detects that a proposed change touches
WhiteCrow's protected core (the manuscript's essential intellectual
contribution), it marks it `core_touching` or `core_transforming`
and requires explicit user acceptance. Auto-extraction always marks
core as "not confirmed by user".

**Rationale:** The protected core is the researcher's intellectual
property and identity. No automated system should modify it without
conscious human consent.
