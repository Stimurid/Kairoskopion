# Mavrinsky venue training priors — DISCOVERY SEED, NOT MODEL

**Status:** training-knowledge inference dump. **Not a verified venue
corpus.** Not a finished `VenueProfilePackage`. Not signed-off gold.

**Provenance of every field below:** `INFERENCE_FROM_TRAINING_DATA` —
LLM training corpus, cutoff January 2026, no live verification. Every
"likely publisher" / "likely scope" line is a hypothesis to be checked
against the journal's own page (source category A), publisher page (B),
or open registries (C: DOAJ, OpenAlex, Crossref, Scimago).

**Anti-pattern compliance:**

- **AP1** (rubric §3, *aims_scope upgraded to FACT*): NOT triggered.
  No scope claim below carries `formal_page` authority; all are tagged
  `inference_from_training`.
- **AP2** (*indexing_claim = fit*): NOT triggered. Quartiles are
  marked `UNKNOWN_2026` deliberately. Where I have a stale recollection
  of historical quartile, it is suffixed with the year as a hint, not
  a claim.
- **AP3** (*editorial board as psychology*): NOT triggered. No board
  is profiled here. Layer-7 work is deferred to live discovery.
- **AP4** (*full-text source = metadata source*): not applicable —
  no full text touched.
- **VAP1** (Mavrinsky gold §5, *Lacan-as-shoulder*): venues with
  psychoanalytic core tradition are explicitly **flagged**, not
  upgraded to fit.
- **VAP2** (*Simondon-hallucination*): no "must-cite Simondon" line.
  Venues where Simondon canon is a known expectation are tagged
  `requires_citation_bridge`, not "fit".
- **VAP3** (*HCI fit upgraded*): HCI venues below are marked
  `SIBLING_ONLY`, never "fit on current article".
- **VAP4** (*Generic STS reframe without core preservation*): STS
  venues below are marked `SIBLING_ONLY`, never "reframe-and-submit".
- **VAP5** (*Philosophy & Technology Q1 = strong*): Phil&Tech is in
  the list, but **not** as "strong". Listed with explicit caveat.
- **VAP6** (*RU-language pool under international scenario*): no
  RU-regime venues here. Russian-language venues (Логос, Социология
  Власти, Stasis-RU, etc.) are deferred to a separate RU-scenario
  seed dump.

**How to use this file:**

1. Treat each entry as a **candidate for verification**, not as a
   ranked recommendation.
2. Before any fit claim, run live source acquisition (canon §3,
   categories A–C minimum) on the entry's name + likely publisher.
3. Identity normalisation: `services/venue_candidate_screening.py`
   already handles ISSN/name dedup — feed these names through it.
4. Discard or downgrade any entry where live verification disagrees
   with the inference here. **Stale memory loses to live source.**
5. Once verified, candidates feed `VenueProfilePackage` builder
   (VF-C2 → VF-C4 once the code lands).

**Inputs that drove cluster assignment:**

- Article-side gold:
  `benchmarks/golden/mavrinsky_article_side_gold.md`
  (FPM coordinates: continental_philosophy 0.75,
  philosophy_of_technology 0.55, media_philosophy 0.55,
  interface_theory 0.45, digital_culture 0.30, STS 0.15, HCI 0.10;
  tribes Deleuze/Guattari 0.80, Agamben 0.70, Foucault 0.65,
  Heidegger 0.20, Lacan −0.35; argument_move
  concept_reconstruction + concept_introduction; evidence
  theoretical_argument 0.85; method philosophical_analysis,
  low specificity, no empirical component).
- Venue-side gold:
  `benchmarks/golden/mavrinsky_venue_side_gold.md` (three target
  clusters: CPT, STS-platform, HCI-design + their decision labels).
- Canonical funnel:
  `docs/VENUE_FUNNEL_AND_PROFILE_PACKAGE_V1.md`
  (source allowlist A–J, authority discipline).

---

## Cluster A — CPT (continental philtech / media philosophy)

**Decision label per venue-side gold §3:** `strong_candidate` or
`possible_but_costly` depending on per-venue envelope alignment.

**Pathway link (article-side gold pathway 1, continental media
philosophy):** native home. **Low core-risk.** First-line targets.

### A1. Philosophy & Technology
- **publisher_inference:** Springer (training, high confidence)
- **why_picked:** declared philosophy-of-technology scope; historical
  presence of continental and analytic phil-tech both
- **risks:** VAP5 (do not auto-label as strong fit just because it's
  the obvious "philosophy of technology" journal); tribe lean
  unknown — may currently lean Simondon-Stiegler-Hui (requiring
  VAP2 citation bridge) rather than Deleuze-Foucault-Agamben
- **sibling_only:** no
- **UNKNOWN_NOT_VERIFIED:** quartile_2026, indexing_2026,
  current_EB_tribe_lean, AI_policy, APC, accept_rate,
  current_article_type_gates

### A2. Techne: Research in Philosophy and Technology
- **publisher_inference:** Society for Philosophy and Technology
  (training, OA likely)
- **why_picked:** society journal for SPT; broader tradition mix
  than Phil&Tech; OA reduces APC friction
- **risks:** smaller readership; may be tribe-narrower than its
  parent society
- **sibling_only:** no
- **UNKNOWN:** quartile_2026, indexing_2026, current_OA_terms,
  current_scope

### A3. Foundations of Science
- **publisher_inference:** Springer (training)
- **why_picked:** broader philosophy-of-science scope occasionally
  hosting phil-tech and continental epistemology
- **risks:** may want explicit science-anchor; continental
  argumentation has uneven uptake
- **sibling_only:** no
- **UNKNOWN:** quartile_2026, current_continental_lean

### A4. Continental Philosophy Review
- **publisher_inference:** Springer (training)
- **why_picked:** explicit continental-philosophy venue; strong tribe
  fit (Deleuze/Foucault/Agamben canon at home)
- **risks:** less philosophy-of-technology framing; may want pure
  text-with-philosopher rather than artefact-with-philosopher
- **sibling_only:** no
- **UNKNOWN:** openness_to_interface_theory_framing, current_EB

### A5. Angelaki: Journal of the Theoretical Humanities
- **publisher_inference:** Routledge / Taylor & Francis (training)
- **why_picked:** strong Deleuze-friendly theoretical-humanities
  venue; concept-introduction is a recognised move here
- **risks:** prefers humanities/literary anchor over technical
  artefact; may want explicit theoretical-humanities framing
- **sibling_only:** no
- **UNKNOWN:** current_scope_drift, indexing_2026

### A6. Cultural Politics
- **publisher_inference:** Duke University Press (training)
- **why_picked:** continental political theory, Deleuze-friendly,
  cultural-politics of technology line
- **risks:** prefers a political-stakes line that the current article
  draft may not foreground enough
- **sibling_only:** no
- **UNKNOWN:** current_rhythm, accept_rate

### A7. Body & Society
- **publisher_inference:** Sage (training)
- **why_picked:** Foucault/Deleuze/Agamben in embodiment register;
  interface-as-dispositif sits adjacent to body-society line
- **risks:** wants body/embodiment anchor; interface-without-body may
  read as not-quite-right
- **sibling_only:** no
- **UNKNOWN:** quartile_2026, current_scope

### A8. Substance: A Review of Theory and Literary Criticism
- **publisher_inference:** Johns Hopkins University Press (training)
- **why_picked:** historical Deleuze/Guattari venue; theoretical
  humanities; strong tribe fit
- **risks:** literary anchor traditionally expected; technical
  artefact may need framing as cultural object
- **sibling_only:** no
- **UNKNOWN:** current_scope_drift

### A9. Deleuze and Guattari Studies
- **publisher_inference:** Edinburgh University Press (training)
- **why_picked:** explicit Deleuze/Guattari venue; concept work is
  the genre
- **risks:** wants rigorous engagement with D&G primary texts; "uses
  Deleuze to talk about X" risks being read as decorative; possibly
  high-self-citation-of-canon expectation
- **sibling_only:** no
- **UNKNOWN:** openness_to_applied_DG_work, current_EB

### A10. Theory & Event
- **publisher_inference:** Johns Hopkins University Press (training)
- **why_picked:** political philosophy, Foucault/Agamben aligned;
  event/dispositif vocabulary at home
- **risks:** political event-anchor expected; interface-as-dispositif
  needs to land politically, not just analytically
- **sibling_only:** no
- **UNKNOWN:** current_scope, openness_to_technical_artefact

### A11. Postmodern Culture
- **publisher_inference:** Johns Hopkins University Press (training, OA)
- **why_picked:** continental humanities, post-structuralist; OA
- **risks:** rhythm slowed in recent training data; scope drift
  unknown
- **sibling_only:** no
- **UNKNOWN:** current_activity_level, indexing_2026

### A12. Parrhesia: A Journal of Critical Philosophy
- **publisher_inference:** OA, possibly Open Humanities Press affiliate
  (training, low confidence on publisher)
- **why_picked:** explicitly critical philosophy, Foucault-aligned name
- **risks:** small venue; publication cycle may be slow; quartile
  likely absent from Scimago
- **sibling_only:** no
- **UNKNOWN:** current_publisher, indexing_status_at_all, rhythm

### A13. Parallax
- **publisher_inference:** Taylor & Francis (training)
- **why_picked:** theoretical humanities, interdisciplinary theory
- **risks:** thematic-issue-driven; needs CFP match
- **sibling_only:** no
- **UNKNOWN:** current_thematic_calendar, scope

### A14. Diacritics
- **publisher_inference:** Johns Hopkins University Press (training)
- **why_picked:** theory venue, continental tradition
- **risks:** rhythm may have slowed; theoretical-humanities anchor
- **sibling_only:** no
- **UNKNOWN:** current_activity_level

### A15. Phenomenology and the Cognitive Sciences
- **publisher_inference:** Springer (training)
- **why_picked:** phenomenology + cognitive science, partial overlap
  with media-philosophy-of-mind work; interface-as-cognitive-apparatus
  bridge possible
- **risks:** wants explicit phenomenological method; may push toward
  Husserl/Merleau-Ponty canon and away from Deleuze
- **sibling_only:** no
- **UNKNOWN:** continental_phil_tech_uptake_currently, EB_lean

---

## Cluster B — Adjacent Media studies / digital culture

**Pathway link (article-side gold pathway 3, media interface theory):**
medium fit, requires citation bridge to media canon (Manovich,
Galloway, platform mediation). **Medium core-risk** because adding the
media-canon shoulder is doable without altering the desire/dispositif
core.

By FPM coordinates this cluster is **as close to native as Cluster A**
(media_philosophy 0.55, interface_theory 0.45). It is "adjacent" only
relative to disciplinary labelling, not to envelope distance.

### B1. Theory, Culture & Society
- **publisher_inference:** Sage (training)
- **why_picked:** interdisciplinary theory; published Foucault/Deleuze/
  Agamben-adjacent for decades; interface-as-cultural-form welcomed
- **risks:** high competition; possibly wants more explicit sociological
  anchor; envelope wide but bar high
- **sibling_only:** no
- **UNKNOWN:** quartile_2026, accept_rate, current_EB

### B2. Media, Culture & Society
- **publisher_inference:** Sage (training)
- **why_picked:** continental media philosophy welcome; Foucault/
  cultural-studies canon at home
- **risks:** prefers media/culture anchor over abstract interface theory
- **sibling_only:** no
- **UNKNOWN:** quartile_2026, current_scope

### B3. Convergence: The International Journal of Research into New Media Technologies
- **publisher_inference:** Sage (training)
- **why_picked:** new media research, sometimes continental
- **risks:** more empirical-sociological than theoretical-philosophical
- **sibling_only:** no
- **UNKNOWN:** current_theoretical_appetite

### B4. Media Theory journal
- **publisher_inference:** OA (training, low confidence on host)
- **why_picked:** explicitly theoretical media studies; continental-
  friendly by editorial intent (per training)
- **risks:** young venue; indexing minimal
- **sibling_only:** no
- **UNKNOWN:** indexing_2026, current_EB, rhythm

### B5. International Journal of Cultural Studies
- **publisher_inference:** Sage (training)
- **why_picked:** cultural studies of media; tribe-permissive
- **risks:** cultural-studies anchor (empirical-cultural) may be
  expected over pure philosophy
- **sibling_only:** no
- **UNKNOWN:** quartile_2026, scope

### B6. Necsus: European Journal of Media Studies
- **publisher_inference:** OA, Amsterdam University Press affiliate
  (training, medium confidence)
- **why_picked:** European continental media studies; thematic issues
  often phil-tech adjacent
- **risks:** thematic-issue-bound; CFP match needed
- **sibling_only:** no
- **UNKNOWN:** thematic_calendar, indexing_2026

### B7. New Media & Society
- **publisher_inference:** Sage (training)
- **why_picked:** wide media-tech-society scope
- **risks:** empirically inclined; theoretical-only essay may struggle;
  borders STS-platform territory which triggers VAP3
- **sibling_only:** maybe — depends on whether reframe stays in
  media-philosophy register or drifts to platform empirics
- **UNKNOWN:** current_theoretical_quota

### B8. Television & New Media
- **publisher_inference:** Sage (training)
- **why_picked:** media studies; some theoretical openness
- **risks:** medium-anchor (TV, specific platforms) expected; pure
  interface theory may not land
- **sibling_only:** no
- **UNKNOWN:** current_continental_lean

---

## Cluster C — Adjacent Critical theory / political philosophy

**Pathway link (article-side gold, partial bridge from pathway 1):**
strong tribe match (Deleuze/Foucault/Agamben canon native). **Low
core-risk** in tribe, medium core-risk if argument-move is asked to
become more political and less artefact-focused.

### C1. Critical Inquiry
- **publisher_inference:** University of Chicago Press (training)
- **why_picked:** top humanities theory venue; continental canon at
  home; interface-as-form-of-life fits the genre
- **risks:** extreme selectivity; needs a strong novelty claim and
  excellent prose; may want broader humanities framing over technical
  specificity
- **sibling_only:** no
- **UNKNOWN:** accept_rate, current_EB, AI_policy

### C2. boundary 2
- **publisher_inference:** Duke University Press (training)
- **why_picked:** post-structuralist theory venue; Foucault/Deleuze
  tradition; strong tribe match
- **risks:** prefers literary/cultural-political anchor; technical
  artefact framing may need cultural-political stake
- **sibling_only:** no
- **UNKNOWN:** current_scope, accept_rate

### C3. Constellations
- **publisher_inference:** Wiley (training)
- **why_picked:** critical theory and democratic political philosophy
- **risks:** Habermas/Frankfurt school lineage may dominate; Deleuze/
  Foucault less native here
- **sibling_only:** no
- **UNKNOWN:** current_continental_balance

### C4. Critical Horizons
- **publisher_inference:** Taylor & Francis (training)
- **why_picked:** critical theory journal; openness to continental
  political philosophy
- **risks:** small venue; may want Frankfurt-school anchor
- **sibling_only:** no
- **UNKNOWN:** indexing_2026, current_scope

### C5. Political Theory
- **publisher_inference:** Sage (training)
- **why_picked:** political philosophy core; Foucault/Agamben canon
  recognised
- **risks:** wants explicit political claim; interface-as-political-form
  needs to land politically; argument-move expectation closer to
  political-argument than concept-introduction
- **sibling_only:** maybe — depends on political framing of interface
- **UNKNOWN:** current_continental_lean

### C6. Philosophy & Social Criticism
- **publisher_inference:** Sage (training)
- **why_picked:** continental political philosophy; Foucault-Agamben
  tradition welcomed
- **risks:** wants explicit social-critical stake
- **sibling_only:** no
- **UNKNOWN:** quartile_2026

### C7. Telos
- **publisher_inference:** Telos Press (training)
- **why_picked:** critical-theory tradition with continental openness
- **risks:** ideological scope shift in recent decades (training-era
  uncertainty); may not match current article register
- **sibling_only:** no
- **UNKNOWN:** current_editorial_direction, indexing_2026

### C8. European Journal of Political Theory
- **publisher_inference:** Sage (training)
- **why_picked:** European political philosophy; continental-friendly
- **risks:** politics-anchor required
- **sibling_only:** no
- **UNKNOWN:** quartile_2026, current_scope_balance

---

## Cluster D — Adjacent Aesthetics / art-theory / philosophy of art

**Pathway link:** lowers VAP3/VAP4 risks entirely (no HCI fit upgrade,
no STS reframe). "Generous interface" lands as aesthetic-political
concept rather than as design-affordance, preserving protected core.

### D1. October
- **publisher_inference:** MIT Press (training)
- **why_picked:** top contemporary art theory venue; continental;
  Foucault/Agamben tradition; interface-as-aesthetic-political-form
  is the genre
- **risks:** historically art-historical anchor expected; pure
  philosophy-of-technology may be off-genre
- **sibling_only:** no — but framing must shift toward aesthetics
- **UNKNOWN:** current_scope_drift, accept_rate

### D2. e-flux journal
- **publisher_inference:** e-flux (training, OA)
- **why_picked:** contemporary art-theory-philosophy crossover;
  continental, Agamben-friendly; essay form welcomed
- **risks:** invitation-driven curation; submission path unclear
- **sibling_only:** no
- **UNKNOWN:** open_submission_path, peer_review_model_currently

### D3. Journal of Aesthetics and Phenomenology
- **publisher_inference:** Routledge / Taylor & Francis (training)
- **why_picked:** continental aesthetics with phenomenology bridge
- **risks:** prefers explicit phenomenological method (Husserl/
  Merleau-Ponty); Deleuze-only article may need a phenomenology
  shoulder added
- **sibling_only:** no
- **UNKNOWN:** quartile_2026, current_EB

### D4. NOEMA
- **publisher_inference:** Berggruen Institute (training)
- **why_picked:** long-form philosophy-tech-art crossover; continental-
  friendly
- **risks:** magazine more than journal; peer review structure unclear
- **sibling_only:** no
- **UNKNOWN:** peer_review_status, indexing_status

### D5. Estetika: The European Journal of Aesthetics
- **publisher_inference:** Charles University / OA (training, medium
  confidence)
- **why_picked:** European aesthetics with continental openness
- **risks:** explicit aesthetics framing required
- **sibling_only:** no
- **UNKNOWN:** indexing_2026, current_scope

---

## Cluster E — STS-platform (sibling-manuscript zone)

**Pathway link (article-side gold pathway 4, STS / platform studies):**
**sibling manuscript** per article-side gold. **High core-risk** for
the current article without case work and platform empirics. **Do
not submit the current draft as-is to any of these.** Listed for
sibling-line planning only.

### E1. Social Studies of Science
- **publisher_inference:** Sage (training)
- **status:** SIBLING_ONLY. VAP4 hard-FAIL if attempted as-is.
- **UNKNOWN:** sibling-side fit details

### E2. Science, Technology, & Human Values
- **publisher_inference:** Sage (training)
- **status:** SIBLING_ONLY. VAP4.
- **UNKNOWN:** sibling fit

### E3. Engaging Science, Technology, and Society
- **publisher_inference:** Society for Social Studies of Science (4S)
  (training, OA)
- **status:** SIBLING_ONLY. VAP4. Lower bar than SSS but same tribe.

### E4. Big Data & Society
- **publisher_inference:** Sage (training, OA)
- **status:** SIBLING_ONLY. Platform studies. VAP3 risk if HCI/data
  fit upgraded.

### E5. Computational Culture
- **publisher_inference:** OA (training, low confidence on host)
- **status:** SIBLING_ONLY. Software studies; some continental
  openness, but core anchor remains software-as-empirical-object.

---

## Cluster F — HCI-design (sibling-manuscript zone)

**Pathway link (article-side gold pathway 5, HCI/design theory):**
**sibling manuscript** per article-side gold. **High core-risk** —
generous interface easily reduces to "good UX" if HCI canon is
adopted without preserving Deleuze/Agamben dispositif core. **VAP3
hard-FAIL** if listed as "fit" on current article.

### F1. Design Issues
- **publisher_inference:** MIT Press (training)
- **status:** SIBLING_ONLY. Most continental-friendly HCI/design
  venue; but still requires design-canon shoulder.

### F2. Human–Computer Interaction (journal)
- **publisher_inference:** Taylor & Francis (training)
- **status:** SIBLING_ONLY. Empirical HCI. VAP3.

### F3. International Journal of Human-Computer Studies
- **publisher_inference:** Elsevier (training)
- **status:** SIBLING_ONLY. Empirical HCI. VAP3.

### F4. First Monday
- **publisher_inference:** University of Illinois Chicago (training, OA)
- **status:** SIBLING_ONLY. Broader digital-culture register; lower
  HCI-empirical demand; possible bridge venue between Cluster B and
  the HCI sibling line.

---

## Summary

- **Cluster A (CPT — native home):** 15 candidates. Layer-5 (journal
  envelope) acquisition is the first live step. Then layer-7
  (editorial board) to disambiguate tribe lean within continental
  philosophy (Deleuze-Foucault-Agamben vs. Simondon-Stiegler-Hui vs.
  Heideggerian technics — all "continental" but different envelopes).
- **Cluster B (Media / digital culture):** 8 candidates. **By
  FPM-axis distance these are as close as Cluster A.** Treating them
  as "adjacent" rather than "primary" is a labelling convenience,
  not a fit verdict.
- **Cluster C (Critical theory / political):** 8 candidates. Strong
  tribe match; medium core-risk depending on whether interface needs
  to become more political to land.
- **Cluster D (Aesthetics / art-theory):** 5 candidates. The path
  with **lowest VAP risk** because aesthetic-political framing of
  generous interface preserves the Deleuze/Agamben core natively.
- **Cluster E (STS-platform):** 5 candidates. **SIBLING_ONLY.**
- **Cluster F (HCI-design):** 4 candidates. **SIBLING_ONLY.**

**Total: 45 venues.** (15 + 8 + 8 + 5 + 5 + 4)

**Not in this dump (deliberately):**

- RU-language pool (Логос, Социология Власти, Stasis-RU, etc.) —
  VAP6 applies under the international scenario; needs a separate
  RU-scenario seed.
- Q3/Q4 venues — not requested.
- Specifically Russian-state-mandated VAK list — separate doc.
- Predatory or risk-flagged venues — would need explicit risk-flag
  field which is not in the schema yet.
- All anthropology (general): Mavrinsky article is not ethnographic
  or theory-of-culture-as-form; interface is not an anthropological
  object of inquiry in this draft.
- All mainstream Q1/Q2 psychology: wrong tribe (clinical /
  experimental / neuro Q1s). The continental-psychology-adjacent
  subset (Subjectivity, Theory & Psychology, Psychoanalysis Culture
  & Society) is small and was deferred for VAP1 reasons: those
  venues lean Lacanian, and Mavrinsky uses Lacan as foil —
  Lacan-as-shoulder fit would be a hard mis-read.

**Next concrete step (operational):**

1. Run a live verification pass over Cluster A first (15 venues) —
   adapter calls in order: Crossref (ISSN + publisher), DOAJ (OA +
   trust), OpenAlex Sources (concepts + topic distribution),
   SnapshotCrawler on the journal's official author-guidelines page
   for each.
2. Drop or downgrade entries where live data disagrees with the
   inference here.
3. Promote survivors to `VenueRecord` + initial `VenueClaim` set
   (when VF-C2 lands) with the existing `VenueEvidencePack` flow.
4. Repeat for Cluster B, then D (lowest VAP risk first), then C.
   Skip Clusters E and F until the sibling-manuscript line is opened.

**This file becomes obsolete once verified.** It is a memory dump,
not a registry entry. Delete or move to `archive/` after the live
discovery pass closes.
