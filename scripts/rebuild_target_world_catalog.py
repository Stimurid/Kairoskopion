"""Ingest one or more TargetWorld stores into the shared exchange catalog."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from kairoskopion.kairon_provider.target_world_catalog import TargetWorldCatalog

def iter_snapshots(root: Path):
    for path in sorted(root.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("snapshot_id") and data.get("target_id"):
            yield path, data

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog-root", required=True)
    ap.add_argument("--source", action="append", nargs=3, metavar=("DIR","STATUS","ORIGIN"), required=True)
    args = ap.parse_args()
    catalog = TargetWorldCatalog(args.catalog_root)
    count = 0
    for directory, status, origin in args.source:
        source_dir = Path(directory)
        for path, snapshot in iter_snapshots(source_dir):
            entry = catalog.ingest(
                snapshot,
                origin=origin,
                status=status,
                source_ref=str(path),
            )
            print(json.dumps({
                "package_id": entry["package_id"],
                "target_id": entry["target_id"],
                "status": entry["status"],
                "origins": entry["origins"],
            }, ensure_ascii=False))
            count += 1
    print(json.dumps({"ingested": count, "catalog_entries": len(catalog.list_entries())}))

if __name__ == "__main__":
    main()