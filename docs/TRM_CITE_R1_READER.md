# TRM-CITE-001 R1 reader — provenance correction (2026-10-21)

Status: code candidate. Not independently reviewed, scientifically certified, merged or deployed.

## Correction of fabricated primary fixtures
The prior snapshot 033c4a6 placed invented primary text under real Descartes and Springer filenames. Independent reviewer correctly rejected both as fabricated evidence. The files have now been deleted. All source texts generated in unit tests are explicitly fictional temporary files without a real author, publisher, DOI, edition or primary locator.

## Witness identity classes
- SYNTHETIC_TEST: an ephemeral fictional test source. The production provider blocks it. Only a test-mode provider may produce a test-only OBSERVED; the production batch consumer rejects all test-only evidence.
- MANUAL_WEB_OBSERVED: an operator-owned, dated, SHA-pinned captured source. It can propose evidence of the operator's reading, but does not imply automatic Indago research or independent V1–V5 certification.
- LIVE_AUTHORIZED_SOURCE_READ: a permitted and allowlisted safe HTTP fetch with pinned expected witness digest and source locator. A transport observation, not scientific claim support.

Permit fields include witness_class, witness_sha256, and the original observed_at for cached text. The provider must not stamp today's time onto older fixture bytes. The current reader checks digest equality, observation age, allowed host before native or injected fetcher, reading depth, unique phrase occurrence, and whether the claimed locator label occurs in the witness body. Synthetic test headers are checked for fictional work, edition, and witness IDs.

Work / Edition / Witness IDs in permits are OPERATOR DECLARATIONS and do not become independently true merely because transport passed. A printed page must be externally proved; finding an arbitrary matching label alone is not page certification. No V1–V5 PASS is generated.

## R1 batch correlation
The batch manifest fixes SHA-256 identities of the Z0 queue, followup tasks and manual protocols. The reader independently reconstructs expected correlation IDs and rejects a mutated request. Completed runs replay from persisted return bytes and verify their recorded SHA against the provider summary, without re-fetching and inventing a new timestamp.

## Actual owner source
The original AORUS R1 corpus has thirteen research actions, five manual cases, four shared Z0 work orders, and three unanchored author-source needs. The only source observation in the owner's real transport canary was the manually read University of Caen electronic Regulae text at AT X 360, with SECTION_TEXT depth and unresolved modern-subject interpretation. It produced one observed manual-source return and twelve blocked results. This observation does NOT originate from the deleted fabricated test files.

## Actual capabilities and limits
The new reader can process permit-authenticated source transport, but a verified native Indago/LitOps primary-text reader remains NOT INTEGRATED, and the three unanchored author-needs remain outside the automatic reader. Indago port discovery provides bibliographic leads and metadata, not automatic fulltext evidence.

All source observations remain claim-support proposals with independent V1–V5 and author gate pending. Fully blocked source attempts result in CLI code 3, indicating scientific unavailability, even when transport persisted everything correctly.

## Acceptance requirements
Run targeted pytest and complete project QA on this exact checkout; require independent review of real witness provenance, restrictions, SHA and locator, replay, security, five-case relation, and source-to-claim meaning. No main merge, journal submission, manuscript mutation or production deployment without explicit author/owner action.


## Operator real-publication transport case, 2026-10-21

Open-access Springer Nature paper: Zawacki-Richter, Marín, Bond & Gouverneur,
"Systematic review of research on artificial intelligence applications in
higher education – where are the educators?", International Journal of
Educational Technology in Higher Education 16, article 39 (2019),
DOI 10.1186/s41239-019-0171-0, publisher URL
https://link.springer.com/article/10.1186/s41239-019-0171-0 , CC BY 4.0.

The operator's authorized safe HTTP fetch retrieved actual publisher HTML,
SHA-256 aa8ae48acf8e7028ddff985261ff9d12db4ac1d558765dd6e5b0a4a35537e8ce.
A reproducible stdlib HTMLParser visible-text derivation with original source
retained produced SHA-256
7bfd3f3c4e290adda7f976075440b479884129ee6e504c5c8567a6512e7fd3d5.
The Abstract section and the assessment-domain phrase are present exactly
once in the derived visible text. Both witness and derivation receipt are
stored in the owner-private AORUS evidence directory, not in this Git branch.

A manually source-authorized, SHA-pinned permit for ONLY task
TRM-CITE-R1-R1-02-1 (Z0 child wo_5c299803f036059ba729) yielded:
13 tasks / 5 cases / 4 distinct original Z0 children /
3 unanchored author-source needs; ONE MANUAL_WEB_OBSERVED / SECTION_TEXT
publisher witness and TWELVE BLOCKED research actions, publication-ready ZERO.
The neighboring R1-02-2 and R1-02-3 tasks were not promoted merely because
they share the same child Z0 reference. This was an operator-pinned cached
public-source read, not an autonomous Indago full-source investigation.
Nothing in the observed publisher article directly warrants the author's
strong normative assessment criterion of reconstructing and transferring
the practice that produced an AI-mediated result.

The R2/R4 candidate repairs are stored in a PRIVATE file
R2_R4_SOURCE_REPAIR_CANDIDATES_20261021.json with three alternatives
and author gate PENDING; no manuscript bytes were altered.
