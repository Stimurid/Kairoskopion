# TRIMURTI R1 negative scientific controls — executed 2026-10-24

This is a verified real-data operational probe, NOT a test of successful article production.

AORUS private source artifact:
`C:\projects\trimurti\_ops\TRM_R1_NEGATIVE_CONTROL_20261024\negative_science_controls.json`
Builder:
`build_negative_controls.py`

The builder loaded original Hub author and reviewer receipts and reviewer stdout for **two different scientific cases**, asserted distinct agent/reviewer identities, verified both executed successfully, checked that each reviewer was actually based on the author's final Git head, and that neither independent scientific review accepted the article.

Machine result: `NEGATIVE_CONTROL_PASS 2 reviewed 2 science_accepted 0`.

| Case | Author | Independent reviewer | Runtime chain | Scientific result |
| --- | --- | --- | --- | --- |
| S14 | jx-422ca589a73a | jx-3f002e632f62 | completed | FAIL / COMMENTARY_DONOR |
| S11 | jx-b2a29809af47 | jx-176c319f1caf | completed | FAIL / COMMENTARY_DONOR |

This is *not* a statistical evaluation, a general autonomous factory pass, a journal qualification, or a confirmation that all primary sources were read fully. The S14 failure concerned author/source attribution and unexplained philosophical inference. The S11 failure concerned missing case, unclosed rivals and nonreproducible source claims.

The desired reusable invariant:
`JOB_SUCCEEDED != SCIENTIFIC_PASSED != VENUE_QUALIFIED != AUTHOR_APPROVED != SUBMITTED`.
A source missing as raw, reproducible bytes can only be UNKNOWN/NO_EVIDENCE for its claim; webpage metadata is not full text. In future Factory runtime, negative review receipts should automatically freeze that article-target route and retain the complete revision history, not allow an author task's success status to turn green.

S14 original verdict: https://docs.google.com/document/d/10irKuexgee_jhdQjSMBZBYeL09i9kQBzYp8qcNO5UQA/edit
S11 original verdict: https://docs.google.com/document/d/11Lu70lJ54EI2BogPrAAt98PoYQHvzzVIDQgs7Xq2NtE/edit
S11 corrected evidence copy: https://docs.google.com/document/d/1bsIepjVK_lI7y5HC2xtRfbsPjVo3mGueYSwU9t6Yjdc/edit
R1 governing plan: https://docs.google.com/document/d/1e62rTE51R3iLZthYyjdYyAb7foh6VLfrVI7z7HaCYU0/edit
