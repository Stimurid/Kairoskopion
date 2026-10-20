"""Stage an exact source/publisher/W3-bound W12 research-route on owner HOLD."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from kairoskopion.services.trm073_w12_route_stage import stage_w12_research_route


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--packet",type=Path,required=True)
    p.add_argument("--storage-root",type=Path,required=True)
    args=p.parse_args()
    try:out=stage_w12_research_route(args.packet,args.storage_root)
    except (ValueError,KeyError,OSError,UnicodeError) as e:
        print("W12_ROUTE_HELD_BLOCKED: "+str(e),file=sys.stderr)
        return 2
    print(json.dumps(out,sort_keys=True,ensure_ascii=False,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
