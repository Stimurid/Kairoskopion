# TRM-CITE-001: Z0 source/citation intake (read-only vertical slice)

Status: **IMPLEMENTED IN ISOLATED DRAFT PR / NOT MERGED / NOT A CERTIFIED CITATION VERIFIER**.

## Purpose

Accept all three beginnings of a citation task without losing the original
author's intention:

1. **AUTHOR_DESIRED**: an explicit request in the manuscript or editorial
   comment, such as `[нужна цитата Выготского]`, `тут цитата Выготского`,
   `[citation needed]` or `TODO: cite ...`.
2. **EXISTING**: a preinserted author/year, numbered reference, DOI, Pandoc
   citekey, LaTeX citation, bibliography entry, Word/Zotero field, DOCX
   footnote/endnote or external document hyperlink.
3. **EXISTING / UNATTRIBUTED_QUOTE_CANDIDATE**: quotation-looking text
   without a nearby recognized citation. This is **heuristic**, not a judgment
   that a quotation is wrong, fabricated, or even attributed to a source.

Automatic Artikl suggestions are a future input route. This first slice
implements author wishes and existing references.

## CLI

Run against a **local owner-authorized file**. A native Google Doc requires
an authorized bridge to export its sections/comments/fields; a URL alone is
not a manuscript.

```bash
kairoskopion cite-intake --manuscript /path/to/draft.docx --output-dir /private/citation-evidence
```

Supported direct inputs: UTF-8 Markdown, UTF-8 plain text, DOCX, PDF with
optional `pypdf`, and a structured editor-section JSON envelope. HTML,
images, scanned PDFs without OCR, Google Docs remote API access and complete
Word modern comment threads are not guaranteed. Unsupported parts carry
`coverage.debts`; a successful scan does not mean full coverage of editorial
components.

The output directory contains:

```text
private/citation-evidence/
  original_snapshots/<sha256>.<original extension>
  runs/trm-cite-z0-v03_<first20sha>/citation_intake.json
  runs/trm-cite-z0-v03_<first20sha>/citation_work_orders.jsonl
```

The byte-exact snapshot is created exclusively and its full SHA-256 checked
before the report is recorded. Rerunning the exact same manuscript is
idempotent. A changed manuscript produces a new source hash, a new immutable
snapshot and a different report path. The manuscript itself is never written.

The JSONL file is a **transportable queue of unverified cases** for the
Z2/Indago/Artikl verifier. Each citation group has one coordinating parent in
the report, but only individual members create actionable work orders, so a
three-source parenthetical does not trigger a redundant fourth hunt.
`work_order_id`, `intake_id`, `group_id`, `original_cluster`, exact
source text, snapshot SHA, claim context, V1–V5 statuses and next stage travel
together. Neither external retrieval nor editor mutation is authorized by this
file. Stage R1 is mandatory for existing sources; author wishes start with Z2.
Accented and uncased historical author names use Unicode-aware detection
rather than English-only name assumptions.

The report carries:

- `source`: original path/hash/byte count and snapshot receipt.
- `coverage`: scanned surfaces, extraction debts, and an explicit
  `all_citations_scientifically_verified: false`.
- `intakes[]`: stable ids, entry origin, kind, exact detected fragment,
  original context, source hash, tentative location and any DOCX parent anchor.
- Compound author-year clusters are represented by a full original citation group and individual AUTHOR_YEAR_MEMBER entries linked by group_id, group_index and original_cluster. Unknown cluster members remain typed review debt; each member can have an independent Z4/V1-V5 outcome.
- `repair_cases[]`: one per intake, with either Z2-Z7 route for author wishes
  or R1 initial forensic check followed by conditional R2-R6 full recovery
  for existing citations.

**Every** V1, V2, V3, V4 and V5 starts `NOT_CHECKED`. No external search,
PDF passage read, bibliographic identity verification, scientific support
judgment or author-approved patch takes place in Z0. Text offsets for DOCX
and PDF refer to extracted paragraphs/pages, not a proven clickable native
editor selection.

## Structured editor envelope

A trusted editor connector can serialize native Google Docs sections,
comments and fields into a local JSON file, preserving its own original
document and revision identity. Z0 will read it without calling Google APIs.

```json
{
  "format": "trm-cite-sections-v1",
  "document_id": "opaque-owner-document-id",
  "revision_id": "opaque-editor-revision",
  "coverage": {
    "body": "SCANNED",
    "comments": "SCANNED",
    "footnotes": "UNKNOWN",
    "bibliography": "SCANNED"
  },
  "sections": [
    {
      "surface": "body",
      "locator": "tab-x/p-12",
      "text": "О проблеме см. (Декарт, 1641)."
    },
    {
      "surface": "comment",
      "locator": "comment-c7",
      "parent_anchor": "tab-x/p-12",
      "text": "тут цитата Выготского"
    }
  ]
}
```

Do **not** mark a surface SCANNED unless the connector actually acquired
that source element. A JSON envelope's declared revision is evidence of a
claimed revision, not proof of fresh cloud/editor readback. The byte snapshot
protects the envelope supplied to Z0, not the remote document.

## Gate to Z2-Z7 (for Hephaestus, Artikl and Indago)

The outputs are **working-case candidates**, not accepted citation objects.
For each case the next system must:

1. Read original fragment and human request in full; reconstruct the exact
   target claim and what sort of support/quotation was intended.
2. For existing references, first audit actual Work/Edition/Witness, literal
   phrase, source status and locator. A correct DOI does not prove passage.
3. If invalid or orphaned, enter a new full search: own LitOps corpus and
   authorized external discovery, primary-witness acquisition, independent
   literal/exact-anchor verification, argumentative V4, historical V5 and
   author's contested-meaning gate.
4. Preserve rejection, ambiguity, negative search and the original citation.
   Offer a reversible proposed document diff; never silently replace content.
5. After author decision, verify the emitted manuscript, bibliography,
   actual clickable source witness and current document revision.

Historical case: the presence of `subjectis` in the *Regulae* of Descartes
does not directly verify a later philosophical concept of the subject. Z0
must preserve original owner language and pass the problem to H0-H7.

## Acceptance and release boundaries

Synthetic tests cover Markdown/TXT, Russian author wants, existing author-year,
numbered references/DOIs, footnotes, unresolved direct quotation, DOCX split
Zotero fields, comment anchor, footnote, hyperlink, original bytes, dedup,
structured editor envelope, malformed intake and CLI invocation.

CI in GitHub Actions is the available reproducible test host while
AORUS Remote Desktop Commander registration reports offline. Tests and a
passed Actions run establish **code behavior in that runner**, not installation
under Hestia, successful private manuscript handling, or production readiness.

Observed regression driver: an owner-authorized private 76 KB article had 43 author-year parentheticals, mostly multi-source. The v01 scanner recognized only two because it required a single author-year token per parentheses; v02 adds cluster and member detection; v03 handles multilingual names and persists individual verification work orders. Do not expose private article text to public fixtures. Source-evidence receipt remains in the private AORUS audit directory.

Future tests:
- DOCX with complex tracked changes and threaded comments.
- Google Docs connector fetch and *real* comment/tab/field coverage readback.
- False-positive detection on prose about citation vs author instructions.
- Correct alignment of Native Word, Google Docs UTF-16 and PDF text offset.
- Full independent V1-V5 on authorized source texts.
- Bulk 10-50 ArticleVersions without duplicate case/source creation.

Canonical research spec: https://docs.google.com/document/d/1ap5BA9vFo2QhCSJnjL1-KDr_pcZZeGmDg0QjB_bCkDo/edit

Architecture/donors: https://docs.google.com/document/d/1gVAApoGCjdSdkJpG4moa1efcUXObmjmlisDgntAiE2g/edit

Related draft PR #55: venue reference-count/recency rules independent of source verification.
