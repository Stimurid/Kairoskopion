# MAI W12 — published-source acquisition and provisional scholarly criticism

Date: 2026-10-21. Purpose: bulk research on real MAI article seeds under issue #51; author rewriting and external journal submissions are separate and prohibited here.

## Implemented, exercised, reproducible

1. `scripts/fetch_mai_prior_art.py`: reads the authenticated 53-route native Google-Sheets-derived W12 corpus and its existing INDAGO W69 opposition index. Collects DOI-bearing records from Crossref and OpenAlex APIs, verifies returned DOI identity, saves complete raw API JSON and SHA256 evidence, extracts database abstracts with bounded source passages and explicitly records **DATABASE_ABSTRACT**, **DATABASE_METADATA_ONLY**, or unavailable. It never pretends to read publisher full text. Bounded requests and per-DOI cache; the second live 53-route run returned **48 cached API responses / 48 requested**. A DOI occurrence per route is not a distinct publication. Verified run: **53 routes**, **24 unique DOI**, **48 successful provider records**, **178 route-abstract bindings**, zero source fetch errors.
2. `scripts/run_mai_claim_challenge.py`: prepares bounded article/venue/INDAGO scientific context, anchors allowed citations to exact SHA-derived passages from the database abstracts, invokes Codex CLI in read-only mode (structured schema), with a Claude CLI schema-constrained secondary backend on 429. It validates that the returned route IDs and all cited passage IDs exist in the staged corpus, and rejects invented DOI or passage anchors. Every output stays `scientific_claim_accepted=false`, `human_author_gate=HOLD`, `published_fulltext_read=false`, `journal_send_count=0`. Model criticism is provisional and is *not* a professional peer-review certificate.
3. The source-carrying runnable receipts are saved only on authorized AORUS in the private `C:\projects\trimurti\_ops\MAI_W12_PROVIDER_SNAPSHOT_20261020\prior_art_live_first10` and `scientific_model_first10` directories. Author text, contacts, full raw API responses, personal Gmail state, and model outputs have not been added to GitHub.

## Material example: A-NORM
Against the MAI A3/A4 hypothesis of norm revision, the bounded model cites DOI `10.1007/s44163-026-02130-1` (Noller) at an exact database-abstract passage and demands separation of distributed normative mediation from asymmetrically human normative authorization. Suggested discriminating case: same co-produced rule with different legal/collective ratification. This is a useful hypothesis for Artikl's research work. It is **not a full-text verification** or proof of original contribution.

## Acceptance snapshot
- Source/corpus gate: 53/53 authenticated source hash records.
- Source and context Factory: 60 source snapshots (53 W12 and seven prior research/author text projections) and six WhiteCrow family contexts, with cold replay zero duplicates.
- Database source retrieval: 53/53 routes with independent Crossref/OpenAlex retrieval, 24 unique DOI.
- Scholarly model objections: initial 25 accepted as *provisional machine-source-linked* critiques, 24 cite admissible real abstract passages, one abstains. The subsequent remainder requires provider continuity. Claude structured JSON-Schema contract is exercised live. No editorial acceptance, human author pass or submission is claimed.
- Focused private machine tests for source/critique/Factory integration: 46 passed. Full-project CI not asserted.

## Required next stage
Continue batched source-linked criticism for remaining routes without repeating cached Codex runs, then bind each review to 53-item Kanban with `HOLD` status. Require published full-text/venue-native rules and author governance before moving any ArticleSeed to actual author rewrite or send. Issue #51 owns the semantic operation; PR #58 builds on existing Factory PR #46, PR #50 provides local operator board. Source-only publication claims remain false.
