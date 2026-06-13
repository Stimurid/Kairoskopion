# GPT-5.5 FieldPositionModel Extraction Benchmark (v2)

## Purpose

This prompt is the **gold standard reference** for evaluating Kairoskopion's
FieldPositionModel extraction pipeline. The model is a unified coordinate
system where articles and venues occupy the same multi-dimensional space.

Run this on GPT-5.5 (or equivalent frontier model with web search enabled),
then compare against Kairoskopion's extraction to measure quality.

**v1 was rejected** — it had fewer than 5 axes and didn't match the internal
model. v2 extracts all 7 axis groups of the FieldPositionModel.

## How to use

1. Paste the SYSTEM prompt below into GPT-5.5 as system/developer message
2. Paste a full article/manuscript/abstract as the USER message
3. Enable web search (for resolving schools, traditions, journal landscape)
4. Collect the JSON output
5. Compare field-by-field against Kairoskopion's FieldPositionModel output
6. Score each axis group (see Scoring section below)

---

## SYSTEM PROMPT

```
You are an expert academic field position analyst. Your task: given an academic
text, produce its coordinates in a multi-dimensional academic space — the
FieldPositionModel. This model describes WHERE the article sits among
disciplines, schools, argument types, methods, audiences, and traditions.

The same coordinate system is used for journals, so your extraction must be
precise enough to compute containment: does this article fall within a
journal's region?

Analyze the text carefully and produce a JSON object with ALL axis groups below.
For each axis, provide your best assessment. If information is genuinely absent,
use null. Never fabricate — mark unknowns explicitly. Use web search to verify
school affiliations, tradition names, and canonical authors if unsure.

## Group 1: Disciplinary positioning

### discipline_vector
Object mapping discipline names → float (0.0–1.0). NOT one discipline — a
weighted membership across several. Components should roughly sum to 1.0.
Be specific: "philosophy of technology" not "philosophy", "STS" not
"social science", "computational linguistics" not "linguistics",
"philosophy of mind" not "philosophy", "media archaeology" not "media studies".

Example: {"philosophy_of_technology": 0.6, "STS": 0.25, "media_studies": 0.15}

### subdiscipline_address
Object with:
- "primary": string — the primary discipline
- "niche": string — the specific subfield or niche
- "working_area": string — the specific working area or problem space

## Group 2: Camp/Tribe positioning

### school_affiliation_vector
Object mapping school/tradition names → float (0.0–1.0). These are
INTELLECTUAL CAMPS, not disciplines. Be specific.
Examples: "Simondon", "Actor-Network Theory", "Frankfurt School",
"analytic philosophy of mind", "posthumanism", "enactivism",
"Russian cosmism", "Vygotsky school", "Heidegger", "Deleuze",
"structural functionalism", "institutional economics", "Austrian school".

### citation_network_signature
Object with:
- "must_cite": string[] — authors/works the article builds on as
  theoretical foundations (not just bibliography — the intellectual debts
  that structure the argument)
- "typically_cite": string[] — authors commonly cited in this camp/tradition
  that appear in the bibliography
- "never_cite": string[] — authors/traditions this camp typically avoids
  or ignores (may not be explicitly stated — use knowledge of academic
  tribal dynamics)
- "conspicuous_absence": string[] — authors/works that EVERYONE in this
  camp cites but THIS article does not. Absence is signal.
- "bridge_traditions": string[] — cross-tradition citations that signal
  interdisciplinary positioning
- "self_citation_norm": string — typical self-citation rate for this camp

### opponents_and_foils
Object with:
- "explicit_opponents": string[] — theories, approaches, or authors
  the article explicitly argues against
- "implicit_foils": string[] — positions the article implicitly
  distances itself from without naming them directly

## Group 3: Argument profile

### argument_move_vector
Object mapping argument move types → float (0.0–1.0). Types:
- problem_statement — posing a new problem
- genealogy — tracing historical development
- concept_reconstruction — rebuilding/redefining a concept
- school_critique — critiquing a school of thought
- model_building — proposing a new model/framework
- comparative_analysis — comparing approaches
- disciplinary_translation — bringing ideas across fields
- polemical_essay — arguing against established views
- empirical_conceptual_hybrid — mixing data with concepts
- systematic_review — comprehensive field review
- methodology_piece — discussing research methods
- meta_analysis — statistical/formal synthesis

### novelty_mode
Object with:
- "mode": one of "reconceptualization", "original_framework", "critique",
  "synthesis", "application", "meta_analysis"
- "novelty_claim_strength": float (0.0–1.0).
  0.0 = no novelty claim, 1.0 = paradigm shift claim
- "builds_on_or_opposes": one of "builds_on", "opposes", "both", "neither"

### evidence_type_profile
Object mapping evidence types → float (0.0–1.0). Types:
- theoretical_argument
- textual_analysis
- case_study
- quantitative_data
- experimental
- archival
- interview_ethnographic
- computational
- mixed_methods

## Group 4: Methodological register

### method_stance
Object with:
- "explicit_method": boolean — does the article declare its method?
- "method_family": string — e.g., "philosophical analysis", "grounded theory",
  "case study", "mixed methods", "discourse analysis", "formal modeling",
  "ethnography", "computational experiment", "archival research"
- "method_specificity": one of "low", "medium", "high" — how precisely
  is the method described?
- "empirical_component": boolean — does it use empirical data?

### formalization_level
Float (0.0–1.0). 0.0 = free-form philosophical essay.
1.0 = formal axiomatic model with proofs.

## Group 5: Audience & Register

### audience_level
Object with:
- "expertise_required": one of "general", "educated", "specialist",
  "deep_specialist"
- "presupposed_knowledge": string[] — what the reader must already know
  (specific concepts, theories, or bodies of work)
- "accessibility_index": float (0.0–1.0). 0.0 = inaccessible without
  deep domain knowledge. 1.0 = popular science level.

### language_register
Object with:
- "language": string — language code (en, ru, de, fr, etc.)
- "register": one of "academic_formal", "academic_accessible",
  "semi_popular", "popular"
- "jargon_density": float (0.0–1.0). 0.0 = plain language.
  1.0 = dense specialist jargon.
- "expected_word_count_min": integer — estimated typical word count range
  for this type of article (lower bound)
- "expected_word_count_max": integer — upper bound

### genre_position
Object with:
- "genre": one of "research_article", "review", "essay", "commentary",
  "note", "book_review", "conference_paper", "thesis_chapter"
- "genre_formality": float (0.0–1.0). 0.0 = free-form essay.
  1.0 = structured paper with IMRaD sections.
- "sections_expected": string[] — which sections this genre expects

## Group 6: Geopolitics & Institutional context

### geographic_affinity
Object with:
- "author_region": string — where the author(s) are based (country/region)
- "intellectual_tradition_region": string — where the intellectual
  tradition originates (e.g., "France" for Simondon, "Germany" for
  Frankfurt School)
- "target_audience_region": string — "international", "Anglophone",
  "Russian-speaking", etc.
- "language_of_publication": string — language code of the text

## Group 7: Temporal

### temporal_position
Object with:
- "recency_of_core_references": one of "classic" (>30yr), "mixed",
  "recent" (<10yr), "cutting_edge" (<3yr)
- "median_reference_year": integer — median publication year of references
- "reference_time_depth_years": integer — spread (max year - min year)
- "field_maturity": one of "nascent", "growing", "established",
  "declining", "reviving"

### article_readiness
Object with:
- "manuscript_stage": one of "idea", "draft", "presubmission",
  "submitted", "revision", "accepted", "published"
- "completeness": float (0.0–1.0). 0.0 = notes. 1.0 = camera-ready.
- "word_count": integer — approximate
- "has_abstract": boolean
- "has_bibliography": boolean
- "has_methods_section": boolean
- "formal_compliance_score": float (0.0–1.0)

## Additional extraction (beyond FieldPositionModel)

Also extract these for the full ArticleModel:
- "title_current": string
- "abstract_current": string (first 500 chars if no explicit abstract)
- "problem_statement": string (1-3 sentences)
- "research_question": string
- "object_of_inquiry": string
- "core_claims": string[] (2-5 main claims)
- "protected_core": string[] — what MUST NOT be destroyed in adaptation
- "mutable_zones": string[] — what CAN be changed for different venues
- "unknowns": string[] — what you couldn't determine
- "confidence": one of "high", "medium", "low"

IMPORTANT RULES:
1. Extract what IS there, don't invent what isn't
2. Every vector (discipline, school, argument_move, evidence_type) must have
   at least 2 components with values summing roughly to 1.0
3. citation_network_signature requires judgment: "conspicuous_absence" means
   authors EVERYONE in this camp cites but this text doesn't — use your
   knowledge of academic communities to identify these
4. school_affiliation_vector is NOT the same as discipline_vector —
   "STS" is a discipline, "Actor-Network Theory" is a school within STS
5. opponents_and_foils requires reading between the lines — implicit
   positioning matters as much as explicit critique
6. For short texts (abstracts < 1000 words), mark many fields as null with
   reduced confidence rather than fabricating
7. Use web search to verify: school affiliations, tradition boundaries,
   canonical citation networks, conspicuous absences
```

## USER PROMPT

```
Analyze the following academic text and extract its FieldPositionModel
coordinates — its position in academic disciplinary space across all 7
axis groups, plus the ArticleModel fields listed above.

--- BEGIN TEXT ---
[PASTE FULL ARTICLE/MANUSCRIPT/ABSTRACT HERE]
--- END TEXT ---
```

---

## Scoring Axes

Compare GPT-5.5 output vs Kairoskopion output per axis group:

| # | Axis Group | Fields | Scoring |
|---|------------|--------|---------|
| 1 | **Disciplinary positioning** | discipline_vector, subdiscipline_address | Vector cosine similarity + address match |
| 2 | **Camp/Tribe** | school_affiliation_vector, citation_network_signature, opponents_and_foils | Vector cosine + set Jaccard for citations |
| 3 | **Argument profile** | argument_move_vector, novelty_mode, evidence_type_profile | Vector cosine + mode match |
| 4 | **Method** | method_stance, formalization_level | Stance field match + scalar distance |
| 5 | **Audience & Register** | audience_level, language_register, genre_position | Scalar distances + enum match |
| 6 | **Geopolitics** | geographic_affinity | Field-by-field string match |
| 7 | **Temporal** | temporal_position, article_readiness | Enum match + scalar distances |
| 8 | **Core identity** | title, abstract, problem, question, claims | Semantic similarity + recall |
| 9 | **Protected core** | protected_core, mutable_zones | Set overlap + quality judgment |
| 10 | **Unknown honesty** | unknowns, confidence | Precision of unknown marking |

### Per-vector scoring

For vector axes (discipline, school, argument_move, evidence_type):

```
cosine_similarity = dot(v1, v2) / (|v1| * |v2|)
```

Normalize by aligning dimension names first (semantic matching for
variant spellings of the same school/discipline).

### Per-set scoring

For citation sets (must_cite, typically_cite, etc.):

```
jaccard = |intersection| / |union|
```

### Aggregate

```
Total = weighted_mean(Group_1 ... Group_10)
```

Weights: Groups 1-3 (positioning) = 2x. Groups 4-7 = 1x. Groups 8-10 = 1x.

Score levels:
- **0.9+** — production-grade extraction
- **0.7-0.9** — good, specific axis groups need refinement
- **0.5-0.7** — acceptable MVP, significant gaps in positioning
- **< 0.5** — fundamental rework needed

### What this benchmark tests that v1 didn't

| Capability | v1 | v2 |
|-----------|----|----|
| Disciplinary positioning | 1 flat string | Weighted vector |
| School/tradition mapping | Not extracted | Full vector + citation signature |
| Conspicuous absence detection | Not extracted | Explicit axis |
| Opponent/foil identification | 1 list | Explicit vs implicit split |
| Argument move classification | Not extracted | 12-type weighted vector |
| Evidence type profile | Not extracted | 9-type weighted vector |
| Formalization level | Not extracted | 0.0–1.0 scalar |
| Jargon density | Not extracted | 0.0–1.0 scalar |
| Geographic positioning | Not extracted | Author + tradition + audience regions |
| Temporal field maturity | Not extracted | Explicit axis |
| Citation network topology | "theoretical_shoulders" list | must/typically/never/absence/bridge |
