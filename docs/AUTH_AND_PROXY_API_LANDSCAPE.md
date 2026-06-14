# Auth, proxies and API landscape for Kairoskopion venue/source layer

**Date:** 2026-06-14
**Scope:** map of what we currently use, what we *could* use with which
auth, and where it would be cheaper to go through an aggregator
(including AI aggregators) instead of the original source.

Не "сделай так" — это карта. Решения по auth (особенно платные / DPA)
принимает оператор.

---

## 0. What we already use (free, no auth)

| source | what we use it for | what we attach | rate-limit reality |
|---|---|---|---|
| **DOAJ** | venue discovery + identity (OA journals) | User-Agent only | none observed |
| **OpenAlex Sources** | venue identity, ISSN→source lookup, homepage_url | User-Agent only | 100 000 req/day shared; ~10 req/s polite |
| **OpenAlex Works** | corpus mining (titles + concepts + reconstructed abstracts + references) | User-Agent only | same |
| **OpenAlex Authors** | editor identity resolution | User-Agent only | same |
| **CyberLeninka** | Russian-language venue discovery + article-level corpus hits | none | none observed, polite ~1 req/s |
| **Crossref** (skeleton ready, not wired in v1 yet) | DOI metadata, references | mailto in UA | 50 req/s polite pool |
| **OpenCitations COCI** (skeleton ready) | cited-by / references graph | none | polite |
| **Unpaywall** (skeleton ready) | OA status by DOI | email URL param | 100 000/day with email |
| **Sherpa Romeo** (skeleton ready) | self-archiving policy | API key (free) | 1000/day |

This stack covers the **C indexers/registries + D corpus + G graph
adapters** rows of the rubric v2 source map for venues with OpenAlex
coverage.

---

## 1. Five things to do **right now** (cheap, free, high leverage)

### 1.1 OpenAlex polite pool (zero auth, just an email)
- Add `&mailto=kairoskopion@proton.me` to every OpenAlex request.
- Effect: requests go through a separate, less-congested queue;
  rate limits relax in practice; you become a known polite client.
- Cost: nil.
- Where: `adapters/venue/openalex_works.py`, `adapters/venue/openalex.py`.

### 1.2 Crossref polite pool
- Same trick: `?mailto=...` on every Crossref endpoint.
- Effect: better rate limits, fewer 503s.
- Cost: nil.

### 1.3 Semantic Scholar API key
- Free signup at https://api.semanticscholar.org/. Key issued by email.
- Effect: rate limit jumps from 100 req/min → 1000 req/min (10× headroom).
- What we'd use it for: citation graph cross-check for OpenCitations,
  paper recommendations from a seed corpus, abstract coverage where
  OpenAlex inverted index is empty.
- Cost: nil (research tier).

### 1.4 ORCID Public API client
- Free registration at https://orcid.org/developer-tools.
- Get a Client ID + Secret (OAuth 2-legged client credentials).
- Effect: clean per-editor lookup for affiliations, employment history,
  works list. Better than scraping board pages.
- What we'd use it for: editorial board enrichment without HTML regex.
- Cost: nil.

### 1.5 ROR API (no auth)
- https://ror.org/registry — institutional identifier resolution.
- Effect: canonicalize "University of Cambridge" / "Cambridge Univ." /
  "Univ Cambridge" into one ROR id; OpenAlex Authors carry ROR ids.
- What we'd use it for: editorial board geo distribution by
  institutional cluster, not by free-text affiliation.
- Cost: nil.

**Combined effect of 1.1–1.5:** roughly doubles the per-venue
profile completeness without spending a single dollar or touching
any paid API.

---

## 2. Free aggregators we're **not yet using** but should consider

| source | what it gives us | auth | uses for venue layer |
|---|---|---|---|
| **OpenAIRE Graph API** | works + funders + repositories aggregated | none for read | extra abstract / OA coverage when OpenAlex misses |
| **CORE API** | full-text of 200M+ OA papers | free API key | feeds D corpus directly — closes the "no abstract" gap |
| **BASE API** | institutional repository works | none | discovers OA copies for paywalled venues |
| **ScienceOpen API** | citation context, post-publication peer review | free signup | citation network for venues outside OpenCitations |
| **CrossRef Event Data** | citations / mentions / tweets | none | corpus signal not in OpenAlex |
| **arXiv API** | preprints | none | for STS / philtech preprints |
| **PhilPapers (no public API)** | philosophy-specific catalogue | scraping or pgsql dump request | continental-philosophy canon coverage we currently lack |

**Recommendation:** wire **CORE** first (closes the abstract-coverage
gap that bit us in pass #002), then **OpenAIRE** for European OA
journals, then **ScienceOpen** as an OpenCitations alternative for
venues that OpenCitations doesn't cover.

---

## 3. Paid primary sources — what authentication actually buys

### 3.1 Scopus (Elsevier)
- **Cost reality:** institutional only; ~$7-15k/year typically; no
  meaningful individual plan.
- **What you get:** Scopus journal categories + quartile snapshots +
  CiteScore + author profiles + cited references for paywalled journals.
- **Authentication:** Elsevier Developers Portal → request API key →
  approval can take days; institutional IP gateway optional.
- **What we'd use it for:** `institutional_signals` (rubric §2 row 9)
  — `prestige_tier` and `indexing` populated authoritatively.
- **Honest cost/benefit:** for Mavrinsky's case we don't need it.
  For "is this venue Q1?" → DOAJ + OpenAlex `concepts.level` rankings
  + Sherpa give us 80% of what Scopus would give us, for free.

### 3.2 Web of Science (Clarivate)
- **Cost reality:** institutional only; similar tier to Scopus.
- **What you get:** WoS categories + JCR Impact Factor + ESCI/SSCI/SCI
  inclusion; gold-standard for "is this venue cited where it claims".
- **Authentication:** Clarivate Developer Portal → "Web of Science
  Starter API" trial available with email signup; full API requires
  institutional contract.
- **Honest cost/benefit:** same as Scopus. The free trial is real but
  rate-limited to 5 req/s and 5 fields per call.

### 3.3 Dimensions (Digital Science)
- **Cost reality:** **free tier for academics exists** (Dimensions
  Free). Personal account, gated.
- **What you get:** citation graph + funding data + clinical trials +
  policy citations. Coverage similar to OpenAlex but with finer-grain
  funder tagging.
- **Authentication:** Digital Science account → personal API key.
- **Honest cost/benefit:** mostly redundant with OpenAlex for journals.
  Useful for **funding** data which OpenAlex underreports — relevant
  if we ever assess "venues that funded researchers publish in".

### 3.4 JSTOR / Project MUSE / ProQuest
- **Cost reality:** institutional, no public API at all.
- **Honest cost/benefit:** not relevant for venue *metadata*. Only
  for getting at full text of humanities papers, which we don't need
  in venue layer.

### 3.5 eLibrary.ru / РИНЦ
- **Cost reality:** Russian academic indexer; **free signup for
  individuals**, but API access is gated by separate institutional
  agreement; in practice no public API.
- **What you get:** РИНЦ inclusion + impact factor + ВАК-listed status
  + author profiles for Russian venues.
- **Authentication:** individual account is free; data API requires
  institutional contract.
- **Honest cost/benefit:** **the only authoritative source for ВАК
  status**. Everything else (CyberLeninka, OpenAlex Russian coverage)
  is partial. If we want to actually serve Russian-language scenarios,
  this is the single biggest hole.
- **Suggested compromise:** scrape the public HTML pages politely;
  many fields (РИНЦ status, ВАК perechen' inclusion) appear in the
  free public view. This **is not the official API path** and may
  violate ToS — operator decision.

### 3.6 ВАК (Перечень рецензируемых научных изданий)
- **Reality:** there is **no API**. The list is published as PDF /
  HTML on `vak.minobrnauki.gov.ru`. Updates are gazette-style.
- **What we can do:** download the latest PDF, parse it, hash it,
  date-stamp it. Treat as a static reference asset, not a service.
- **Authentication:** none — it's a public-record document.

---

## 4. AI aggregators as proxies

This is the new layer the user asked about. AI aggregators sit on top
of one or more primary sources and resell access through a unified
API. Some of them have institutional contracts with paid sources, so
calling them is cheaper than buying Scopus.

### 4.1 Semantic Scholar (Allen Institute)
- **Cost:** free, no auth for low rate; free API key for high rate.
- **What you proxy through it:** abstracts + citations + author
  records + paper TLDRs (machine-generated short summaries).
- **Does it proxy paywalled content?** No — it indexes only what's
  publicly available, but **it covers more than OpenAlex** in CS, ML,
  med (OpenAlex is broader on humanities).
- **Recommendation:** wire it. Zero risk.

### 4.2 Consensus
- **Cost:** $9-$15/mo individual; team plan for $$.
- **What you proxy through it:** LLM-summarized claims across papers,
  including those behind paywall (they have institutional licenses).
- **Auth:** account + API key (API in private beta as of 2026).
- **Does it proxy paywalled content?** YES, that's its value — but
  via summary, not full text.
- **Honest cost/benefit:** useful for "what does the literature say
  about X" at fit-time; **not** useful for venue-side profile building.

### 4.3 Elicit
- **Cost:** $10-$60/mo; API available on paid tiers.
- **What you proxy through it:** semantic search across 200M papers,
  RCT-quality summaries, automated literature reviews.
- **Does it proxy paywalled content?** Partial — Elicit pulls from
  Semantic Scholar primarily.
- **Honest cost/benefit:** same as Consensus — fit/review use, not
  venue-side.

### 4.4 SciSpace (Typeset)
- **Cost:** free tier + $12-$20/mo paid.
- **What you proxy through it:** paper Q&A, table extraction, citation
  graph, author profiles.
- **Has API?** Yes — `https://api.scispace.com`, paid only.
- **Does it proxy paywalled content?** Partial.
- **Honest cost/benefit:** their "Journal Finder" claims to fit
  manuscripts to journals — directly competes with what Kairoskopion
  does. **Not a proxy we want to depend on** — we'd be benchmarking
  ourselves against a black box.

### 4.5 Scite.ai
- **Cost:** $20/mo individual.
- **What you proxy through it:** Smart Citations (whether a paper is
  supported / contradicted / mentioned). Useful for `citation_expectation`
  on a venue's corpus.
- **API:** yes, REST.
- **Does it proxy paywalled content?** Yes — paywalled-paper citation
  context is included in the institutional license.
- **Honest cost/benefit:** unique signal (no free alternative for
  "this paper is contradicted by these later papers"). **Strong
  candidate for one paid integration** if we ever need it.

### 4.6 ResearchRabbit / Connected Papers / Iris.ai
- **No public API.** UI/widget only. Cannot be a programmatic proxy.

### 4.7 Lens.org
- **Cost:** free tier (limited), paid for high volume.
- **What:** scholarly + patent metadata.
- **API:** yes, free for academic use with registration.
- **Honest cost/benefit:** unique on **patent-cites-paper** signal.
  Not relevant for Mavrinsky-grade venues; matters for engineering
  fields the user mentioned in their broader wish (
  "от философии до психологии или инженерных дисциплин").

### 4.8 Litmaps
- **API:** beta-only.
- Same family as Connected Papers; skip.

### 4.9 Dimensions API (already covered above in §3.3 — but worth
re-mentioning: Dimensions sits structurally as both a primary source
**and** an aggregator over OpenAlex-like graphs).

---

## 5. The trade-off table — "direct vs. via aggregator"

| signal we need | best free path | when paying buys you something | what AI aggregator adds |
|---|---|---|---|
| journal identity (ISSN, publisher) | DOAJ + OpenAlex + Crossref | nothing meaningful | nothing |
| OA / APC | DOAJ + Sherpa + Unpaywall | nothing | nothing |
| indexing (Scopus / WoS / РИНЦ) | OpenAlex `concepts.level` proxies + DOAJ | **yes** — only Scopus / WoS / eLibrary give authoritative inclusion | Lens.org as a partial proxy (mirrors Scopus for some venues) |
| journal Quartile / IF | inference from OpenAlex `cited_by_count` + percentile | **yes** for JCR-grade IF | Scite.ai's Citation Statement Quality (different signal but related) |
| editorial board affiliations | E adapter + OpenAlex Authors + ORCID + ROR | nothing meaningful | nothing |
| corpus abstracts | OpenAlex (60-70% coverage) + CORE (≈85% with overlap) | full subscription gives last 30% | Semantic Scholar fills part of CS-leaning gap |
| corpus references | OpenAlex `referenced_works` + OpenCitations COCI + ScienceOpen | Scopus / WoS for cited-references on paywalled venues | Scite.ai for citation-context |
| recommendation ("which venue?") | **do not outsource this** | n/a | SciSpace Journal Finder — competitor, do not use as proxy |
| ВАК / РИНЦ status | CyberLeninka partial proxy | **yes** — eLibrary is the only authority | none |
| editor publication preferences | ORCID + OpenAlex Authors works list | nothing | Semantic Scholar TLDRs help summarize a board member's recent papers |

---

## 6. Concrete asks of the operator (auth-shaped TODO)

These are credential-shaped tasks the system **cannot** do itself.
None of them require code work right now; they're "go sign up here,
paste the key into `.env`" tasks.

| # | task | who/where | cost | effort | gives us |
|---|---|---|---|---|---|
| 1 | Set `KAIROSKOPION_OPENALEX_MAILTO` in `.env` (already in `.env.example`) | nothing — pick any email | $0 | 1 min | 10× headroom on rate limits |
| 2 | Register at https://api.semanticscholar.org/, paste key as `KAIROSKOPION_SEMANTIC_SCHOLAR_API_KEY` | Semantic Scholar | $0 | 10 min | full citation graph + author records, no rate-limit grief |
| 3 | Register at https://orcid.org/developer-tools, paste `KAIROSKOPION_ORCID_CLIENT_ID`/`_SECRET` | ORCID | $0 | 15 min | clean editor lookup, replaces HTML regex for ~30% of editors |
| 4 | Register Sherpa Romeo at https://v2.sherpa.ac.uk/cgi/programmes/, paste `KAIROSKOPION_SHERPA_API_KEY` | Sherpa | $0 | 5 min | self-archiving policy for venues |
| 5 | Register CORE at https://core.ac.uk/services/api, paste `KAIROSKOPION_CORE_API_KEY` | CORE | $0 | 10 min | full-text + abstracts for ≈85% coverage |
| 6 | Sign up at Dimensions Free for academics, paste `KAIROSKOPION_DIMENSIONS_API_KEY` | Digital Science | $0 (academic) | 20 min | funder data + clinical trials |
| 7 | Lens.org academic registration, paste `KAIROSKOPION_LENS_API_KEY` | Lens.org | $0 (academic) | 15 min | patent-cites-paper signal |
| 8 | Scopus Elsevier Developers — request API key | Elsevier | institutional or $$ | days | authoritative Scopus categories + quartile |
| 9 | WoS Starter API trial | Clarivate | trial only | days | authoritative WoS categories |
| 10 | Scite.ai paid tier + key | Scite.ai | $20/mo | 5 min | citation-context signal nobody else gives |
| 11 | eLibrary individual account | eLibrary.ru | $0 individual | 30 min (RU language) | enables possible HTML scrape for РИНЦ/ВАК; no official API for free |
| 12 | Consensus / Elicit team tier | varies | $10-60/mo | 15 min | LLM-summarised paywalled paper claims **for fit-time, not venue-side** |

The "stop sign" items (8, 9, 10, 12) are the ones I'd defer until the
free stack saturates. The rate-limited free items (1-5) close ~80% of
the actual gaps we hit in pass #002.

---

## 7. My straight recommendation

**Stop here on auth for the venue layer.** Wire items 1-5 from §6.
They cost $0 and ~30 minutes total. They give us:

- 10× rate-limit headroom on OpenAlex / Crossref;
- a second corpus source (Semantic Scholar) that fills the CS/ML gaps
  OpenAlex misses;
- clean editor identity (ORCID + ROR + OpenAlex Author) without regex
  scraping;
- the missing 30% of OA abstracts via CORE.

**Defer everything else** until we have a real "this venue would
benefit from Scopus authority" failure mode. We don't have one yet —
pass #002 surfaced "we lack OpenAlex IDs for DOAJ-only venues", which
is now closed by ISSN → OpenAlex resolver in this pass.

**For Russian-regime, separately:** until eLibrary opens a real API,
the honest path is:

- accept CyberLeninka as the authoritative "open Russian-corpus"
  proxy (it's what we have);
- treat ВАК perechen' as a downloadable PDF asset, version-stamped,
  parsed once and stored;
- mark anything beyond as `AUTH_REQUIRED`, never `UNKNOWN_ABSENT`.

**For AI aggregators specifically:** there is **no current case** for
proxying venue-side queries through Consensus / Elicit / SciSpace.
Their value is at fit-time (claim-level LLM summarisation), not at
venue-profile time. SciSpace specifically is a competitor product;
proxying through it would mean we trust their black-box journal
recommender, which defeats the whole rubric.

**For the Mavrinsky case specifically:** the §6 free stack is enough
to close all four C-blockers from pass #002 honestly. Paying for
Scopus / WoS / Scite would buy precision we don't currently lack —
we lack *coverage*, not precision, and coverage is what CORE +
Semantic Scholar + OpenAIRE solve for free.

---

## 8. What I'm not doing in this pass

- I will not register on the operator's behalf. Items 1-7 of §6 need
  the operator to do the signup.
- I will not add code that requires keys not yet in `.env`. The
  enricher already works with empty mailto / missing keys.
- I will not propose adding Scopus, WoS, Scite as runtime dependencies.
  Their cost/benefit doesn't justify it at this stage.
- I will not use AI aggregators as a stealth replacement for the
  rubric's primary computation layer per the rubric v2 §3 forbidden
  source uses.

End of landscape.
