# Review Packet Schema

## JSONL Record Types

Each line in `review_packet.jsonl` is a JSON object with a `record_type` field.

### `review_packet_header`
```json
{
  "record_type": "review_packet_header",
  "packet_id": "rpkt_...",
  "created_at": "2026-06-27T...",
  "summary": {
    "total": 79,
    "verdicts": {
      "promote_verified": 0,
      "promote_local_evidence_supported": 44,
      "keep_provisional": 35,
      "needs_manual_review": 0,
      "reject": 0,
      "blocked": 0
    }
  }
}
```

### `venue`
```json
{
  "record_type": "venue",
  "venue_id": "vrec_...",
  "canonical_name": "Вопросы философии",
  "issn": "0042-8744",
  "publisher": "ИФ РАН",
  "source_status": "provisional",
  "evidence_refs": [{"evidence_status": "corpus_grounded", ...}]
}
```

### `venue_metric`
```json
{
  "record_type": "venue_metric",
  "metric_id": "vmet_...",
  "venue_id": "vrec_...",
  "metric_system": "sjr",
  "metric_type": "quartile",
  "metric_value": "0.31",
  "evidence_status": "corpus_grounded"
}
```

### `discipline`
```json
{
  "record_type": "discipline",
  "discipline_id": "disc_...",
  "display_names": {"ru": "Философия", "en": "Philosophy"},
  "source_status": "provisional",
  "provenance": "llm_draft from ru_seed.jsonl"
}
```

### `source_packet`
```json
{
  "record_type": "source_packet",
  "packet_id": "spkt_...",
  "packet_type": "evidence_pack_harvest",
  "source_type": "local_file",
  "evidence_status": "corpus_grounded"
}
```

### `acquisition_task`
```json
{
  "record_type": "acquisition_task",
  "task_id": "acqtask_...",
  "task_type": "gap_resolution",
  "query": "Missing education venue universe",
  "status": "open"
}
```

### `verification_decision`
```json
{
  "record_type": "verification_decision",
  "record_id": "vrec_...",
  "record_type": "venue",
  "before_status": "provisional",
  "after_status": "provisional",
  "verdict": "promote_local_evidence_supported",
  "reason": "Record has 1 local evidence ref(s)",
  "evidence_refs_count": 1,
  "verifier_version": "0.1.0"
}
```

## TSV Columns

| column | type | description |
|--------|------|-------------|
| record_type | string | venue, venue_metric, discipline |
| record_id | string | Registry record ID |
| name_or_label | string | Human-readable label |
| status | string | source_status or evidence_status |
| verification_verdict | string | Gate verdict |
| evidence_count | int | Number of evidence refs |
| evidence_kinds | string | Comma-separated evidence statuses |
| needs_action | yes/no | Whether manual action required |
