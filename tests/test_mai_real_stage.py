"""MAI authenticated-byte stage driver: breadth-first & resumable, without send."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pytest
from kairoskopion.kairon_provider.mai_real_stage import execute

def source(tmp_path:Path)->Path:
    p=tmp_path/"route-source.jsonl"
    rows=[
        {"record_id":"R001","seed_family":"A","meaning_version":"A-NORM","route_label":"Educational Philosophy and Theory","route_type":"targeted_target","route_kind":"regular","raw_kind":"metadata","exclusive_venue_class":"none","notes":[]},
        {"record_id":"R002","seed_family":"B","meaning_version":"B-VALIDITY","route_label":"JRTE","route_type":"targeted_target","route_kind":"regular","raw_kind":"metadata","exclusive_venue_class":"none","notes":[]},
    ]
    p.write_text("".join(json.dumps(x)+"\n" for x in rows),encoding="utf-8",newline="\n")
    return p

def test_real_stage_incremental_and_cold_replay(tmp_path):
    p=source(tmp_path);root=tmp_path/"root"
    one=execute(p,root,"MAI-W12-TEST",limit=1)
    assert one["total_routes"]==2
    assert one["newly_completed"]==1
    assert one["source_evidence_completed_count"]==1
    assert one["outbound_send_count"]==0
    two=execute(p,root,"MAI-W12-TEST",limit=2)
    assert two["newly_completed"]==1
    assert two["source_evidence_completed_count"]==2
    again=execute(p,root,"MAI-W12-TEST",limit=2)
    assert again["newly_attempted"]==0
    assert again["source_evidence_completed_count"]==2
    assert again["checkpoint_readback_verified"]
    assert again["ready_for_author_rework"]==0

def test_source_drift_rejected_before_existing_state_mutation(tmp_path):
    p=source(tmp_path);root=tmp_path/"root"
    execute(p,root,"MAI-W12-TAMPER",limit=1)
    prior=(root/"MAI-W12_source_stage_latest.json").read_bytes()
    p.write_text(p.read_text(encoding="utf-8")+" \n",encoding="utf-8")
    with pytest.raises(ValueError,match="source hash changed"):
        execute(p,root,"MAI-W12-TAMPER",limit=2)
    assert (root/"MAI-W12_source_stage_latest.json").read_bytes()==prior

def test_bad_limit_and_missing_source_fail(tmp_path):
    p=source(tmp_path)
    with pytest.raises(ValueError,match="limit"):
        execute(p,tmp_path/"store","b",limit=54)
    with pytest.raises(ValueError,match="real W12 source bytes unavailable"):
        execute(tmp_path/"missing",tmp_path/"store","c",limit=10)
