# MAI W12 Kairon: publisher-page policy quotations + same-journal publisher text (22 Oct 2026)

## Owner-authorized actual execution — preserve distinctions

Input authority: real native Google Sheet W12, 53 route metadata, 6 families and 27 meaning versions; derived JSONL SHA256 `9210da3b761903795907e757950d24c65b99a312554578d0e49860ecde1b9a0c`. Full original 21-tab XLSX raw equivalence remains unknown. Owner AORUS only; private files not committed in Git.

Following previously executed 53-route Crossref/OpenAlex scientific baseline (24 distinct DOI, 48 API retrievals, 178 route abstract bindings, 53 provisional claim critiques: 52 source-attested objections, one abstention MAI-W12-013), Kairon actually collected 53 W12-listed official/organizer URLs, of which **37** yielded extractable original HTML text and **16** were HTTP rejected. Raw bytes + HTML extraction SHA, retrieval UTC, redirected URL and read depth saved in `venue_web_evidence_53`. None of the rejected sources are silently replaced by a guessed call.

### New published-page requirement operation

`scripts/run_mai_kairon_policy_claims.py` drives an explicitly bounded source-quote-extraction model stage against each source. The model returns typed policy candidates, such as abstract/manuscript deadline, word limit, actual abstract channel (form/email), eligibility restrictions, intellectual scope or page-type. **Every admitted exact_quote must be a contiguous literal substring of the captured original publisher/organizer page with a deterministic passage SHA and position.** Repeated provider restarts cannot rewrite existing accepted route/model receipts. Both actual source web bytes and provider response are pinned; bad model quotes are rejected rather than interpreted as policies.

ACTUAL RESULT: **53/53 terminal route records**: 37 quote-bearing model dossiers with **229 anchored requirement claims**; 16 explicit HTML-read blockers. These are `PUBLISHER_PAGE_POLICY_CANDIDATES / CURRENTNESS_HOLD` and not approved official current rules. No AI policy was inferred where absent. No author-ready or outbound send. Source route pages and citation bodies are owner private on AORUS.

Codex model attempts in the prior research stage hit quota; the Kairon extraction used Claude CLI (schema constrained, no outside tools). Initial multi-route batch had 21 valid model dossiers, four failed chunks (model nonliteral passages, >8 source quotes, one provider exit). The separate repair utility `scripts/rescue_mai_kairon_model_chunks.py` recovered **9 independently valid route reports** from original failed raw model outputs with **zero fresh provider calls**, leaving invalid rows for retry. The next batch recovered all except #48, and a bounded independent final retry recovered #48. Every failed original remains on disk. Final source-linked 53/53 acceptance is **not 53 journal policies certified**.

Verified route examples:

* MAI-W12-001 / A-NORM / *Educational Philosophy and Theory*: special issue "Intelligence Beyond the Artificial", abstract by 1 Dec 2026, manuscript by 1 May 2027, direct special-issue editorial contact. The cited CFP text was retrieved from Taylor & Francis; no accepted original ArticleSeed.
* MAI-W12-002 / E-JUSTICE / *Teaching in Higher Education*: abstracts ≤750 words via exclusive FORM by **2 Nov 2026 at 18:00 GMT**, not a generic editor email. Must address socio-political or critical assessment in higher education; unrelated curriculum/method instruction excluded. Full manuscript if invited 24 May 2027. Time sensitive; no send action taken. Publisher URL: https://think.taylorandfrancis.com/special_issues/the-politics-of-assessment/
* MAI-W12-003 / B-VALIDITY / *Journal of Research on Technology in Education*: abstract ≤1000 words excluding references, author title page, form-based channel, due **15 Nov 2026**; full paper invitation contingent on abstract review; final full paper by 1 Apr 2027.
* MAI-W12-006 / F-PROCESS / *Open Philosophy*: call hosted on issue organizer's non-publisher site, email for 500–700-word abstract, 30 Nov 2026 deadline. **Publisher authority not confirmed**.

### First genuinely same-journal publisher-original article capture

One priority route, `MAI-W12-009` / A-EDUCATION → *Studies in Philosophy and Education*, was tested using exact publisher-hosted original scholarly article URLs, not previously repeated cross-venue opponent DOI:
- DOI 10.1007/s11217-026-10100-4, Smith, *Generative Artificial Intelligence, Formative Epistemic Injustice, and Educators’ Solutions*
- DOI 10.1007/s11217-026-10051-w, Tishenina, *Generative AI and the Irreducible Role of Teachers as Callers into Subjectness*
- DOI 10.1007/s11217-026-10097-w, Jin/Wang, *Socratic or Sophistic AI?*

`scripts/run_mai_venue_native_sources.py` reused the existing Crossref API and Kairon publisher HTML acquisition. On live AORUS: **3 Crossref DOI identity matches, 3 exact target-journal metadata matches and 3 actual readable Springer publisher-HTML text captures with pinned raw SHA**. Real metadata/source availability acquired; manuscript genre, complete scholarly read, research claims and independent scientific opposition were NOT certified. There is no author-approved ArticleSeed. Source list was a *bounded explicit researcher selection* for the pilot, not an autonomous Indago venue hunt.

### Actual cold replay and operator UI

Existing `scripts/run_mai_science_pipeline.py` now accepts `--venue-policy-root` and `--venue-native-root`, invokes every bounded stage, independently verifies the real source/claim/model/HTML and refreshes the existing Kairoskopion 53-card board. Actual full one-command cold replay gave:
- 53/53 W12 scientific research dossiers, 52 anchored research objections + one abstention
- 48/48 Crossref/OpenAlex provider responses cached
- 53 Kairon original URL source receipts cached (37 readable, 16 HTTP_REJECTED)
- 37 model policy route analyses / 229 exact citations, **0 new model calls**
- three original same-journal publisher-HTML works for A-EDUCATION
- 53-card `index.html` rebuilt; `venue_policies_certified_count=0`, `venue_native_scholarly_full_texts_certified=0`, `ready_for_author_rework=0`, `ready_for_human_send=0`, 0 new mail/submission actions.

Owner-private operator:
`C:\projects\trimurti\_ops\MAI_W12_PROVIDER_SNAPSHOT_20261020\packets-v1\index.html`
Private pipeline receipt:
`C:\projects\trimurti\_ops\MAI_W12_PROVIDER_SNAPSHOT_20261020\MAI_FULL_ONE_COMMAND_WITH_POLICY_NATIVE_20261022.json`

Command contract (PowerShell, adapt actual source path):
`python scripts/run_mai_science_pipeline.py --packets <W12>/packets-v1 --prior-index <W12>/indago_science_index_53 --published <W12>/prior_art_live_first10 --model-output <W12>/scientific_model_first10 --merged-output <W12>/scientific_model_merged53 --reuse-published --existing-model-root <W12>/scientific_model_first10 --existing-model-root <W12>/scientific_model_claude_26to38 --existing-model-root <W12>/scientific_model_claude_27to35 --existing-model-root <W12>/scientific_model_claude_36to44 --existing-model-root <W12>/scientific_model_claude_45to53 --venue-web <W12>/venue_web_evidence_53 --reuse-venues --venue-policy-root <W12>/venue_policy_candidates_53 --venue-native-root <W12>/venue_native_springer_009 --board-repo <MAI_batch_integrated> --board-output <W12>/packets-v1 --w12-rows <W12>/W12_routes_derived_from_live_sheet.jsonl --w12-native-snapshot <W12>/W12_sheet_A1_M54_verified_read_snapshot.json --outreach-events <W12>/MAI_private_editorial_events_20261020.json --existing-diagnostics <W12>/local-pipeline`.

CODE TESTS: source/CLI/Factory integration **74 local targeted PASS**; board/venue source integration **136 local targeted PASS**. All new code in PR #58 and PR #50 branches is still DRAFT/UNMERGED, no full CI green / staging / production assertion.

## NEXT OPERATION

1. Actually read and compare the three published original works for MAI A-EDUCATION against MAI original source, producing distinct source-anchored Artikl/WhiteCrow objections and a scientific return, not only HTML retrieval.
2. Kairon source-currentness/authority validation for first ten LIVE priority journals, true official author instructions, form URL and rules; treat 16 HTTP_BLOCKED as unsatisfied, use other authorized official sources.
3. Batch 10 → 30–50 across deep reading / scientific challenge / revised opportunity / route qualification and updated board. Author rewriting postponed as owner ordered; human-only SEND retained.
