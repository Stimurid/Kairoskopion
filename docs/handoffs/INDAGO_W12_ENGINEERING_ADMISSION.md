# HEAD-TRIMURTI acceptance of INDAGO W12 handoff — 2026-10-13

This engineering slice answers a different question from article batch processing:
**which evidence-backed, author-revisable publication opportunities arise from
research seeds, scholarly disputes and journal worlds?**

## Authoritative inputs

- Research handoff: `docs/handoffs/INDAGO_MAI_W12_PUBLICATION_OPPORTUNITY_HANDOFF_RU.md` (Indago PR #22).
- Tracking: Kairoskopion issue #24 and draft PR #25.
- Existing execution line: PR #19 package factory, issue #21 P06/P07 adapters.
- Deep venue modeling line: PR #17, PR #18, issue #20.

## Distinctions that must not collapse

- 6 initial scientific directions, 27 semantic versions, 81 venue candidates,
  53 editorial routes, 67 editorial actions and 43 cited source/CFP records
  are **distinct types/counts**, reported by W12 but NOT imported here.
- A proposal, editorial inquiry, and manuscript route are different acts.
- A journal does not become a new journal when a special issue is created.
- A summary, citation or index record does not count as fully read evidence.
- Artikl and the author own semantic manuscript identity and author decisions;
  neither the UI nor Kairon can send to a journal autonomously.

## What this PR proves and what it does not

**CODE_ONLY candidate:** separate immutable opportunity records + events;
fail-closed route policies, coauthor/author decisions, journal identity and
full-text read-depth checks; typed W12 source-byte preflight; Russian read-only
screens for portfolio, matrix, journal passports and variant lineage.

**NOT VERIFIED:** original W12 XLSX bytes, real W12 object import, screenshots
and runtime data hydration, actual P06/P07 submission readiness, live venues.

The W12 workbook was located by name and size in the user's Library, but
raw-byte materialization returned no authorized source path. Consequently the
application must show `BLOCKED_SOURCE_BYTES_UNAVAILABLE`, not fabricate a
successful 53-route ingest. Next engineering step is an authenticated byte
transfer, SHA receipt, schema mapping, source anchors, idempotent import test,
then live API hydration and UI verification.

**No external sending is permitted by this branch.**
