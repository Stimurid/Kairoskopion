"""Stage an exact source/publisher/W3-bound W12 research-route on owner HOLD."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from kairoskopion.services.trm073_w12_route_stage import (
    stage_w12_research_route, stage_w12_candidate_wave,
)


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--packet",type=Path,action="append",default=[])
    p.add_argument("--wave-case-id",type=str,
                   help="Run all existing W3 candidate routes; packets must be W12 source-verified")
    p.add_argument("--storage-root",type=Path,required=True)
    args=p.parse_args()
    if not args.wave_case_id and len(args.packet) != 1:
        p.error("single mode requires exactly one --packet")
    try:
        if args.wave_case_id:
            out = stage_w12_candidate_wave(case_id=args.wave_case_id,
                  storage_root=args.storage_root, packet_paths=args.packet)
        else:
            out = stage_w12_research_route(args.packet[0], args.storage_root)
    except (ValueError,KeyError,OSError,UnicodeError) as e:
        print("W12_ROUTE_HELD_BLOCKED: "+str(e),file=sys.stderr)
        return 2
    print(json.dumps(out,sort_keys=True,ensure_ascii=False,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
