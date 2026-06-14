# Venue Funnel and Profile Package — v1.0

**Status:** canonical reference. Authoritative for venue discovery, profiling
and database building. Supersedes the v0 discovery scope restrictions
(see [DECISIONS.md](DECISIONS.md) ADR-16).

**Companions:**
- [FIELD_POSITION_MODEL.md](FIELD_POSITION_MODEL.md) — single coordinate
  space (article = point, venue = envelope).
- [PUBLICATION_INTEGRABILITY_MODEL_v1.md](PUBLICATION_INTEGRABILITY_MODEL_v1.md)
  — authoritative integrability model; this document is the venue-side
  expansion of §1 / §6 / §11 of v1.0.
- [VENUE_REGISTRY_ARCHITECTURE.md](VENUE_REGISTRY_ARCHITECTURE.md) — persistence
  with provenance (`VenueRecord` / `VenueSource` / `VenueClaim` /
  `VenueEvidencePack`). VenueProfilePackage maps onto this registry.
- [SOURCE_ADAPTER_AUTHORITY_CONTRACT.md](SOURCE_ADAPTER_AUTHORITY_CONTRACT.md)
  — authority levels for sources used in the funnel.
- [VENUE_CORPUS_PROFILER_V2.md](VENUE_CORPUS_PROFILER_V2.md) — corpus mining
  policy referenced from layer 8 of the funnel.
- **[VENUE_DISCOVERY_TRADECRAFT.md](VENUE_DISCOVERY_TRADECRAFT.md)** —
  operator playbook with accumulated URL-pattern lifehacks, aggregator
  allowlist, auth strategy, cross-listing inference, anti-patterns.
  **Required reading before any new discovery session** — saves
  re-inventing workarounds and burning classifier budget.

**Status of code:** purely additive specification. No schema change is
mandated by this document. Code alignment will go through separate
backlog packages (see appendix C).

---

## 0. Главный тезис

Публикуемость статьи определяется не «похожестью» на журнал по
ключевым словам и не формальным соответствием шаблону. Она определяется
тем, может ли работа быть распознана как осмысленный академический ход
внутри конкретного дисциплинарного сообщества, школы, лагеря,
publication regime и конкретного venue (или его раздела / спецвыпуска).

После Mavrinsky golden-run модель журнала нельзя мыслить как
«карточку журнала». Она должна быть **симметрична модели статьи**.
Если статья описывается через `FieldPositionModel(article)`, то журнал
должен описываться как **envelope в том же пространстве**.

Одна и та же `FieldPositionModel` описывает:

- статью — точку или компактный регион;
- журнал — envelope;
- секцию — подрегион;
- спецвыпуск — подрегион + временной коридор;
- редколлегию — облако точек;
- корпус опубликованных статей — эмпирический hull;
- дисциплину — регион верхнего уровня.

Fit = **containment + distance + adaptation cost + core-risk + unknowns**.
Это не score. Это многомерное отношение координат.

«Модель журнала» в Kairon — это не название, ISSN и требования.
Это **реконструкция публикационного контейнера как места распознавания
академического хода**.

---

## 1. Воронка: от широкой области к конкретной редакционной сцене

Discovery — не один шаг и не один запрос к LLM. Это воронка из восьми
слоёв. На каждом слое:

- есть свои источники данных (см. §3),
- есть своя authority-разметка,
- есть свой набор полей в `VenueProfilePackage`,
- есть фиксированный момент, когда выбор может остановиться (если уже
  ясно, что journal не подходит — не идём ниже).

### Слой 1 — Venue universe / broad direction

Не выбираем журнал. Определяем **класс публикационных контейнеров**:
философия техники, STS, media studies, digital culture, HCI/design
theory, AI ethics, education, sociology of knowledge, art & science,
междисциплинарные форматы, и т.д.

Данные грубые: subject categories, indexing categories, publisher
taxonomy, OpenAlex topics, Scopus/WoS/DOAJ categories, ключевые слова
сайта, дисциплинарные рубрики, названия разделов.

Слой разведки, не решения.

### Слой 2 — Disciplinary regime

Не «тема», а **как в этой области принято доказывать, писать и
распознавать вклад**. Статья Mavrinsky по объекту касается
interface/theory/technology, но по режиму аргумента она
континентально-философская.

Аналогично журнал: может иметь "technology" в scope, но фактически
публиковать STS case studies, analytic philosophy of artifacts, HCI
empirical papers или continental media philosophy.

Для журнала строим:

- `discipline_envelope`
- `argument_move_envelope`
- `evidence_type_envelope`
- `method_envelope`
- `genre_envelope`

### Слой 3 — Tribe / school / camp

Не «discipline = philosophy of technology», а:

- Simondon / Stiegler / Hui;
- Heideggerian technics;
- Deleuze / Guattari / Foucault / Agamben;
- Latour / ANT;
- platform studies;
- HCI / dark patterns;
- analytic artifact theory;
- русская методологическая школа;
- critical theory;
- media archaeology;
- ...

> Дисциплинарные границы **jagged** и **культурно-зависимые**: США vs
> Германия vs Россия vs Франция — разные дисциплины, разные их границы,
> разные школы внутри одной и той же номинальной дисциплины (аналитическая
> vs континентальная философия — самый явный пример).

Для статьи: `school_affiliation_vector + citation_network_signature`.
Для журнала: `school_envelope + typically_cite + dangerous_missing_names +
published_polemics + editorial_board_cloud`.

«Простой список школ» (`schools_and_traditions: ["Simondon", "STS"]`)
ничего не вычисляет. Только связка
`school_affiliation_vector + citation_network_signature + venue_envelope`
позволяет видеть дистанцию, containment и цену адаптации.

### Слой 4 — Venue class

Journal vs section vs special issue vs proceedings vs edited volume vs
book series vs open review vs preprint reviewed.

`focus_level`: Q1/Q2 primary, Q3/Q4 supported-non-focus, local/VAK,
proceedings, zine/author collection/backlog.

Журнал не выбирается только по престижу. Он выбирается как **контейнер
определённого режима публикации**.

### Слой 5 — Конкретный журнал как envelope

Появляется `JournalModel` со всем что в нём есть: canonical title,
ISSN, publisher, URLs, scope, instructions, editorial board, submission,
OA, policies, indexing, metrics, subject categories, official claims,
verified metadata, source refs, last_checked, unknowns.

MVP: title, publisher, URLs, scope, instructions.
Full: + ISSN, indexing, metrics, publisher systems, policies, sections.

### Слой 6 — Section / article type / special issue

**Критично.** Журнал как целое может быть широким, но конкретная секция
принимает только essays, review articles, forum pieces, methods papers,
book reviews, case studies.

`SectionModel`: section name, article type, scope, requirements, typical
structure, editor refs, recent article refs, fit notes, evidence refs,
unknowns.

`SpecialIssueModel` / CFP: title, theme, deadline, editors, article
types, submission URL, target disciplines, expected articles.

Часто fit на section / special issue точнее, чем fit на «журнал вообще».

### Слой 7 — Editorial board as cloud

Не психологический profiling людей. Дисциплинарный и социальный сигнал.

`EditorialBoardProfile` содержит: editor-in-chief, associate/section
editors, institutions, countries, disciplines, known research areas,
recurring theoretical traditions, network notes, board turnover,
confidence, ethical notes.

Derived signals: disciplinary center of gravity, geographical center,
methodological center, theoretical openness, likely audience,
gatekeeping risks.

> Жёсткое ограничение: derived signals должны быть помечены как
> `inference`. Нельзя писать «редколлегия не любит ИИ» по двум именам.
> Можно писать: «available board data does not show strong AI/STS
> representation; confidence low».

### Слой 8 — Published corpus as empirical hull

Корпус того, что журнал реально публикует.

Режимы:

- `seed_profile`: 8–12 статей;
- `working_profile`: 25–35;
- `robust_profile`: 50–80;
- `special_issue_profile`;
- `section_profile`.

Поля: selection strategy, date range, collected count, metadata/fulltext
completeness, PDF/HTML/abstract-only counts, language/section
distribution, bias notes.

> Если пользователь загрузил zip с 20 статьями — это валидный корпус,
> но `selection_strategy = user_uploaded_pack` и `bias_notes` должны
> сказать, что это не независимая выборка.

### И только после этого — FitAssessment

Не «журнал подходит». Многомерное отношение по 16 осям:
topic, discipline, tribe, school, argument_move, method, evidence_type,
citation_ecology, novelty, audience, language_register, genre,
formal_compliance, author_eligibility, publication_regime,
trust_compliance.

См. [PUBLICATION_INTEGRABILITY_MODEL_v1.md §8](PUBLICATION_INTEGRABILITY_MODEL_v1.md).

---

## 2. VenueProfilePackage — связанный пакет, не плоская VenueModel

```text
VenueProfilePackage:
  venue_identity
  journal_model
  section_models
  issue_or_special_issue_models
  publication_regime_model
  venue_field_position
  venue_envelope
  formal_submission_profile
  indexing_and_metrics_profile
  editorial_board_profile
  published_article_corpus
  published_article_patterns
  citation_expectation_profile
  method_expectation_profile
  genre_move_profile
  style_register_profile
  author_eligibility_profile
  time_review_profile
  apc_access_profile
  trust_compliance_profile
  tacit_venue_signals
  source_evidence_packet
  unknowns_and_conflicts
```

### 2.1 venue_identity

Факты идентификации: canonical name, aliases, ISSN/eISSN, publisher,
country, languages, website URL, submission system, official pages.
Берётся из сайта журнала, издателя, Crossref, ISSN, DOAJ, OpenAlex,
Scopus/WoS/SJR/РИНЦ/ВАК-snapshots. Каждый источник имеет **разный
authority status** — см. §3.

### 2.2 journal_model

Журнал как serial venue: homepage, aims/scope, author guidelines,
editorial board URL, submission URL, OA/policies/indexing/metrics URLs,
subject categories, official claims, verified metadata, unknowns.
(Прежний `JournalModel`.)

### 2.3 publication_regime_model

**Не «о чём журнал», а как там происходит публикация:** peer review
clarity, double blind / open review / editorial review, article type
gates, desk rejection patterns, typical decision time, special issue
logic, APC, OA, language regime, author eligibility, compliance burden.

Источники: author guidelines, editorial policies, submission pages,
publisher platform, иногда пользовательский опыт и review outcomes.

### 2.4 venue_field_position

Координата журнала в том же пространстве, что и статья: disciplines,
schools, argument moves, evidence types, method stance,
audience/register, temporal depth, institutional/geographical signals.
Смесь official scope + corpus mining + board profile + inference.
См. [FIELD_POSITION_MODEL.md](FIELD_POSITION_MODEL.md).

### 2.5 venue_envelope

Диапазоны допустимости. Например:

```
continental_philosophy: [0.2, 0.7]
STS:                    [0.3, 0.8]
empirical_conceptual_hybrid: [0.4, 0.9]
pure_theoretical_essay: [0.0, 0.3]
```

Сравнивается со статьёй: журнал = envelope, статья = point/region.

### 2.6 section_models, issue_or_special_issue_models

Fit часто точнее на секцию / special issue / research topic / forum,
чем на журнал в целом.

### 2.7 editorial_board_profile

Облако людей / институций / традиций. Center of gravity, не решение.
Для философского журнала может быть решающим: continental / analytic /
STS / education / cultural studies — разные «племена», даже если scope
формально широкий.

### 2.8 published_article_corpus, published_article_patterns

Эмпирическое тело журнала. Показывает что реально проходит: titles,
abstracts, article structures, methods, theory shoulders, citation
ages, languages, author geographies, genre moves, section patterns,
lengths, reference counts, use of cases/data.

### 2.9 citation_expectation_profile

Не «сколько ссылок», а **какие имена/школы обычно делают статью своей
в этом журнале**. Для Mavrinsky это ключ: один журнал примет тему
интерфейса при условии Simondon/Stiegler/Hui; другой — Manovich/Galloway;
третий — Latour/platform studies; четвёртый — Deleuze/Agamben/Foucault.
Отсутствие нужного имени — не всегда ошибка, а pathway-specific signal.

### 2.10 trust_compliance_profile

Отделяет качество и риски: peer review clarity, indexing/archiving,
persistent identifiers, fee transparency, license clarity,
COPE/DOAJ/OASPA signals, predatory risk.

### 2.11 source_evidence_packet

Никогда не смешивать источники. Official guideline ≠ corpus inference.
Indexing claim на сайте издателя — vendor claim, пока не проверен.
Board inference — inference. Пользовательский опыт — tacit signal.

> В UI это должно быть видно: Venue Space обязан показывать source
> freshness, unknowns, conflicts и уровни уверенности. Формальные
> требования из official guidelines имеют более высокий статус, чем
> corpus inference. Indexing со страницы издателя — vendor claim
> unless independently verified.

### 2.12 unknowns_and_conflicts

UNKNOWN ≠ absent. Если не нашли политику AI disclosure — это не
значит, что её нет. Это значит `not_verified`.

---

## 3. Источники данных по слоям

Для каждой категории фиксируется: **что берём**, **какой authority
status**, **на каком слое воронки задействована**.

См. также 6 уже реализованных адаптеров в `adapters/venue/`:
OpenAlex / Crossref / DOAJ / Unpaywall / OpenCitations / SnapshotCrawler.
Они покрывают часть категорий C / E / G ниже.

### A. Сайт журнала

```
homepage
canonical title
ISSN/eISSN if listed
publisher
aims & scope
sections / article types
instructions for authors
word count
abstract requirements
reference style
template
language policy
submission portal
peer review description
OA/APC policy
license
ethics/COI/data/AI policy
editorial board page
special issues / CFP
archives / recent issues
contact info
```

**Authority:** `formal_page` / `official_claim`. Высокая для формальных
требований и self-description.

**Caveat:** сайт часто врёт гладкостью. Scope широкое — реальные статьи
узкие. Peer review описан общо. Indexing может быть vendor claim.
Редколлегия может быть устаревшей. Стиль может расходиться с практикой.

**Слои:** 5, 6, 7 (board URL), 4 (article types).

### B. Сайт издательства и платформа подачи

```
publisher identity
journal portfolio
publisher-level policies
ethics policy
OA/APC/payment terms
license variants
submission system
template/package requirements
metadata standards
journal transfer network
special issue platform
article processing workflow
copyright/self-archiving rules
```

Важно для Elsevier / Springer / Taylor / Sage / MDPI / Frontiers / Brill /
De Gruyter — часть правил живёт не на странице журнала, а на издательском
уровне.

**Authority:** `formal_page` / `vendor_policy`.
**Слои:** 5, 6.

### C. Индексаторы и реестры

**Локально (Россия):**
```
ВАК / перечень специальностей
РИНЦ / eLIBRARY
КиберЛенинка / НЭБ
сайт журнала при университете/издателе
архив выпусков
требования по научным специальностям
```

**Международно:**
```
Scopus / Sources
Web of Science / Master Journal List / JCR
DOAJ
OpenAlex Sources
Crossref journal metadata
ISSN Portal
Scimago / SJR snapshot
Sherpa / Unpaywall (OA, self-archiving)
COPE / DOAJ / OASPA membership
```

**Authority spread:**

- Scopus / WoS / JCR — высокий для индексации и метрик, **закрыты/платны**.
- OpenAlex / Crossref / OpenCitations — хороший открытый
  metadata/citation backbone, **не заменяют журнальные требования**.
- DOAJ — хорош для OA и trust.
- Sherpa / Unpaywall — policy / OA / self-archiving, **не genre fit**.

> Из MVP-стека: build-now — OpenAlex, Crossref, OpenCitations, manual
> URL snapshots, GROBID, Litops, existing LLM provider. Build-soon —
> DOAJ, Sherpa-like, Semantic Scholar, Unpaywall, AnyStyle / CERMINE /
> citation-js, PhilPapers / PhilEvents. Closed/paid (Scopus/WoS/JCR/
> Dimensions/Lens/Altmetric/Scite) не должны блокировать MVP — они
> деградируют в `UNKNOWN_NOT_VERIFIED`.

**Слои:** 1, 2, 4, 5, частично 6, 10 (trust/compliance).

### D. Корпус опубликованных статей журнала

**Что собираем:**

```
latest articles
articles by section
special issue articles
most cited articles
topic-matched articles
editorial-selected / user-uploaded pack
PDF/HTML/abstracts
metadata: DOI, dates, authors, affiliations
titles / abstracts / keywords
section labels
article types
reference lists
full-text structures if accessible
```

**Что реконструируем:**

```
published_article_patterns
genre / move profile
typical introduction pattern
method explicitness
theory shoulders
citation expectation
reference count distribution
median reference age
article length distribution
section structure
case / data presence
empirical vs conceptual balance
language / register
author geography
institutional patterns
special issue dynamics
```

**Authority:** `corpus_observation`. Сильный сигнал о реальной практике
журнала, но **не равен official policy**. Если 30 последних статей все
STS-case-based — это сильный empirical hull, но не формальное правило.

**Слои:** 5, 6, 8, plus feeds into 2.

### E. Редколлегия — биографии и публикации

С сайта журнала берём список редакторов. По каждому, насколько возможно:

```
affiliation
country / institution
discipline
department / school
personal page
ORCID
Google Scholar profile
Scopus / WoS author page if accessible
OpenAlex author
recent publications
key topics
coauthor networks
editorial roles
section responsibilities
```

**Из этого НЕ делаем** «психологию редактора».
**Делаем:**

```
disciplinary center of gravity
theoretical traditions represented
methodological center
geographical center
institutional prestige cluster
board openness to topic
missing representation
possible gatekeeping risks
section-specific editors
```

**Authority:** `inference` (board), `external_claim` (publication
metadata). Confidence: low — сильные утверждения по 2 именам запрещены.

**Слои:** 7.

### F. Биографии и публикации авторов, которые журнал публикует

Отдельный слой от редколлегии. По корпусу статей смотрим:

```
who publishes there
countries
institutions
career stage if visible
single-author vs multi-author
local vs international authors
repeat authors
editorial-board self-publication risk
invited / special issue clusters
```

Помогает `author_eligibility_fit` и `geo_institutional_position`.
Для русских / санкционных / аффилиационных рисков — важно. Отделять
факты от догадок.

**Authority:** `corpus_observation`.
**Слои:** 8, plus feeds into 2.11.

### G. Google Scholar, Semantic Scholar, OpenAlex, Crossref, OpenCitations

**Google Scholar** — человеко-ориентированная поверхность:

```
editor publication traces
journal article discoverability
citation clusters
author schools
related works
actual cited / citing ecology
```

Неудобен и не всегда API-friendly. Используется как secondary
recall-увеличение, не primary backbone.

**OpenAlex / Semantic Scholar / Crossref / OpenCitations** — для
воспроизводимых данных:

```
works metadata
authors
venues / sources
citations / references
topics
concepts
DOI validation
publisher metadata
open citation graph
```

**Authority:** `metadata_api` для OpenAlex/Crossref/OpenCitations.
Scholar — `external_claim` с пометкой нестабильности access pattern.

**Слои:** 1, 2, 5, 7 (editor pubs), 8 (citation ecology).

### H. Full-text access

```
journal HTML/PDF pages
publisher PDF
DOAJ / OA full text
institutional repositories
author personal pages
Academia.edu
ResearchGate
Internet Archive Scholar
Zotero / personal library
user-uploaded ZIP / PDF pack
shadow library resolvers
Telegram / article exchange packs
```

**Принцип разделения:** полный текст нужен для genre / move / citation /
style mining. **Но источник полного текста не обязательно авторитетен
для метаданных журнала.**

В Kairon это должно быть `FullTextResolver` / `ShadowFullTextResolver` /
`PersonalLibraryAdapter`. Он даёт `fulltext_available`, `parsed`,
`partially_parsed`, `failed`, `source_access_status`, `rights/risk note
if needed` — но **не говорит «журнал такой-то»**. Метаданные и политики
проверяются отдельно.

**Authority:** `corpus_observation` (текст), **не** `formal_page`
(метаданные).

**Слои:** 8.

### I. CFP, спецвыпуски, ассоциации, Telegram-каналы, сообщества

Discovery layer, не core authority:

```
special issue calls
research topic pages
association CFPs
conference tracks
publisher topical collections
society newsletters
Telegram CFP channels
mailing lists
PhilEvents / PhilPapers
community websites
```

Из них строим `SpecialIssueModel`, `ResearchTopicModel`, `CFPModel`,
возможно `CommunityVenueMemory`.

**Backlog adapters:** CFPChannelAdapter, AssociationSiteAdapter,
TelegramCFPAdapter, CommunityVenueMemory, SpecialIssueWatcher.

**Authority:** `external_claim` / `vendor_claim`.
**Слои:** 6.

### J. Пользовательский опыт / tacit signals

Невозможно надёжно достать из веба:

```
пользователь уже подавался
редакция отвечала так-то
review занял столько-то
просили такой-то тип правки
отказали по причине X
коллега публиковался там
редактор на конференции говорил Y
есть спецвыпуск через знакомую сеть
```

Это `TacitVenueSignal` / `VenueMemory`, **не факт**. Обязательно: источник,
дата, confidence, scope. Нельзя смешивать tacit signal с official policy.

**Authority:** `tacit_signal`.
**Слои:** 7, 10 (regime / outcomes).

---

## 4. Что реконструируем по каким материалам

| Материал | Реконструируем | Authority этого вывода |
|---|---|---|
| Author guidelines / instructions | article types, word count, abstract, keywords, structure, reference style, templates, language, peer review, AI/data/ethics/COI policies, submission files, cover letter, anonymization, APC/OA, copyright/license | `official_fact` (если страница свежая) |
| Aims / scope | declared disciplines, themes, audience, novelty mode, article types, interdisciplinarity | `official_claim` — self-description, не доказывает реальную практику |
| Корпус статей | реальные жанры, disciplinary registers, theory shoulders, argument moves, методы, citation ecologies, язык, плотность, structure, presence/absence of cases/data, reference recency/depth, author geography, section distribution | `corpus_observation` → feeds `PublishedArticlePattern`, `GenreMoveProfile`, `CitationExpectationProfile`, `MethodExpectationProfile` |
| Editorial board | editorial cloud, disciplinary center of gravity, school openness, methodological center, geographic/institutional center, section-specific gates, missing expertise, possible alignment with article tribe | `inference` — confidence low по умолчанию |
| Indexers / Scopus / WoS / DOAJ / ВАК | verification of identity, indexing status, subject categories, quartile/metrics snapshot, OA/trust signals, country/publisher metadata, archive/persistent identifiers | `external_claim` / `registry_card` |
| Publisher pages | platform rules, portfolio bias, transfer networks, ethics/OA, submission tech, global author rules, copyright/self-archiving, APC | `vendor_policy` |
| OpenAlex / Crossref / OpenCitations / Scholar / Semantic Scholar | article metadata, references/citations, editor/publication traces, venue graph, topic graph, citation ecology, author/institution graph, DOI sanity | `metadata_api` (открытые) / `external_claim` (Scholar) |
| Full-text (журнал, OA, repo, Sci-Hub-like, личная библиотека, user ZIP) | corpus mining only — **не authority для метаданных журнала** | `corpus_observation` |

---

## 5. Симметрия article ↔ venue (после Mavrinsky)

| Side | Object | Shape |
|---|---|---|
| Article | discipline_vector | point / region |
| Venue | discipline_envelope | hull (min, max per dim) |
| Article | school_affiliation_vector | point / region |
| Venue | school_envelope | hull |
| Article | argument_move_vector | point / region |
| Venue | argument_move_envelope | hull |
| Article | evidence_type_profile | point |
| Venue | evidence_type_envelope | hull |
| Article | method_stance | structured |
| Venue | method_envelope | hull + constraints |
| Article | citation_network_signature | must / typically / never / conspicuous_absence |
| Venue | citation_expectation_profile | typically_cite / dangerous_missing / canonical_must_cite |
| Article | genre_position | point |
| Venue | genre_envelope | hull |
| Article | audience_level / language_register | point |
| Venue | audience_register_envelope | hull |
| Article | protected_core | list of non-negotiables |
| Venue | published_polemics / avoided_polemics | what venue tolerates / forbids |
| Article | readiness | formal_compliance_score, completeness |
| Venue | formal_requirements + publication_regime_model | hard constraints |

Fit-формула:

```
article point/region  ⊂ ? ⊃ ? ↔ ?  venue envelope
                              + distance by axis
                              + what can be adapted
                              + what requires citation bridge
                              + what requires genre shift
                              + what requires method shift
                              + what destroys protected core
                              + what is unknown because source absent
```

---

## 6. Режимы глубины профилирования

### Quick

```
official site
aims / scope
author guidelines
indexing claim
5–10 latest articles
unknowns list
```

### Standard

```
official site + publisher
guidelines / policies
editorial board
20–35 recent / section articles
OpenAlex / Crossref / OpenCitations metadata
citation expectation sketch
genre / move pattern
```

### Deep

```
50–80 articles
section / special issue split
editorial board publication graph
citation ecology
reference distributions
author geography / institution graph
policy verification via external sources
indexing snapshots
special issue history
tacit signals / prior outcomes
```

Совпадает со старым сценарием single venue в спеке:
quick = site + requirements + 5 articles; standard = + board + 20
articles; deep = 35–50 articles + citation ecology + reviewer simulation.

---

## 7. Двухстадийная LLM-семантика «база → сеть»

Поиск ведётся LLM-агентом. Стадия 1 — по локальной базе
(`VenueRecord` + `VenueEvidencePack` corpus). Стадия 2 — по сети
(адаптеры + browse по разрешённому списку источников).

Cache-miss таксономия:

| Состояние | Триггер | Действие |
|---|---|---|
| `absent` | в базе нет `VenueRecord` под кандидата | агент строит с нуля через сеть → кладёт в базу |
| `stale` | `VenueRecord` есть, но `last_checked` за пределами `freshness_window` для типа источника | точечное освежение конкретных claim'ов, не полная пересборка |
| `weak_evidence` | claim'ы есть, но `evidence_status` не покрывает оси текущего запроса | дотягиваем только недостающие axes / claim-paths |
| `fresh_sufficient` | покрытие достаточно для текущего fit-вопроса | LLM-ключ не сжигается, ответ из базы |

> Принцип: **горячий путь — детерминированная композиция из базы.
> LLM на сети — только при cache-miss соответствующей категории.**
> Это ровно ответ на «чтобы не делать через LLM-ключ».

Allowlist источников сети — §3 (A–J). Произвольное гугление запрещено.

---

## 8. Mirror gold: эталон для venue-стороны

По аналогии с Mavrinsky golden-run для статьи нужен зафиксированный
**venue benchmark**:

- 3–5 эталонных журналов разных режимов (один continental philosophy,
  один STS, один HCI/design, один analytic philosophy of technology,
  один media studies);
- для каждого — заморожённый snapshot источников по §3 (A–J);
- эталонный `VenueProfilePackage`, собранный руками и подписанный как
  ground truth;
- детерминированный прогон агента-собирателя против gold + diff;
- CI падает, если агент стал хуже.

Gold обновляется руками **только** при изменении модели или при
доказанной ошибке в эталоне (как и Mavrinsky article gold).

---

## 9. Самая короткая формула

```
Journal is not a page, not a scope statement, not a quartile.

Journal = publication envelope:
  formal rules
  declared scope
  actual corpus hull
  editorial-board cloud
  citation ecology
  genre / method norms
  section / special-issue subregions
  publication regime
  trust / compliance layer
  tacit memory

Article = publication point / region:
  academic move
  field position
  tribe / school position
  citation signature
  evidence type
  method stance
  protected core

Fit = relation:
  containment + distance + adaptation cost + core-risk + unknowns.
```

Это центральный инвариант. Журнал строится не «для базы журналов», а как
**вторая половина той же координатной системы**, в которой строится
модель статьи.

---

## Appendix A. Supersedes

Этот документ отменяет ограничения скоупа из:

- [REAL_VENUE_POOL_DISCOVERY_V0_IMPLEMENTATION_MAP.md](REAL_VENUE_POOL_DISCOVERY_V0_IMPLEMENTATION_MAP.md):
  - *«Not an all-journal database»* — отменяется. Корпус готовых
    `VenueProfilePackage` со временем строится (см. §7).
  - *«Not web crawling»* — уточняется. Произвольный crawling по-прежнему
    запрещён, но allowlist §3 (A–J) разрешён.
  - *SnapshotCrawler «explicit URL only, not search»* — снимается для
    стадии 2 (network) при cache-miss; SnapshotCrawler по explicit URL
    остаётся как один режим.
  - Запреты на Google Scholar / publisher pages / aggregators отменены.
- [VENUE_CANDIDATE_SCREENING_V0.md](VENUE_CANDIDATE_SCREENING_V0.md):
  - Скрининг по 7 осям остаётся, но axes расширяются до 16 v1.0
    `FitAssessment` axes (см. PUBLICATION_INTEGRABILITY_MODEL_v1.md §8).
  - Правило *«User-seed-only candidates cannot be screened_in»* остаётся.

v0-документы НЕ удаляются. Они помечаются `Status: superseded` в шапке
и остаются как историческая запись MVP-скоупа.

## Appendix B. Extends / reuses

- **Extends** PUBLICATION_INTEGRABILITY_MODEL_v1.md §6 — VenueProfilePackage
  это 24-частная декомпозиция плоского `VenueModel`.
- **Reuses** FIELD_POSITION_MODEL.md envelopes для `venue_field_position`
  и `venue_envelope`.
- **Reuses** VENUE_REGISTRY_ARCHITECTURE.md — каждый компонент пакета
  серилизуется через `VenueRecord` + `VenueSource` + `VenueClaim`
  с явным `claim_path` per layer.
- **Reuses** SOURCE_ADAPTER_AUTHORITY_CONTRACT.md — authority levels из
  §3 (A–J) совпадают с контрактом.

## Appendix C. Code alignment backlog

Это спецификация. Код не меняется этим документом. Когда дойдёт черёд:

| Шаг | Что добавить | Где |
|---|---|---|
| C1 | Enum `VenueFunnelLayer` (8 значений: universe, regime, tribe, class, journal, section, board, corpus) | `enums.py` |
| C2 | Dataclass `VenueProfilePackage` агрегирующий 24 субмодели | `schema.py` |
| C3 | Dataclass `CitationExpectationProfile`, `MethodExpectationProfile`, `GenreMoveProfile`, `StyleRegisterProfile`, `AuthorEligibilityProfile`, `TimeReviewProfile`, `APCAccessProfile`, `TacitVenueSignal` | `schema.py` |
| C4 | Service `venue_profile_package_builder` принимает `VenueRecord + claims` → `VenueProfilePackage` | `services/` |
| C5 | Service `venue_funnel_navigator` принимает `ArticleModel + FieldPositionModel(article)` → ordered list of (layer, candidates) | `services/` |
| C6 | Agent `VenueDiscoveryFunnel` с LLM + детерминированным fallback, дополняет существующий `VenueProfiler` | `agents/` |
| C7 | Cache-miss таксономия §7 как enum + policy hook в discovery agent | `services/` |
| C8 | Backlog adapters категорий H, I, J — `FullTextResolver`, `CFPChannelAdapter`, `TacitVenueSignalImporter` | `adapters/` |
| C9 | Mirror gold corpus + bench harness | `tests/fixtures/venue_gold/` + `tests/test_venue_funnel_benchmark.py` |

Каждый шаг — отдельный feature branch и BACKLOG-пакет.

## Appendix D. Open questions

1. **Jagged disciplinary boundaries by culture.** Нужен ли отдельный
   `DisciplineCulturalVariant(culture, discipline, boundary_notes,
   sources)` как первоклассная сущность, или это слой нормализации
   поверх существующего `discipline_vector` с culture как координатой?
   Решение пока отложено — фиксируется как открытый вопрос для §1
   слой 2.
2. **Section vs special issue vs research topic vs forum** — все
   четыре имеют разную семантику. Сейчас в спеке есть `SectionModel`
   и `SpecialIssueModel`. Нужен ли `ResearchTopicModel` отдельно — или
   это специальный случай special issue?
3. **Tacit signals provenance.** Как формализовать «коллега сказал»
   без потери приватности и без подделки? Возможно — отдельный
   `private_tacit_layer` с пользовательской подписью и невыгружаемый
   в bundle.
4. **Two-stage budget control.** При cache-miss `weak_evidence` сколько
   axes можно дотянуть за один LLM-вызов до перехода в `absent`?
   Это политика, не спека.

Эти вопросы НЕ блокируют использование документа как канона. Они
фиксируются здесь, чтобы при возврате к ним было видно, что они
известны и сознательно отложены.
