# Venue Discovery Tradecraft — accumulated lifehacks

**Status:** canonical operator playbook. Living doc — append new
discoveries as they're found.

**Purpose:** every workaround, URL-pattern, bypass, and recovery
strategy that took non-trivial trial-and-error to discover during a
real venue-discovery session lives here. Future engines (LLM or human)
hit the same walls; this doc means they hit them once collectively,
not once per agent run.

**Companion to:**
- [VENUE_FUNNEL_AND_PROFILE_PACKAGE_V1.md](VENUE_FUNNEL_AND_PROFILE_PACKAGE_V1.md) — canon
- [SOURCE_ADAPTER_AUTHORITY_CONTRACT.md](SOURCE_ADAPTER_AUTHORITY_CONTRACT.md) — authority levels
- `benchmarks/golden/venue_source_layer_map.md` — operational rubric

---

## 1. Tool capability map (what CAN access what)

| Tool | What it gets | Auth-aware? | When to use |
|---|---|---|---|
| `WebSearch` | top-N search results with snippets | ❌ no user session | broad discovery, finding URLs |
| `WebFetch` | URL → markdown via small model | ❌ no cookies, no JS execution | static HTML pages, journal homepages |
| `Claude in Chrome` MCP | full browser with user's session | ✅ uses user's logged-in tabs | Google Scholar, Scopus, paywalled archives, JS-rendered pages |
| `Bash` for `git/curl` | direct HTTP without session | ❌ | follow-redirect, retry-on-network-fail |

**The rule:** if a site requires login OR JS-renders content OR has
anti-bot detection → use Chrome MCP (user's session). Everything else
→ WebFetch is faster and cheaper.

**Anti-pattern:** retrying WebFetch against a login-walled URL hoping
it works on retry. It won't. Switch to Chrome MCP or skip the source.

### Chrome MCP usage sequence (must follow in order)

1. `mcp__Claude_in_Chrome__list_connected_browsers` — verify connection
2. If >1 browser: `select_browser` with chosen deviceId (the system
   will prompt for selection only when ambiguous AND user has
   approved auto-selection)
3. `tabs_context_mcp{createIfEmpty:true}` — required before any action
4. `browser_batch{actions:[navigate, get_page_text, ...]}` — sequential
   actions in one round-trip (much faster than individual calls)

**Hard rule:** `browser_batch` actions are SEQUENTIAL, not parallel.
Each navigate REPLACES the page in the same tab. To preserve previous
content, batch is `navigate→get_page_text→navigate→get_page_text`.

### Service-outage recovery

When `claude-opus-4-7 is temporarily unavailable` errors appear:
- ALL classifier-checked tools fail simultaneously: WebFetch, WebSearch,
  Edit, Write, browser_batch
- Read, Grep, Glob still work (no classifier needed)
- Outage typically resolves in 1-3 minutes; retry once after brief pause
- DO continue with local file analysis using Read/Grep during outage

---

## 2. URL-pattern fallback library

Empirically verified URL patterns. When a journal site blocks one path,
try the next.

### Russian academic OJS instances

Most RU journals run **Open Journal Systems**. Common URL skeleton:

```
{base}/                                  → main page
{base}/issue/current                     → current issue (often works when archive doesn't)
{base}/issue/archive                     → full archive listing
{base}/issue/view/{n}                    → specific issue (may require auth)
{base}/about                             → journal info
{base}/about/editorialTeam               → EB (sometimes only ed-in-chief)
{base}/about/displayMembership/{n}       → full board (rarely)
{base}/about/editorialPolicies           → policies
{base}/jour/...                          → some installs nest under /jour/
{base}/pages/view/{slug}                 → custom pages (RANEPA pattern)
```

**Locale tricks:**
- `?locale=en_US` appended sometimes bypasses RU-only access locks
  (verified: Социология власти `socofpower.ranepa.ru/jour/pages/view/EditorialC?locale=en_US`)
- `?lang=ru` / `?lang=en` switches some Tomsk/SPb sites
- `?showToc` parameter sometimes shows full issue ToC when not visible
  by default

### Static-HTML journal sites (non-OJS)

Common patterns for hand-maintained sites:

```
{base}/redaktsionnaya-kollegiya.html  ← старая конвенция
{base}/redkollegiya.html
{base}/redkollegiya                   ← без .html, Chelovek pattern
{base}/editorial-board.html
{base}/editorial-board
{base}/redaktor-staff.html
{base}/about/board
{base}/board
{base}/council
```

**Empirical findings:**
- НЛО (nlobooks.ru): `/magazines/novoe_literaturnoe_obozrenie/{N}_nlo_{n}_{year}/` per issue
- Логос (logosjournal.ru): `/board/`, `/council/`, `/archive/`
- Stasis (stasisjournal.net): `/index.php/journal/issue/current` works publicly;
  individual issues at `/issue/view/{id}` may paywall
- Praxema (praxema.tspu.ru): **domain migrated Dec 2024** from `praxema.tspu.edu.ru`
  → `praxema.tspu.ru`; both work as of mid-2026, but old cached search
  results often return 404 on new domain due to .html-vs-.php path
  shuffling. Use `/index.php` paths if `.html` fails.
- Худ.журнал (moscowartmagazine.com): `/archive/releases/{year}` works;
  individual issues paywalled
- ИФЕ (ife.iphras.ru): direct ECONNREFUSED frequently; fallback is
  `iphras.ru/histph.htm` (parent institute page)
- Chelovek (chelovek.iphras.ru): `/redkollegiya` (no `.html`), NOT
  `/jour/about/editorialTeam` (404)
- Полития (politeia.ru): frame errors on most paths. Skip primary site;
  search RINTs or CyberLeninka instead.

### Verified-broken patterns (don't retry)

- `praxema.tspu.ru/redaktsionnaya-kollegiya.html` → 404
- `praxema.tspu.ru/redkollegiya.html` → 404
- `praxema.tspu.ru/praxema-redactor-staff.html` → 404
- `usp.hse.ru/about/editorialTeam` direct → was 403 from WebFetch, but
  WORKED from authenticated Chrome MCP
- `socofpower.ranepa.ru/jour/pages/view/EditorialC` (no locale) → often
  ECONNREFUSED; with `?locale=en_US` works
- `scholar.google.com/citations?user={random}` → 404 if user_id wrong
- `scholar.google.com/citations?hl=en&user={id}` direct without prior
  search → may redirect to login
- HSE staff publications direct URL (publications.hse.ru/articles/?author={id})
  → returns JS shell only; useless without browser execution

---

## 3. Cross-listing inference — the "Avanesov technique"

**Pattern:** Editor X is chief of Journal A. Journal A's EB page is
inaccessible (404/403/cert error). But Editor X is also a board member
on Journal B. Journal B's EB page works AND lists Editor X with their
Journal A role attached.

**Verified example:**
- **Avanesov S.S.** is Praxema editor-in-chief
- Praxema's `/redaktsionnaya-kollegiya.html` returns 404
- Chelovek editorial board page lists: "Аванесов С.С., главный редактор
  журнала «ΠΡΑΞΗΜΑ»."
- Confirmation acquired without touching the blocked journal site

**Heuristic for finding cross-listings:**
1. Identify the venue cluster the blocked journal sits in
2. Find 2-3 nearby venues in same cluster with verified EB
3. Grep their EB pages for the blocked editor's name
4. The role is usually annotated in the cross-listing

**Why this works:** RU academic editorial culture cross-pollinates
heavily. A senior editor of journal A almost always sits on the
editorial board of 2-3 sibling journals.

---

## 4. Aggregator allowlist — surfacing blocked content

When primary journal sites block content, these aggregators sometimes
surface ToCs / EBs / publication metadata:

| Aggregator | What it surfaces | When | Reliability |
|---|---|---|---|
| **motto-distribution.com** | journal catalogue listings with full editorial board copy | when journal site has anti-bot | high — surfaced Stasis full board |
| **CyberLeninka** (cyberleninka.ru) | full text of many RU papers republished | when journal paywalled | high |
| **eLibrary.ru / Истина MSU** (istina.msu.ru) | author publication lists for RU researchers | for editor publication traces | high — Markov A.V. 31 titles via Истина |
| **vse-svobodny.com** | RU bookshop with full issue ToCs (often) | for journal issues | medium |
| **podpisnie.ru** | RU subscription service with magazine ToCs | similar | medium |
| **shop.kunstkamera.ru** | Kunstkamera publication shop with issue ToCs | АнтроФорум +60 captured this way | high |
| **NEB (rusneb.ru)** | National Electronic Library catalogue | metadata + sometimes ToC | medium |
| **GES-2 / V-A-C foundation** | joint special issue announcements | for art-theory cross-publishing | high — Logos №1/2024 confirmed here |
| **books.google.com** | book entries with year + publisher + sometimes ToC | for monograph publication confirmation | high |

**Anti-pattern:** Sci-Hub / shadow libraries — out of scope for venue
metadata work; only useful for fulltext mining (cluster H per canon §3).

---

## 5. Google Scholar tradecraft

### Query patterns that work

```
"FirstName LastName" {affiliation} {keyword1} {keyword2}
"Surname FirstInitial" {topic}
"русское имя" {english_keyword}        ← мешанный поиск для bilingual authors
```

**Verified-working examples:**
- `"Alexander Filippov" HSE Schmitt political theology` → 13+ Schmitt
  papers
- `"С.С. Аванесов" Аванесов phenomenology philosophy` → mixed results
  via Cyrillic
- `"Аванесов" визуальная "Praxema"` → 11 Praxema papers verified

### Query patterns that DON'T work

```
"Aleksandr Markov" RGGU                ← too generic, Markov is common name
```

**Rule:** for common surnames (Markov, Sokolov, Smirnov, Petrov, etc.),
use Cyrillic + venue name + topic. English transliteration alone fails.

### Direct Scholar profile URL strategy

- Don't guess user_ids. They're 12-char alphanumeric and arbitrary.
- Instead: search by name → click first author's profile link → get URL
- Scholar profile URL pattern: `scholar.google.com/citations?user={12char}&hl={lang}`
- The Khestanov h-10 / Kurakin h-26 / Pisarev h-7 we captured all came
  from secondary sources clicking through search results, not direct
  user_id guessing.

### What you can extract from Scholar results page

Without logging in / hitting profile page:
- Recent publications (titles, year, venue, citation count)
- Co-authors (often visible in author line)
- Top-cited works in time-range
- Cross-referenced citation patterns ("cited by N")

What requires authenticated Scholar profile access:
- h-index value
- i10-index
- Total citation count
- Full publication list (vs top results)
- Co-authorship network details

---

## 6. Editor identity verification heuristics

When the primary editorial board page is blocked or thin, an editor's
identity can be triangulated from multiple secondary signals:

### "Glossarium signal" — single dominant work
Some editors have ONE highly-cited work that defines their scholarly
identity. Finding it tells you their tribe.

| Editor | Glossarium-signal work | Cit count |
|---|---|---|
| Filippov A.F. | "Glossarium" (Schmitt translation 2013) | 583 |
| Sokolov B.G. | "Генезис истории" 2004 monograph | 58 |
| Avanesov S.S. | "Городское пространство как антропологический феномен" Praxema 2018 | 58 |
| Yampolsky M. | "In the shadow of monuments" 1995 | 126 |
| Kurakin D.Yu. | "Reassembling the ambiguity of the sacred" J. Classical Sociology 2015 | 67 |
| Pisarev A.A. | "On the question of truth" Epistemology Phil Sci 2020 | 17 |
| Timofeeva O. | "Solar Politics" book 2022 | 31 |

The Glossarium-signal isn't always the editor's most-recent or most-
representative work, but the citation pattern tells you the venue mass
of their tribe.

### "Through-author signal" — cross-venue publication trace

An editor of journal A who publishes in journal B as a regular author
is operationally bridging the two venues, even if neither EB page
explicitly says so.

Verified through-author bridges in this corpus:
- **Markov** (Артикульт board) → publishes in Соц.обозр + НЛО + Praxema + Новый мир (31 titles 2022-2026)
- **Khestanov** (Логос+Соц.обозр board) → Urban Studies 2022 smart-city paper (6 cit)
- **Kurennoy** (Логос Scientific Editor) → Соц.власти 2021 lab-vs-field paper (4 cit)
- **Syutkin** (Stasis Centre faculty) → Logos 2024 "Fissure in the Absolute" (4 cit)
- **Pisarev** (Логос board) → Человек 2024 Foucault paper
- **Yatsenko** (НЛО author 2025) → Stasis Vol 13 №2 2025 author

### Authority of "X edits journal Y" claim by source

```
formal_page (journal A's own EB page)           — highest authority
publisher_page (publisher's portfolio listing)  — high
aggregator (motto-distribution etc.)            — medium-high
cross-listing (journal B lists X as A's editor) — medium
training-knowledge inference                    — low (always verify!)
```

---

## 7. Source freshness windows (verified empirically)

```
Editorial board pages                             — 60 days
  (turnover real; verified Vakhshtain→Smolkin transition April 2022)
Author guidelines                                 — 90 days
Submission process descriptions                   — 90 days
Aims/scope text                                   — 180 days
Journal homepage metadata                         — 180 days
Issue archive listings                            — 365 days
Indexer cards (Scopus, ВАК, WoS)                  — 365 days
Founder / institutional history                   — never expires
```

**Editorial transitions to watch for** (verified during this session):
- Vakhshtain → Smolkin (Соц.власти, April 2022, foreign-agent exit)
- Pavlov RAS Cor Member elected 2025 (changes his board weight)
- Domain migration Dec 2024: praxema.tspu.edu.ru → praxema.tspu.ru

---

## 8. Russian transliteration heuristics

Editor names often appear in multiple forms:
- Аванесов → Avanesov / Avansov / Avansov (rarely)
- Хестанов → Khestanov / Hestanov (rare)
- Куренной → Kurennoy / Kurennoi / Kurennoj
- Куракин → Kurakin
- Шиповалова → Shipovalova / Shipovalov

**Search strategy for editors with Cyrillic-primary names:**

1. Try search with quoted Cyrillic name first: `"Шиповалова Л.В."`
2. Then add English: `"Lada Shipovalova"` + affiliation
3. Combine both in one query if first two return thin results

**For uncommon names** (Кодзокова, Тавровский, etc.) Cyrillic-only is
usually enough. **For common names** (Соколов, Петров, Иванов, Марков)
always combine with affiliation + topic to disambiguate.

---

## 9. Failed patterns to NOT retry

If you see these symptoms, change strategy immediately. Don't waste
classifier budget retrying.

| Symptom | What it means | What to do instead |
|---|---|---|
| Frame error on first paint | JS-rendered SPA | Chrome MCP or skip |
| 403 Forbidden | bot detection | Try locale param + aggregator |
| 404 on multiple url patterns | site reorganized recently | check CyberLeninka mirror |
| `ECONNREFUSED` | site down or geo-blocked | retry once after 60s, then skip |
| Cert verification failed | expired/self-signed | Chrome MCP may work; WebFetch won't |
| Redirect to /login | paywalled | Chrome MCP with user session |
| Page returns 200 but content is "Page Not Found" | soft-404 | treat as 404 |
| Empty `Source element: <body>` with login form | session expired | Chrome MCP re-select_browser |

---

## 10. Idempotent seed corpus pattern

When extending the Mavrinsky-RU seed corpus (or building a new one
for a different scenario), follow this pattern:

```python
# scripts/build_*_seed_corpus.py

def _slug(text: str, n: int = 12) -> str:
    """8-12 char sha1 hash of text. Same text → same hash → idempotent."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:n]

def venue_id(canonical_name: str) -> str:
    return f"vrec_mavru_{_slug(canonical_name)}"

def source_id(venue_record_id: str, source_key: str) -> str:
    return f"vsrc_mavru_{_slug(venue_record_id + ':' + source_key)}"

def claim_id(venue_source_id: str, claim_path: str, sequence: int = 0) -> str:
    return f"vclm_mavru_{_slug(venue_source_id + ':' + claim_path + ':' + str(sequence))}"
```

**Why deterministic IDs matter:**
- Re-running the converter doesn't create duplicate records
- Two different operators can build the same corpus and get identical IDs
- Registry import is naturally idempotent (overwrite by ID)
- Cross-session continuity: closing and reopening a session still
  produces same canonical_name → same venue_record_id

**Verified working in this session:** 17 venue rebuilds, 0 duplicates.

---

## 11. Anti-pattern callbacks (from rubric)

When adding any venue or claim to the corpus, run a quick mental check
against the rubric anti-patterns:

| Pattern | Trigger | Resolution |
|---|---|---|
| AP1 — aims_scope upgraded to FACT | "publishes continental philosophy" → `official_fact` | Mark `official_claim`, require corpus verification |
| AP2 — indexing → fit | "Phil&Tech Q1" → "strong fit" | These are orthogonal; never conflate |
| AP3 — editorial board as psychology | "Board has Foucault scholars → loves dispositif papers" | Mark as `inference`, low confidence |
| AP4 — full-text source = metadata source | full-text URL used to claim ISSN/publisher | Always separate full-text from metadata authority |
| VAP1 — Lacan-as-shoulder | Mavrinsky-specific: Lacan as foundational | flag as foil, not shoulder |
| VAP2 — Simondon-hallucination | making up Simondon citations | check actual references |
| VAP3 — HCI fit upgraded | non-HCI article called "HCI fit" | sibling manuscript only |
| VAP4 — generic STS reframe without core | "just reframe as STS case" | adds core risk; mark explicitly |
| VAP5 — Phil&Tech Q1 = strong | analytic-leaning venue tagged Mavrinsky-strong | check tribe before quartile |
| VAP6 — RU pool under international scenario | RU venue in international submission strategy | scenario-mismatch flag |

---

## 12. Operational quick reference

### Sequence for discovering a new venue

```
1. WebSearch for "{venue_name} {year} содержание" (Cyrillic) — get
   primary URL + recent issue clue
2. WebFetch {primary_url} — identity, ISSN, mission, ed-in-chief
3. WebFetch {primary_url}/about/editorialTeam — full board
4. If blocked: try /redkollegiya, /board, /redaktor-staff
5. If still blocked: try aggregator pattern (motto, vse-svobodny,
   CyberLeninka)
6. If editor identity is critical: cross-listing inference
   (search other venues' EB pages for the editor's name)
7. For editor publications: Chrome MCP + Google Scholar with
   Cyrillic+English name combination
8. Always: record source URL + retrieved_at + freshness_window for
   each claim
```

### Sequence for filling editor publication data

```
1. Chrome MCP (user session) + Scholar query "FirstName LastName
   {affiliation} {topic}"
2. Take top 5-10 results; record title + year + venue + citation count
3. If profile page accessible: get h-index, total citations
4. If common surname: add Cyrillic + topic to disambiguate
5. Watch for editorial roles mentioned in profile blurbs
   (e.g., "deputy editor of journal Stasis")
6. Encode as claim with `claim_path: "editorial_board_publications.{LastName}"`
   and `evidence_status: "external_claim"` confidence: high
```

### Sequence for finding cross-venue bridges

```
1. List known editors with their primary venue(s)
2. For each editor, Scholar-search recent publications
3. Note which other Mavrinsky-target venues appear as publication venues
4. The intersection = cross-venue through-author bridge
5. Record as claim with claim_path:
   "through_author_signal.{EditorName}" and quote both venues
```

---

## 13. Adding new tradecraft

When you discover a new workaround during a future session:

1. **Test it once** to confirm it works
2. **Test the failure mode** to confirm what you were working around
3. **Add an entry** to this doc with: pattern + example + reliability
4. **Update the seed corpus converter** if the pattern affects multiple
   venues
5. **Update memory** if the pattern is session-spanning operational
   knowledge

**Format for new entries** (append to the relevant numbered section):

```markdown
### {Pattern name}
**Symptom:** what you see
**Cause:** why it happens
**Fix:** specific workaround with verified URL/method
**Verified on:** date + specific example
**Reliability:** high/medium/low
```

---

## 14. Cross-references

- Canonical funnel: [VENUE_FUNNEL_AND_PROFILE_PACKAGE_V1.md](VENUE_FUNNEL_AND_PROFILE_PACKAGE_V1.md)
- Source authority levels: [SOURCE_ADAPTER_AUTHORITY_CONTRACT.md](SOURCE_ADAPTER_AUTHORITY_CONTRACT.md)
- Operational rubric: `benchmarks/golden/venue_source_layer_map.md`
- Mavrinsky venue gold: `benchmarks/golden/mavrinsky_venue_side_gold.md`
- Mavrinsky-RU operator notes:
  `benchmarks/_operator_notes/mavrinsky_venue_research/`
- Seed corpus converter: `scripts/build_mavrinsky_ru_seed_corpus.py`
- Backlog code-alignment items VF-C1…C9: [BACKLOG.md](BACKLOG.md)
