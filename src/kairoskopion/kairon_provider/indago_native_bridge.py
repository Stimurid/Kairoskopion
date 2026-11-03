"""Fail-closed native Indago preflight, delegated to existing indago-port.

No substitute hunting, no weakening of OpenClaw isolation policy, no owner
approval or journal submission. This adapter does not start a hunt unless the
native port itself admits the selected task and agent.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

from .publication_runner import EvidenceBlocked, atomic_write, sha256

SCHEMA="trimurti-indago-native-preflight-v1"

def preflight(*, port_root:Path, task_id:str, output_root:Path,
              runner=None, timeout_seconds:int=150) -> dict:
    if not task_id.startswith("TRIMURTI_") or not task_id.replace("_","").isalnum():
        raise EvidenceBlocked("explicit_trimurti_task_required")
    port_root=port_root.resolve(strict=True)
    if not (port_root/"indago_port"/"cli.py").is_file():
        raise EvidenceBlocked("native_indago_port_not_verified")
    cmd=[sys.executable,"-m","indago_port","plan","--task",task_id]
    execute=runner or subprocess.run
    try:
        result=execute(cmd,cwd=port_root,capture_output=True,text=True,
                       encoding="utf-8",errors="replace",timeout=timeout_seconds,
                       check=False)
    except subprocess.TimeoutExpired as e:
        raise EvidenceBlocked("native_indago_plan_timeout") from e
    try:
        data=json.loads(result.stdout)
    except (ValueError,TypeError) as e:
        raise EvidenceBlocked("native_indago_plan_unreadable") from e
    if not isinstance(data,dict) or data.get("status") not in {"PASS","PARTIAL","BLOCKED","DENIED"}:
        raise EvidenceBlocked("invalid_native_indago_status")
    selection=data.get("selection") or {}
    chosen=selection.get("chosen") or {}
    oc=data.get("openclaw") or {}
    auth=data.get("authorities") or {}
    required=("tasks_and_trails","living_current","source_ledger","candidate_queue","hunt_ledger")
    source_authority_ok=all(
       isinstance(auth.get(k),dict) and auth[k].get("source")=="LIVE" and
       auth[k].get("currentness")=="LIVE_VERIFIED" and len(auth[k].get("sha256") or "")==64
       for k in required
    )
    eligible=chosen.get("id")==task_id and (selection.get("eligibility") or {}).get("eligible") is True
    isolated=oc.get("isolated") is True and oc.get("block") is None and not oc.get("violations")
    admitted=result.returncode==0 and data["status"]=="PASS" and source_authority_ok and eligible and isolated
    receipt={
      "schema":SCHEMA,"task_id":task_id,
      "native_package":"indago_port","native_plan_exit":result.returncode,
      "native_plan_status":data["status"],
      "native_authorities_live_verified":source_authority_ok,
      "native_task_eligible":eligible,"native_agent_isolated":isolated,
      "native_agent_block":oc.get("block"),
      "native_agent_violations":oc.get("violations") or [],
      "native_plan_stdout_sha256":sha256(result.stdout.encode("utf-8")),
      "native_plan_stderr_sha256":sha256(result.stderr.encode("utf-8")),
      "result":"ADMITTED_FOR_SEPARATE_NATIVE_HUNT" if admitted else "BLOCKED_NATIVE_HUNT",
      "author_gate":"HOLD","article_seed_accepted":False,"manuscript_go":False,
      "send":False,"world_mutation":False,"new_w12_routes":0,
      "hunt_invoked":False,
    }
    output_root.mkdir(parents=True,exist_ok=True)
    serialized=(json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")
    target=output_root/"indago-native-preflight.json"
    if target.exists() and target.read_bytes()!=serialized:
        raise EvidenceBlocked("native_indago_preflight_receipt_conflict")
    if not target.exists():
        atomic_write(target,serialized)
    return receipt

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--port-root",required=True,type=Path)
    ap.add_argument("--task-id",required=True)
    ap.add_argument("--output-root",required=True,type=Path)
    args=ap.parse_args()
    try:
        out=preflight(port_root=args.port_root,task_id=args.task_id,output_root=args.output_root)
    except (EvidenceBlocked,OSError,ValueError) as e:
        print(json.dumps({"result":"BLOCKED_NATIVE_HUNT","reason":str(e),"send":False}))
        return 2
    print(json.dumps(out,ensure_ascii=False))
    return 0 if out["result"]=="ADMITTED_FOR_SEPARATE_NATIVE_HUNT" else 2

if __name__=="__main__":
    raise SystemExit(main())
