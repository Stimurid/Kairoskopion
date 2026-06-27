# P9 Review Packet / Dossier Export

**Date:** 2026-06-27
**Branch:** `feature/round3-p7-4-to-p9-acquisition-verification`

## Purpose

After harvest → acquisition → verification, the user receives a provenance
dossier — a complete, verifiable review packet of all registry state.

## Contents

| section | description |
|---------|-------------|
| Venues | All venue registry records with evidence refs |
| Venue sections | Article types / sections per venue |
| Venue metrics | SJR, CiteScore, h-index, RSCI IF, Scopus quartiles |
| Classifications | VAK status, Scopus subject areas |
| Disciplines | From seed files, with provenance |
| Source packets | All SourcePackets created during harvest/acquisition |
| Acquisition tasks | Open, blocked, completed tasks |
| Verification decisions | Per-record verdict with audit trail |
| Gaps | Open gaps requiring additional evidence |
| Blocked items | Tasks blocked by paid API or missing source |

## Export Formats

### Markdown report (`review_packet.md`)
- Human-readable summary with tables
- Venue list, metrics, source packets (top 10)
- Open gaps and blocked items
- Next steps for manual resolution

### JSONL export (`review_packet.jsonl`)
- One JSON record per line
- Header line with packet ID and verification summary
- Each record tagged with `record_type`
- Machine-parseable for downstream tools

### TSV review table (`review_packet.tsv`)
- Spreadsheet-ready format
- Columns: record_type, record_id, name_or_label, status,
  verification_verdict, evidence_count, evidence_kinds, needs_action
- Filterable by needs_action=yes for manual review queue

## Implementation

`src/kairoskopion/services/review_packet_exporter.py`

Functions:
- `build_review_packet(hub, gaps)` → `ReviewPacket`
- `export_markdown(packet)` → string
- `export_jsonl(packet)` → string
- `export_tsv(packet)` → string
- `write_review_packet(packet, output_dir)` → dict of paths

## No Fabrication

The review packet exports exactly what is in the registry. No records are
added, upgraded, or fabricated during export. If a record is provisional,
it appears as provisional. If evidence is missing, it shows as a gap.
