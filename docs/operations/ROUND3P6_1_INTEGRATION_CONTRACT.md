# Round III-P6.1 — Integration Contract

## Record usage statuses

| source_status | review_status | usage_status | downstream rule |
|---------------|---------------|--------------|-----------------|
| accepted | curator_confirmed | `canonical` | Use as fact |
| provisional | any | `provisional_with_warning` | Show with explicit status + warning |
| rejected | any | `rejected_unusable` | Exclude from all product outputs |
| any | rejected | `rejected_unusable` | Exclude from all product outputs |
| unknown | any | `unknown` | Create acquisition task or unknown marker |
| (no record) | (no record) | `unknown` | Create acquisition task |

## Product rules

1. **Canonical** records can be used as fact in all product outputs
   (fit assessment, venue matrix, submission pack, dossier).
2. **Provisional** records can be shown/used ONLY with explicit status
   label and warning. Cannot be presented as canonical. Cannot be used
   in final submission recommendations without curator acceptance.
3. **Rejected** records cannot be used in any product output. Must be
   excluded from candidate pools, fit axes, and recommendations.
4. **Unknown** (no record found) creates a `SourceAcquisitionTask` or
   an explicit unknown marker. No model-memory facts substituted.
5. **LLM output never promotes** a record to canonical. Only curator
   `accept()` action changes source_status to accepted.

## Source fact rules

1. `source_id` and `source_url` may come ONLY from:
   - Source packet (adapter result, user-provided source)
   - Accepted registry record
   - Direct user input
2. **No model-memory source facts.** An LLM may propose candidate names
   for acquisition tasks but cannot provide source_id, source_url, ISSN,
   DOI, classification codes, or metrics from its training data.
3. Every candidate venue/section/classification/metric used downstream
   must have `evidence_refs` or `source_ref` traceable to a source, or
   be explicitly marked `unknown`/`provisional`.

## Integration points

### DisciplineSourceAcquisition
- Search DisciplineRegistry first
- Accepted match → return canonical, skip LLM
- Provisional match → return with warning
- No match → create SourceAcquisitionTask
- Source packets → create provisional DisciplineRecord

### VenueFunnel
- Search VenueRegistry + VenueSectionRegistry
- Candidates must carry record_id, source_status, usage_status
- Empty registry → create discovery tasks, no model-memory candidates
- Section candidates independent from parent

### VenueFamilyContext
- Build from registry/corpus evidence only
- No model-memory sibling names
- Insufficient corpus → incomplete/insufficient_evidence

### VenueMatrix
- Candidates must have provenance (evidence_refs)
- Reject/warn candidates without provenance
- Assess parent and section separately
- Provisional candidates remain provisional in output

### VenueFactExtraction
- Extracted data → provisional registry records
- Sections → VenueSectionRecord drafts
- Indexing claims → VenueClassificationRecord drafts (vendor_claim)
- Metrics → VenueMetricRecord drafts (per db/year/category)
- No scalar journal.quartile

## Enforcement

These rules are enforced via:
- `record_usage_status()` utility (registry/status.py)
- Test assertions on product outputs
- Integration smoke tests (Track 11)
