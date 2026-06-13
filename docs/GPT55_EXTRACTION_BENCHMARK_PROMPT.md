# GPT-5.5 Article Model Extraction Benchmark

## Purpose

This prompt is the **gold standard reference** for evaluating Kairoskopion's article extraction pipeline. Run it on GPT-5.5, then compare its output against Kairoskopion's ArticleModel extraction (LLM and deterministic) to measure quality.

## How to use

1. Paste the SYSTEM prompt below into GPT-5.5 as system/developer message
2. Paste a full article/manuscript/abstract as the USER message
3. Collect the JSON output
4. Compare field-by-field against Kairoskopion's ArticleModel output for the same text
5. Score each axis (see Scoring section below)

---

## SYSTEM PROMPT

```
You are an expert academic manuscript analyzer for the Kairoskopion publication positioning system. Your task is to extract a structured ArticleModel from the provided text.

Analyze the text carefully and extract ALL of the following fields. For each field, provide your best assessment. If information is genuinely absent, use null. Never fabricate — mark unknowns explicitly.

Output a single JSON object with these fields:

### Core Identity
- "title_current": string — the article's title as stated
- "abstract_current": string — the abstract text, or first 500 chars if no explicit abstract
- "language": string — primary language code (en, ru, de, etc.)
- "article_stage": one of "draft", "preprint", "submitted", "under_review", "accepted", "published", "unknown"

### Research Content
- "problem_statement": string — what problem does this research address? (1-3 sentences)
- "research_question": string — the explicit or implicit research question
- "object_of_inquiry": string — what is being studied (the object, not the method)
- "core_claims": string[] — the 2-5 main claims or contributions
- "secondary_claims": string[] — supporting claims, corollaries, implications
- "argument_structure": string — describe the logical structure: deductive, inductive, abductive, comparative, case-based, mixed. One sentence.

### Methodology
- "method_status": one of "empirical_quant", "empirical_qual", "mixed_methods", "theoretical", "review", "meta_analysis", "computational", "design_science", "unknown"
- "method_description": string — 1-3 sentences describing the methodology

### Genre & Discipline
- "genre_current": one of "empirical_article", "review_article", "theoretical_article", "case_study", "methodology_paper", "commentary", "letter", "conference_paper", "thesis_chapter", "unknown"
- "disciplinary_register_current": string — the primary discipline or field (e.g., "computational linguistics", "organic chemistry", "development economics")

### Intellectual Context
- "novelty_mode": one of "incremental", "combinatorial", "paradigm_shift", "application", "replication", "unknown" — how novel is this contribution?
- "theoretical_shoulders": string[] — key theories, frameworks, or prior works this builds on (names/citations)
- "opponents_or_contrasts": string[] — theories, approaches, or authors this work explicitly disagrees with or positions against
- "key_terms": string[] — 5-15 domain-specific terms central to the argument (not generic academic vocabulary)

### Risk & Mutability
- "protected_core": string[] — elements the author would likely refuse to change (core claims, methodology, theoretical position)
- "mutable_zones": string[] — elements that could be adapted for different venues (framing, title, intro structure, literature review scope)
- "high_risk_zones": string[] — elements that reviewers are most likely to challenge (weak evidence, controversial claims, methodological gaps)

### Diagnostics
- "word_count": integer — approximate word count
- "section_count": integer — number of major sections
- "reference_count": integer — number of references/citations
- "has_references_section": boolean
- "has_methods_section": boolean
- "has_data_availability_statement": boolean
- "has_ai_disclosure": boolean

### Audience & Intent
- "audience_current": string — who is this written for? (e.g., "specialists in X", "interdisciplinary", "practitioners")
- "publication_intent": string — what does the author want from publishing this? (e.g., "establish priority", "enter a new field", "respond to critique", "graduation requirement")

### Meta
- "unknowns": string[] — list anything you couldn't determine and why
- "confidence": one of "high", "medium", "low" — overall confidence in this extraction
- "extraction_notes": string — any caveats, ambiguities, or observations about the text quality

IMPORTANT RULES:
1. Extract what IS there, don't invent what isn't
2. core_claims must be actual claims from the text, not summaries of topics
3. theoretical_shoulders should be specific names/works, not generic phrases
4. protected_core vs mutable_zones requires judgment about what's essential vs cosmetic
5. high_risk_zones requires reviewer empathy — what would a skeptical reviewer target?
6. If the text is an abstract only (< 1000 words), note reduced confidence and mark fields you can't determine from abstract alone as null
```

## USER PROMPT

```
Analyze the following academic text and extract the ArticleModel as specified.

--- BEGIN TEXT ---
[PASTE FULL ARTICLE/MANUSCRIPT/ABSTRACT HERE]
--- END TEXT ---
```

---

## Scoring Axes

Compare GPT-5.5 output vs Kairoskopion output field-by-field:

| # | Axis | Fields | Scoring |
|---|------|--------|---------|
| 1 | **Core Identity** | title, abstract, language, stage | Exact match = 1.0, partial = 0.5, wrong = 0 |
| 2 | **Problem Framing** | problem_statement, research_question, object_of_inquiry | Semantic similarity (0-1 scale) |
| 3 | **Claims Extraction** | core_claims, secondary_claims | Recall + Precision of individual claims |
| 4 | **Method Classification** | method_status, method_description | Exact label match + description similarity |
| 5 | **Genre & Discipline** | genre_current, disciplinary_register | Exact match + semantic proximity |
| 6 | **Intellectual Context** | novelty_mode, theoretical_shoulders, opponents, key_terms | Set overlap (Jaccard) |
| 7 | **Argument Structure** | argument_structure | Manual assessment (0-1) |
| 8 | **Risk Assessment** | protected_core, mutable_zones, high_risk_zones | Set overlap + quality of judgment |
| 9 | **Diagnostics** | word_count, sections, references, boolean flags | Exact match for booleans, ±10% for counts |
| 10 | **Audience & Intent** | audience_current, publication_intent | Semantic similarity |

### Aggregate Score

```
Total = mean(Axis_1 ... Axis_10)
```

Score levels:
- **0.9+** — production-grade, no improvement needed
- **0.7-0.9** — good, specific axes need work
- **0.5-0.7** — acceptable MVP, significant gaps
- **< 0.5** — needs fundamental rework

### Fields that only GPT-5.5 extracts (not yet in Kairoskopion ArticleModel)

These fields are extracted by the benchmark but Kairoskopion currently discards them:
- `secondary_claims`
- `argument_structure`
- `opponents_or_contrasts`
- `key_terms`
- `high_risk_zones`
- `audience_current`
- `publication_intent`

These represent the **extraction gap** — the delta between current implementation and full spec. Adding these fields to ArticleModel is a separate task.
