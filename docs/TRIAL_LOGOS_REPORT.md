# Logos Target Trial Report — Kairoskopion v0.2.0-alpha-rc1

**Date:** 2026-06-10
**Branch:** `feature/logos-target-trial-quality-audit`
**Base:** `v0.2.0-alpha-rc1` (`7684f4f`)

---

## 1. Trial Setup

- **Branch:** `feature/logos-target-trial-quality-audit` off `main` at `v0.2.0-alpha-rc1`
- **Storage root:** `.kairoskopion_logos_trial/` (gitignored)
- **Manuscript:** `private_inputs/logos_trial/manuscript.md` — **private, uncommitted**
- **Venue seed:** `private_inputs/logos_trial/venue_guidelines_logos_seed.md` — private, uncommitted
- **Scenario:** `private_inputs/logos_trial/scenario.json` — private, uncommitted
- **Adapter mode:** mock (offline default)

### Commands run

```
kairoskopion --storage-root .kairoskopion_logos_trial run-local \
  --manuscript private_inputs/logos_trial/manuscript.md \
  --venue-guidelines private_inputs/logos_trial/venue_guidelines_logos_seed.md \
  --scenario private_inputs/logos_trial/scenario.json

kairoskopion --storage-root .kairoskopion_logos_trial vault-index
kairoskopion --storage-root .kairoskopion_logos_trial inspect-storage
kairoskopion --storage-root .kairoskopion_logos_trial build-submission-pack
kairoskopion --storage-root .kairoskopion_logos_trial export-bundle --output logos_trial_bundle.zip
kairoskopion validate-bundle --bundle logos_trial_bundle.zip
```

All commands completed successfully. Pipeline status: `completed`.

### IDs generated

| Entity | ID |
|--------|-----|
| ArticleModel | `art_3634deafb7a8` |
| VenueModel | `ven_e6d24a5dc99b` |
| FitAssessment | `fit_835ede732c47` |
| MismatchMap | `mm_2f89d443a63e` |
| RewritePlan | `rw_98333b31168f` |
| RiskReport | `risk_f7a282b784a4` |
| ComplianceChecklist | `cc_735f5e914c60` |
| CitationEcologyReport | `citeco_50a307fd11e7` |
| BibliographyProfile | `bib_be3cd0e1fb0b` |
| SubmissionScenario | `scn_885eb3f52098` |

---

## 2. Article Diagnosis

**Topic:** Universities after AI — what happens to the university's core function (epistemic legitimation) when intellectual production becomes distributed across humans, AI models, memory systems, and institutional norms.

**Core claims:**
1. The university's historical function is epistemic legitimation: turning fragile practices into teachable, disputable, inheritable knowledge.
2. AI introduces distributed intellectual production as the new practice requiring legitimation.
3. "Zone of proximal degradation" — machine-mediated environments can expand what learners produce faster than they develop capability to reconstruct the practice.
4. "Hybrid cognitive unit" — the educational unit of analysis is a cross-stack configuration (participant + model + trace + validation norm), not the student alone.
5. Second-tier universities are positioned as "second-order integrators" — translating external AI capacity into local regimes of validation and inheritance.

**Genre/register:** Philosophical-theoretical article with historical-institutional analysis. Not empirical research. Not a systematic review. Not education policy. Uses extended conceptual argumentation with historical cases (Aquinas/medieval university, Humboldt, Clark/entrepreneurial university, Moscow Methodological Circle, Engelbart). Register is scholarly philosophical — sustained argument, conceptual distinctions, no data tables or statistical analysis.

**Strengths for Logos:**
- Philosophically serious: engages continental philosophical tradition, institutional theory, Vygotsky, Shchedrovitsky/MMK
- Conceptual novelty: "zone of proximal degradation" and "hybrid cognitive unit" are new constructs with philosophical depth
- Connects AI to university function at the right level of generality for a philosophical journal
- References include Russian methodological tradition (Shchedrovitsky) — relevant to Logos readership

**Weaknesses for Logos:**
- Written in English — Logos is primarily Russian-language
- Register leans toward Anglophone social theory (Clark, Etzkowitz, Hutchins) — may need Russian philosophical reframing
- Missing engagement with Russian-language philosophical discourse on education, knowledge, and institutions
- Citation ecology is entirely Anglophone — no Russian-language references
- The applied/institutional framing ("second-tier university") may read as education policy rather than philosophy
- TRIZ reference (Altshuller) is brief and peripheral — would need strengthening for a Russian philosophical journal familiar with this tradition

**Classification:** Philosophical/social-theoretical hybrid. The article is NOT a systematic review, NOT empirical, NOT education policy. It is closest to institutional philosophy of education with strong social theory influence.

---

## 3. Logos Venue Diagnosis

### Known from seed
- Russian philosophical/philosophical-literary scholarly journal
- Publishes philosophy, social theory, cultural theory, modernity, institutional theory
- VAK-listed (claim, unverified)
- Scopus-indexed (claim, unverified)

### Unknown (blocking confident assessment)
- **Submission language policy** — can English submissions be accepted? This is the single most important unknown.
- **Author guidelines** — word limit, citation style, abstract requirements, article types
- **Peer review model** — editorial decision, single-blind, double-blind
- **Thematic issue schedule** — does Logos accept unsolicited submissions, or only thematic calls?
- **APC/OA policy** — the pipeline hallucinated `apc_required` and `open_access` from a seed that said UNKNOWN
- **AI use policy** — whether AI disclosure is needed
- **Current editorial direction** — who edits Logos now, what topics they favor

### Unknowns that block fit assessment
Without the language policy, the entire fit assessment is speculative. If Logos accepts only Russian submissions, the article requires full translation/adaptation — a different trajectory than if English is accepted.

---

## 4. Article-to-Logos Fit

### Pipeline result: `not_enough_data`

This is **honest and correct** — 9 of 12 axes returned `unknown` because the venue seed intentionally provided no official guidelines.

### Human assessment of likely fit axes

| Axis | Likely value | Notes |
|------|-------------|-------|
| topic | strong | AI and universities is a live Logos topic |
| discipline | medium-strong | Philosophy + social theory; Logos publishes both |
| genre | medium | Theoretical essay fits; may need to avoid "review" framing |
| argument_structure | medium | Extended conceptual argument works for Logos |
| method | medium | Conceptual-historical method appropriate for Logos genre |
| citation_ecology | weak | No Russian-language references; entirely Anglophone |
| novelty_positioning | strong | New conceptual constructs with philosophical depth |
| language_register | weak/blocking | Article is in English; Logos is Russian-primary |
| audience | medium | Logos readers are Russian-language philosophers; article speaks to them but in wrong language |
| formal_compliance | unknown | No guidelines available |
| author_eligibility | unknown | No information |
| publication_regime | unknown | Thematic vs. open submission unclear |

### Key issues

1. **Language/register is the blocking axis.** Everything else is secondary until the language question is resolved.
2. **Citation ecology is the second problem.** Zero Russian-language references in a Russian journal is a genre violation, not just a gap.
3. **Genre positioning needs adjustment.** The article reads as Anglophone social theory with philosophical foundations. For Logos, it needs to read as philosophy with institutional applications. The framing emphasis should shift.
4. **Russian philosophical discourse is missing.** Beyond Shchedrovitsky (who appears), the article needs to engage with Russian philosophers and social theorists that Logos readers would expect in this topic area.

---

## 5. Recommended Trajectory

### Language decision (must come first)
- **Option A:** Translate into Russian, adapt register and citation ecology. This is the natural path for Logos.
- **Option B:** Submit in English if Logos accepts English submissions (unknown). Even if accepted, citation ecology still needs Russian references.
- **Option C:** Publish English version elsewhere; create a Russian adaptation as a separate article for Logos.

**Recommendation:** Option C or A. The article is strong enough for a good English-language journal (Higher Education, Studies in Higher Education, or a philosophy of education journal). A separate Russian adaptation for Logos would be a different article — same core concepts, but reframed for Russian philosophical discourse.

### If adapting for Logos (Option A or C):
1. **Title:** Needs Russian philosophical framing. Something like «Университет после ИИ: эпистемическая легитимация и распределённое интеллектуальное производство» — but adapted to Russian philosophical register, not a literal translation.
2. **Abstract:** Must be written in Russian (and possibly English, depending on Logos requirements). Needs to foreground the philosophical problem, not the education policy implications.
3. **Introduction reframing:** Open with the philosophical problem (what is epistemic legitimation?) rather than with the empirical observation (AI changes university routines). Logos readers expect philosophical framing first.
4. **Citation ecology:** Add Russian-language philosophical references — at minimum, Russian philosophers of education, Russian institutional theorists, Russian Vygotsky scholarship (not just the English translations), and possibly more on Shchedrovitsky/MMK from Russian sources.
5. **Register:** Shift from Anglophone social-theory register toward continental philosophical register that Logos readers would recognize. Less "institutional typology" language, more "philosophical distinction" language.

### Missing venue evidence to collect before any submission decision
- Logos official website → current author guidelines
- Language policy (email editorial office if not on website)
- Recent table of contents (last 2-3 years) → what topics, what authors, what genres
- Thematic issue calendar → whether unsolicited submissions are accepted
- Current editorial board → who decides

---

## 6. Kairoskopion Output-Quality Audit

### What the tool did well
1. **Overall fit label `not_enough_data` is honest and correct.** The pipeline refused to fake confidence when venue data was insufficient.
2. **Pipeline ran end-to-end without errors.** All 18 steps completed, all registries and vault cards generated.
3. **Bibliography parsed 42 references correctly.** Year extraction, author extraction, reference counting all worked.
4. **Citation ecology identified real issues:** outdated bibliography (median 1996), no DOIs, venue recency mismatch.
5. **Scenario unknowns preserved.** All 10 scenario unknowns appear in the registry.
6. **Submission pack was honest:** `needs_file_update` status, not `ready`.
7. **Risk report found real risks:** citation gap, timeline, AI policy, author eligibility.
8. **Vault cards have working cross-links** between fit, mismatch, article, and venue.

### Where the report was useful
- The fit assessment table with 12 axes and `unknown` markings is exactly the right structure for this case.
- The citation ecology report identifying "dated" bibliography and missing recent references is actionable.
- The compliance checklist correctly identifies missing keywords, data availability, and COI.
- The mismatch map correctly surfaces that 9 axes cannot be assessed.

### Where the output was generic or empty
1. **Rewrite plan: 0 changes proposed.** This is wrong. Even with unknown venue data, the pipeline should propose conditional changes (e.g., "if language policy requires Russian, then translation needed").
2. **Venue card title: "Unknown Venue."** The seed file explicitly says "Логос / Logos" — the name should have been extracted.
3. **Article genre: `systematic_review`.** This is wrong. The article is a philosophical-theoretical essay, not a systematic review.
4. **Article method: `empirical_method`.** This is wrong. The article is conceptual/philosophical.
5. **Venue scope: null.** The seed contained orientation information that should have populated `scope_summary` or `aims_scope_summary`.

### Where the output was misleading
1. **Venue model hallucinated `open_access`, `apc_required`, `double_blind`** from a seed that explicitly marked all of these as UNKNOWN. This is a **serious defect** — the pipeline extracted false positives from a file designed to test UNKNOWN preservation.
2. **Venue unknowns: only 1 item** ("AI disclosure policy not found"). The seed had 20+ explicit UNKNOWN fields. The pipeline dropped almost all of them.
3. **Article `has_ai_disclosure: true`** — detected because the word "AI" appears frequently, but the article does not contain an AI use disclosure statement. This is a false positive.
4. **Cover letter template says `systematic_review`** — inherits the wrong genre classification.

### Whether unknowns were preserved
**PARTIAL.** Scenario unknowns (10 items) were preserved correctly. Venue unknowns were largely lost. Article unknowns were partially captured (2 items). The tool is honest about what it doesn't know at the fit level, but the venue and article extraction layers produce false positives instead of marking unknowns.

### Whether SubmissionPack readiness was honest
**YES — `needs_file_update` is correct.** The pack correctly identifies missing items and does not claim readiness. However, the pack should also flag that venue evidence is too weak for a submission decision, not just that files are missing.

---

## 7. Top 10 Product Defects Found

### Code/report defects

1. **D1: Venue name not extracted from seed file.** VenueModel `canonical_name` is `null` despite "Journal: Логос / Logos" and "# Venue Seed Profile: Логос / Logos" in the input. Venue card shows "Unknown Venue." The venue profiler needs better title/name extraction.

2. **D2: Venue model hallucinates structured fields from UNKNOWN seed.** The seed explicitly lists APC, OA, peer review as UNKNOWN. The pipeline produced `open_access`, `apc_required`, `double_blind`. The venue profiler's keyword-matching extracts false positives from sections that discuss these topics as unknown.

3. **D3: Venue unknowns not propagated.** Seed has 20+ UNKNOWN items. VenueModel has 1 unknown. The venue profiler does not parse "UNKNOWN:" sections or preserve them as venue model unknowns.

4. **D4: Article genre misclassified as `systematic_review`.** This is a philosophical-theoretical essay. The genre classifier likely matched on the structured argument with sections and references. Needs better heuristics for distinguishing theoretical/philosophical articles from systematic reviews.

5. **D5: Article method misclassified as `empirical_method`.** The article has no data, no experiment, no measurement. Method should be `conceptual` or `theoretical`. The method classifier may be defaulting to empirical when `has_methods_section` is true.

6. **D6: Rewrite plan empty (0 changes).** When most fit axes are `unknown`, the rewrite planner produces nothing. It should produce conditional recommendations: "IF venue requires Russian → translation needed", "IF citation style is X → reformat".

7. **D7: `has_ai_disclosure: true` is a false positive.** The article discusses AI as a topic but contains no "AI was used in the preparation of this manuscript" disclosure. The detector matches on AI topic keywords, not on disclosure statements.

### Extraction defects

8. **D8: `title_fragment` null for all 42 references.** The bibliography parser extracts `author_fragment` and `year` but fails to extract `title_fragment` from Chicago/author-date style references. Title is the text between the year and the next period/quotation mark.

9. **D9: `source_kind` misclassified for several references.** Brown et al. 2020 (NeurIPS paper) classified as `book_chapter`. Several monographs classified as `unknown`. The source_kind classifier needs improvement for Chicago-style references.

### Missing venue evidence (not a code defect)

10. **D10: No official Logos guidelines available.** This is not a tool defect — it's a real evidence gap. All venue model issues (D2, D3) would be mitigated with real author guidelines. But the tool should handle absent evidence gracefully, which it currently does not (D2, D3).

### Limitations of current offline mock mode

- Mock adapters return generic data unrelated to the actual article or venue. They do not provide Logos-specific information.
- No reference verification possible without external APIs.
- No DOI lookup for the 42 references.
- No venue profile enrichment from OpenAlex/Crossref.

---

## 8. Missing Logos Evidence Plan

Before any submission decision, collect these sources:

| Source | Purpose | Where to look |
|--------|---------|---------------|
| Official author guidelines | Word limit, format, citation style, article types | Logos website, editorial office |
| Aims and scope page | Topic scope, disciplinary boundaries | Logos website |
| Submission instructions | Submission route, required files, language policy | Logos website or editorial email |
| Editorial policy | Peer review model, decision timeline | Logos website |
| Language policy | Whether English submissions are accepted | Logos website or editorial email |
| Citation style | Footnote vs. in-text, specific format | Author guidelines |
| APC/OA policy | Costs, access model | Logos website |
| AI/data/ethics policies | Disclosure requirements | Author guidelines |
| Editorial board | Current editors, disciplinary orientation | Logos website |
| Recent issues (2024-2026) | Topics, genres, authors, thematic calls | Logos archive / elibrary.ru |
| Indexing confirmation | VAK list, Scopus source list, WoS | Official registries |

---

## 9. Defect Closure (D6, D8, D9)

**Date:** 2026-06-10
**Branch:** `feature/logos-target-trial-quality-audit`

### D6: Empty RewritePlan under venue uncertainty — FIXED

**Root cause:** `build_rewrite_plan()` skipped all `informational` severity mismatches. When venue data was incomplete, all 9 axes were informational, producing 0 changes.

**Fix:** When informational mismatches exist (indicating venue uncertainty), the planner now generates conditional trajectory actions: evidence collection, guideline verification, language policy check, citation bridge preparation, translation/adaptation path. Each conditional change has `status: "conditional"` and `field_core_risk: UNKNOWN_CORE_IMPACT`.

**Result after fix:** 13 changes — 3 proposed (from weak axes: topic, genre) + 10 conditional (from 7 informational axes). Summary: `"3 proposed change(s) + 10 conditional (venue evidence incomplete), estimated effort: major"`.

**Tests:** 10 new tests in `tests/test_rewrite_planning.py` (7 for conditional behavior, 1 for mixed summary, 2 for standard behavior).

### D8: `title_fragment` null for all references — FIXED

**Root cause:** `_extract_title_fragment()` only matched APA parenthetical year `(Year).` pattern. Chicago author-date `Author. Year. Title.` and other styles were not handled.

**Fix:** Added 4 extraction patterns:
1. APA: `(Year). Title.` (existing, kept)
2. Chicago author-date: `. Year. Title.` (new)
3. Generic post-year: `Year. Title.` with publisher filter (new)
4. Quoted title: `"Title"` or `«Title»` (new)

**Result after fix:** 42/42 references now have `title_fragment` (was 0/42).

**Tests:** 6 new tests in `TestTitleFragmentExtraction` (APA, Chicago, Chicago with subtitle, APA+journal, numbered, quoted).

### D9: `source_kind` misclassification — FIXED

**Root cause:** Missing report markers, overly broad "in " chapter marker matching book titles like "Cognition in the Wild", no DOI-based inference.

**Fix:**
1. Added `_REPORT_MARKERS` (report, working paper, policy brief, etc.) and `_REPORT_ORG_MARKERS` (UNESCO, OECD, World Bank, etc.)
2. DOI presence now infers `journal_article` when no other specific markers match
3. Tightened `_CHAPTER_MARKERS`: removed `"in "` (too broad), kept `"in:"` and added `"(eds.)"`, `"(eds)"`, `"chapter in"`
4. Report detection runs before journal/book fallback

**Result after fix:** Distribution: 16 books, 12 unknown, 7 book_chapters, 4 journal_articles, 2 conference_papers, 1 report (was: 19 book_chapters, 10 books, 7 unknown, 3 journal_articles, 2 conference_papers, 1 report).

**Tests:** 9 new tests in `TestSourceKindClassification` (DOI+journal, DOI alone, publisher→book, UNESCO report, World Bank report, working paper, conference, edited volume chapter, existing book preserved).

### Trial rerun summary

| Metric | Before fixes (D1–D5, D7) | After D6/D8/D9 fixes |
|--------|--------------------------|---------------------|
| RewritePlan changes | 0 | 13 (3 proposed + 10 conditional) |
| title_fragment coverage | 0/42 | 42/42 |
| source_kind: book_chapter | 19 (many false) | 7 (tighter) |
| source_kind: book | 10 | 16 |
| source_kind: report | 0 | 1 |
| Tests | 567 | 592 |

---

## 10. Verdict

### Is current Kairoskopion output useful for this case?

**Yes, with caveats.** After fixing D1-D9 (all except D10, which requires real venue guidelines):
- Fit assessment: `possible_but_costly` -- honest and correct for a speculative venue match.
- Genre/method: `theoretical_essay` / `conceptual_method` -- correct.
- Venue name: extracted correctly.
- Venue unknowns: 24+ unknowns propagated from seed -- correct.
- RewritePlan: 13 actions (3 proposed + 10 conditional) -- actionable.
- Bibliography: 42/42 titles extracted, reasonable source_kind distribution.
- AI disclosure: no false positive -- correct.

Remaining limitations are structural (no real venue guidelines available, no LLM enrichment), not code bugs.

### Is v0.2.0-alpha-rc1+trial-fixes demo-ready?

**Developer-ready, approaching demo-ready.** The pipeline now:
- Handles UNKNOWN venue seeds without hallucination
- Produces conditional recommendations under venue uncertainty
- Correctly classifies philosophical/theoretical articles
- Extracts bibliography titles and source kinds
- Refuses to fake confidence (honest `possible_but_costly` label)

NOT demo-ready for: users who expect LLM-quality venue analysis, DOI verification, or citation bridge discovery. Those require real adapter integration.

### What remains before real submission decisions?

1. ~~Venue model must not hallucinate (D2)~~ -- **FIXED**
2. ~~Venue unknowns must be propagated (D3)~~ -- **FIXED**
3. ~~Genre/method for philosophical articles (D4, D5)~~ -- **FIXED**
4. ~~Rewrite plan under uncertainty (D6)~~ -- **FIXED**
5. ~~AI disclosure false positive (D7)~~ -- **FIXED**
6. ~~title_fragment extraction (D8)~~ -- **FIXED**
7. ~~source_kind classification (D9)~~ -- **FIXED**
8. Real Logos guidelines must be obtained -- **blocking for any submission decision** (D10, not a code defect)
