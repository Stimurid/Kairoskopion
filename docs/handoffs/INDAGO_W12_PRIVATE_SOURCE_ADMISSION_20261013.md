# INDAGO MAI W12 — verified private research-stage admission (2026-10-13)

**Receipt class:** RAW_BYTES_VERIFIED / RESEARCH_STAGED / NOT_ARTIKL_ADMITTED.
**Scientific status:** research source and routing candidates, **not** qualified articles, formally accepted proposals, full-read VenueWorlds, author consent, or permission to submit.

## Verified, actual source
- Private original Drive workbook (21-sheet XLSX): https://docs.google.com/spreadsheets/d/1gniLiBZt6yAxq_FERLxvaMQxLstohms8/edit
- Source MIME: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- Byte size: `251033`
- Raw source SHA-256: `c47143b4d9f4f3186add6473246e45cde48d9f414e8a8d382cb04bf6b6f9f73f`
- ZIP/OOXML integrity: PASS (`ZipFile.testzip() == None`), 21 worksheet names; parsed with openpyxl.
- Linkage checks: zero missing/duplicate seed IDs, version IDs, venue IDs, route IDs, broken route-to-version/seed/venue links, or mismatches between 53 routes and their Russian abstracts, channels, requirements, journal cards and author fields. All 67 editorial actions reference an existing route.

## Verified workbook cardinalities, not claims about submission readiness

| Research record class | Verified count |
| --- | ---: |
| Initial scientific seed directions | 6 |
| Candidate venues (distinct names and corpus IDs) | 81 |
| Research/semantic versions (NOT independent accepted articles) | 27 |
| Source editorial routes | 53 |
| Russian abstract drafts | 53 |
| Editorial actions | 67 |
| Published article/CFP source records | 43 |
| Route-linked cards, channel rows, requirement rows and author-field rows | 53 each |

Of 43 recorded source examples, the workbook itself labels 31 **only abstract/list/fragments**, 8 **full reading not proven**, 4 **selected sections, not fulltext**. No 43 is promoted to independently certified FULL_TEXT; `FULL_READ_QUALIFIED=0`. All 53 staged routes have `POLICY_UNVERIFIED` until separately source-qualified for their exact editorial action. The 27 research versions are not 27 independent Article objects.

## Durable private artifact (NOT COMMITTED TO PUBLIC GITHUB)

- Private Drive container: https://drive.google.com/drive/folders/1hfysfxHrja2ksGkHFtrA9C5mUiO8UXyn
- Owner-only ZIP with SQLite + provenance JSON receipt + reproducible staging script: https://drive.google.com/file/d/1jL_9QxMbeXZnBWIEPm7kyv5J3e5U6IMU/view
- Archive size `202845` bytes; archive SHA-256 `9c7efd9396c3b95c9a6beb64058a84966d347b7775379a1aa211590ba61c377c`.
- SQLite SHA-256 `339ec939387e6bd4225614fbbb9b5307af7485df2033f2c1386c54576e10c9f3`.
- SQLite holds 728 source-row snapshots, 21 sheets, 6 seeds, 81 venue identities, 27 research variants, 53 provisional routes, 67 actions, 43 evidence claims, and 1 admission event. The original source remains in Drive.
- Double stage with identical source input preserved identical `row_digest` and admission event lists: **IDEMPOTENCE PASS**.
- Private folder/file metadata readback reports only owner access, `shared=false`.

Do not mirror this private ZIP, original XLSX, per-journal author profile, or raw source rows into this PUBLIC repository. All links are for authorized Google Drive access only. Public Git contains counts/checksums/contract, not confidential source contents.

## Execution and scientific acceptance boundaries

1. **SOURCE_BYTES**: VERIFIED (this supersedes PR #22/#25's earlier `BLOCKED_SOURCE_BYTES_UNAVAILABLE` claim).
2. **PRIVATE_RESEARCH_STAGE**: IMPORTED_VERIFIED, exact research rows and FK linkage.
3. **VENUE_ROUTE_POLICY**: UNQUALIFIED — policy and communication channel must be re-read on official source with exact stage/date; generic addresses and websites are not route acceptance.
4. **DEEP_VENUE_EVIDENCE**: PARTIAL; zero externally qualified FULL_TEXT exemplars. Requires 3–5 genuinely FULL_READ publications per priority target or a visible blocker.
5. **ARTICLE_IDENTITY**: not admitted by Artikl; 27 editorial versions must not be minted as 27 original articles.
6. **AUTHOR_DECISION**: not inferred; coauthor F and author profile fields require human validation.
7. **RUNTIME_IMPORT / UI HYDRATION**: still pending. The current public-code opportunity API is read-only and user-scoped; no actor has certified loading this private research SQLite into the runtime.
8. **SUBMISSION**: FORBIDDEN without a separate explicit author action.

The research staged data is ready for the *next* authorized importer/UI adapter operation; it is not an executable P06/P07 article package, an automatic journal submission, or a proven live editorial policy.
