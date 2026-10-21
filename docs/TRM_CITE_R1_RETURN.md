# TRM-CITE-001 R1 local return seam

Status: **code candidate; execution and scientific verification blocked in this delegated workspace**.

The Z0 audit and queue remain immutable. `citation_r1` reads both, checks each
work order against the original `CitationRepairCase` and intake, and writes one
minimal request per work order. A source reader with separately established
access may place a `trm-cite-r1-return-v1` JSON receipt. The consumer verifies
the correlation, source hash, anchor, queue version, access declaration and
read-depth fields, then persists the return and a case-state proposal. A
second process can read these files and replay the same operation; a conflicting
return is refused. The original manuscript and audit are never changed.

Run from the repository with `PYTHONPATH=src`:

```text
python -m kairoskopion.services.citation_r1 prepare --audit AUDIT.json --queue QUEUE.jsonl --out REQUEST_DIR
python -m kairoskopion.services.citation_r1 blocked-canary --audit AUDIT.json --queue QUEUE.jsonl --request REQUEST.json --out RETURN_DIR
python -m kairoskopion.services.citation_r1 consume --audit AUDIT.json --queue QUEUE.jsonl --request REQUEST.json --return-file RETURN.json --out STATE_DIR
```

`blocked-canary` is a negative access receipt, not a simulated source read.
The request contains only public source hints and opaque IDs. It grants no
search permission. The source reader must independently establish its provider
permission and return source kind, read depth, retrieval time, access/license,
Work, Edition, Witness and locator. An anchored passage also needs Passage ID
and source byte SHA-256. Search hits and abstracts cannot become passage
evidence. The reader should preserve negative evidence and errors and keep
source-author claims separate from article-author claims. The consumer makes
only a V1 proposal for observed material. V2 is N/A only when the return
explicitly identifies a paraphrase; V3-V5
remain NOT_CHECKED. Every case remains `NOT_PUBLICATION_READY` and has no patch.

The supplied five-case protocols and 13-order JSONL reside outside this
assigned workspace and were explicitly designated pointer-only. Their hashes,
IDs, private source records and manual verdicts were therefore **not** read or
compared here. The R1 Google Doc and issue/PR links were also pointer-only.
No source acquisition, Indago call, manuscript read or historical claim check
occurred in this continuation. A future authorized run must first compare the
three owner-supplied SHA-256 values, then execute this consumer on the actual
queue and compare each machine state with the manual protocol. Any Drive canon
change needs owner acceptance and a fresh source readback.

The target environment exposed neither a runnable Python in PATH nor the
machine-map Python 3.14 path. The found `C:\AI\llm\.venv\Scripts\python.exe`
failed to spawn its child with `permission denied (os error 5)`. Tests were
written but could not run in this sandbox; no test pass is claimed.
