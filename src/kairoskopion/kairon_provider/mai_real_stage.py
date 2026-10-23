"""Run source-evidence stage of existing Trimurti scheduler over W12 REAL source bytes.

Processes all eligible route records with bounded batch size. Source verification
proves recorded bytes, not scholarly novelty, official CFP fit or manuscript QA.
No external email/portal actions, and no artificial phase completion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .w12_importer import SOURCE_KIND_REAL, load_w12
from .trimurti_scheduler import TrimurtiPlanStore, TrimurtiBatchSpec, build_trimurti_plan
from .stage_operation import SourceRoot, run_batch_first_source_evidence

def save_json(path: Path, body: dict[str,Any]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+".tmp")
    temp.write_text(json.dumps(body,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    temp.replace(path)

def execute(source: Path, root: Path, batch_id: str, limit: int = 10) -> dict[str,Any]:
    if not 1 <= limit <= 53:
        raise ValueError("limit must be from 1 to 53")
    records, source_receipt=load_w12(source,source_kind=SOURCE_KIND_REAL)
    if not records or source_receipt.source_kind != SOURCE_KIND_REAL:
        raise ValueError("real W12 source bytes unavailable")
    actual=SourceRoot.from_path(source)
    if not actual.is_real or actual.full_sha256!=source_receipt.source_full_sha256:
        raise ValueError("W12 source bytes drifted from importer receipt")
    store=TrimurtiPlanStore(root)
    plan=store.get(batch_id)
    if plan is None:
        plan=build_trimurti_plan(
            batch_id=batch_id,w12_records=records,
            spec=TrimurtiBatchSpec(batch_id=batch_id,concurrency_limit=limit),
        )
        store.put(plan)
    existing={r.route_id:r for r in plan.routes}
    current={r.route_id:r for r in records}
    if any(route.source_full_sha256 != actual.full_sha256 for route in plan.routes):
        raise ValueError("W12 source hash changed; use a new batch id")
    if existing.keys()!=current.keys():
        raise ValueError("W12 route identity drift; use new batch_id for new source")
    new=run_batch_first_source_evidence(
        plan,records_by_route_id=current,
        source_root=actual,limit=limit,
    )
    store.put(plan)
    check=store.get(batch_id)
    if check is None:
        raise RuntimeError("plan readback unavailable")
    completed=[
        r.route_id for r in check.routes
        if r.phase_checkpoints["source_evidence"].status=="completed"
    ]
    held=[
        r.route_id for r in check.routes
        if r.phase_checkpoints["source_evidence"].status=="hold"
    ]
    receipt={
        "schema":"MAI_REAL_W12_SOURCE_STAGE_v1",
        "batch_id":batch_id,
        "source_path":str(source),
        "source_sha256":actual.full_sha256,
        "total_routes":len(check.routes),
        "source_evidence_completed_count":len(completed),
        "source_evidence_hold_count":len(held),
        "still_await_source_count":len(check.routes)-len(completed)-len(held),
        "newly_attempted":new["requested"],
        "newly_completed":new["by_status"].get("completed",0),
        "newly_held":new["by_status"].get("hold",0),
        "source_stage_evidence":new["results"],
        "downstream_scholarly_challenge_executed":False,
        "ready_for_author_rework":0,
        "outbound_send_count":0,
        "checkpoint_readback_verified":True,
    }
    save_json(root/"MAI-W12_source_stage_latest.json",receipt)
    return receipt

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--storage-root",required=True,type=Path)
    p.add_argument("--batch-id",default="MAI-W12-SOURCE-20261020")
    p.add_argument("--limit",type=int,default=10)
    a=p.parse_args()
    print(json.dumps(execute(a.source,a.storage_root,a.batch_id,a.limit),ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
