# LOKI R1 - read-only official-rule source bridge

STATUS: CODE CANDIDATE / FIXTURE PASS. Not yet a trusted LitOps source admission,
Artikl author acceptance, Factory integration or production release.

## Reuse, not a competing Factory
R1 reuses the existing SourceSnapshot, SourceAuthorityClaim, VenueSource,
VenueClaim, ArtiklArticleProjection, ArtiklStatePointer, TargetWorldSnapshot
models. No new global source-to-seed engine or canonical World/Field authority.

The adapter in src/kairoskopion/loki/read_only.py reads locally pinned
publisher-page bytes and validates SHA-256, exact hostname allowlist, secure
relative path under authorized root, HTML text quote, and source/venue/claim
identity joins. It can link an Artikl semantic projection at an explicit version
to a TargetWorldSnapshot. It does not mutate or fetch anything on the network.

## Crucial boundary: local evidence is not remote publisher authenticity
Even if a caller has named a publisher URL, a file on disk and an internal
SourceAuthorityClaim can be forged. Byte/quote alignment alone CANNOT
authenticate the source producer or grant FULL_REAL_EVIDENCE. For this
reason evidence is emitted as Verification.PARTIAL, never VERIFIED. The
R0 engine therefore reports hypothesis status INDETERMINATE unless a
separate trusted producer certifies the source through established LitOps
authority with a persisted and replayable receipt.

The adapter may suggest an observational statement about the publicly
published rules, but cannot infer undisclosed editorial preferences,
acceptance probabilities, author approval, manuscript quality, or publication.

There are no SEND/MAIL, Field mutation, TargetWorld overwrite, staging or
production writes. The adapter itself has zero I/O writers.

## Case selected: MAI scientific head E
The W12 route catalogue contains E-JUSTICE for Teaching in Higher Education
and E-WARRANT for European Journal of Education:
https://docs.google.com/spreadsheets/d/1ryG1wsEJWyJMnK-QM5v-AluNc_yXL6NU_T3a55t-Y1U/edit

Official publisher rules (independently inspected) support conceptual
articles, subject to their respective critical/political or institutional
and assessment-focus constraints:
https://think.taylorandfrancis.com/special_issues/the-politics-of-assessment/
https://onlinelibrary.wiley.com/page/journal/14653435/homepage/call-for-papers/si-2026-000865

That is evidence against the literal formal exclusion hypothesis only.
It does NOT demonstrate that either editor will accept this particular
article or that a canonical Artikl revision has been admitted.

AORUS saved one public publisher HTML source and computed its digest in
a separate private, uncommitted directory. Running the separate private
case-analysis script was blocked by an access check; do not claim a
successful machine-executed case. The second publisher returned a browser
protection challenge on direct PowerShell acquisition. Neither source
became a trusted LitOps runtime receipt in this stage.

## Verification
57 targeted tests across R0/R1; 21 R1 cases. Negative checks include fake
publisher hosts, local-source alteration, wrong journal identity, unsourced
quote, missing read depth, path escapes, forged local publisher page,
mis-scoped authority, and attempts to use formal policy as active/editorial
outcome evidence. Full non-network suite must pass under isolated test
dependencies and a short Windows pytest base temp. Review receipts in PR.

NEXT: independent review of a stacked draft PR; a trusted immutable source
ingestion readback with producer authority and one owner-authorized MAI
article revision, then preregister and execute a truly source-certified
discriminating probe. This read-only adapter does not alter core Factory
issues 43/53 or their worktrees/queues.
