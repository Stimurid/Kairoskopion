import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

from kairoskopion.kairon_provider.indago_native_bridge import preflight

TASK="TRIMURTI_M108_C04_20261103"

def fake(tmp_path, isolated, exitcode=0):
    p=tmp_path/"indago"
    (p/"indago_port").mkdir(parents=True)
    (p/"indago_port"/"cli.py").write_text("pass")
    h="a"*64
    obj={"status":"PASS" if exitcode==0 else "BLOCKED",
         "selection":{"chosen":{"id":TASK},"eligibility":{"eligible":True}},
         "openclaw":{"isolated":isolated,
            "block":None if isolated else "AGENT_NOT_ISOLATED",
            "violations":[] if isolated else ["TOOLS_NOT_DENIED"]},
         "authorities":{x:{"source":"LIVE","currentness":"LIVE_VERIFIED","sha256":h}
             for x in ("tasks_and_trails","living_current","source_ledger","candidate_queue","hunt_ledger")}}
    def runner(cmd,**kwargs):
        assert cmd[1:4]==["-m","indago_port","plan"]
        assert kwargs["check"] is False
        return SimpleNamespace(returncode=exitcode,stdout=json.dumps(obj),stderr="")
    return p,runner

def test_admission_only_for_native_verified(tmp_path):
    p,runner=fake(tmp_path,True)
    x=preflight(port_root=p,task_id=TASK,output_root=tmp_path/"out",runner=runner)
    assert x["result"]=="ADMITTED_FOR_SEPARATE_NATIVE_HUNT"
    assert x["hunt_invoked"] is False and x["send"] is False
    assert preflight(port_root=p,task_id=TASK,output_root=tmp_path/"out",runner=runner)==x

def test_isolation_failure_fail_closed(tmp_path):
    p,runner=fake(tmp_path,False,20)
    x=preflight(port_root=p,task_id=TASK,output_root=tmp_path/"out",runner=runner)
    assert x["result"]=="BLOCKED_NATIVE_HUNT"
    assert x["native_agent_block"]=="AGENT_NOT_ISOLATED"
    assert x["author_gate"]=="HOLD"
