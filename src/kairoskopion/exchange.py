"""Export/import storage bundles for local handoff and backup.

Bundles are zip archives containing registries, vault cards, manifest,
and metadata. Designed for local exchange — not a sync protocol.
"""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__
from .persistence import (
    ensure_storage_root,
    ensure_registry_root,
    list_registries,
)
from .vault import write_vault_indexes


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def export_storage_bundle(
    storage_root: Path | str,
    output_path: Path | str,
) -> Path:
    """Export storage root as a zip bundle.

    Includes: registries/*.jsonl, vault/**/*.md, vault/manifest.json,
    and metadata.json with version/counts.
    """
    storage = Path(storage_root)
    output = Path(output_path)

    # Regenerate indexes/manifest before export
    write_vault_indexes(storage)

    reg_dir = storage / "registries"
    vault_dir = storage / "vault"

    registry_names = list_registries(storage)
    registry_counts: dict[str, int] = {}
    for name in registry_names:
        jsonl = reg_dir / f"{name}.jsonl"
        if jsonl.exists():
            registry_counts[name] = sum(1 for _ in jsonl.read_text(encoding="utf-8").strip().splitlines())

    metadata = {
        "kairoskopion_version": __version__,
        "created_at": _now_iso(),
        "source_storage_root": str(storage.resolve()),
        "registry_counts": registry_counts,
        "total_registries": len(registry_names),
    }

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("metadata.json", json.dumps(metadata, indent=2, ensure_ascii=False))

        if reg_dir.exists():
            for jsonl_file in sorted(reg_dir.glob("*.jsonl")):
                arcname = f"registries/{jsonl_file.name}"
                zf.write(jsonl_file, arcname)

        if vault_dir.exists():
            for vault_file in sorted(vault_dir.rglob("*")):
                if vault_file.is_file():
                    arcname = f"vault/{vault_file.relative_to(vault_dir)}"
                    zf.write(vault_file, arcname)

    return output


def validate_bundle(bundle_path: Path | str) -> dict[str, Any]:
    """Validate a storage bundle. Returns validation result dict."""
    bundle = Path(bundle_path)
    result: dict[str, Any] = {
        "path": str(bundle),
        "valid": False,
        "errors": [],
        "warnings": [],
        "metadata": None,
    }

    if not bundle.exists():
        result["errors"].append(f"Bundle not found: {bundle}")
        return result

    if not zipfile.is_zipfile(bundle):
        result["errors"].append("Not a valid zip file")
        return result

    with zipfile.ZipFile(bundle, "r") as zf:
        names = zf.namelist()

        if "metadata.json" not in names:
            result["errors"].append("Missing metadata.json")
            return result

        try:
            meta = json.loads(zf.read("metadata.json"))
            result["metadata"] = meta
        except (json.JSONDecodeError, KeyError) as e:
            result["errors"].append(f"Invalid metadata.json: {e}")
            return result

        reg_files = [n for n in names if n.startswith("registries/") and n.endswith(".jsonl")]
        vault_files = [n for n in names if n.startswith("vault/")]

        if not reg_files:
            result["warnings"].append("No registry files in bundle")

        result["registry_count"] = len(reg_files)
        result["vault_file_count"] = len(vault_files)
        result["valid"] = True

    return result


def import_storage_bundle(
    bundle_path: Path | str,
    target_storage_root: Path | str,
    *,
    mode: str = "append",
) -> dict[str, Any]:
    """Import a storage bundle into target storage root.

    mode='append': append JSONL records to existing registries (default).
    mode='replace': overwrite registries and vault with bundle contents.
    """
    bundle = Path(bundle_path)
    target = Path(target_storage_root)

    validation = validate_bundle(bundle)
    if not validation["valid"]:
        return {
            "success": False,
            "errors": validation["errors"],
        }

    if mode not in ("append", "replace"):
        return {
            "success": False,
            "errors": [f"Invalid mode: {mode}. Use 'append' or 'replace'."],
        }

    ensure_storage_root(target)
    reg_root = ensure_registry_root(target)
    vault_root = target / "vault"
    vault_root.mkdir(parents=True, exist_ok=True)

    imported_registries = 0
    imported_records = 0
    imported_vault_files = 0

    with zipfile.ZipFile(bundle, "r") as zf:
        for name in zf.namelist():
            if name.startswith("registries/") and name.endswith(".jsonl"):
                reg_name = Path(name).stem
                content = zf.read(name).decode("utf-8").strip()
                if not content:
                    continue

                target_file = reg_root / f"{reg_name}.jsonl"

                if mode == "replace":
                    target_file.write_text(content + "\n", encoding="utf-8")
                else:
                    with open(target_file, "a", encoding="utf-8") as f:
                        f.write(content + "\n")

                imported_registries += 1
                imported_records += len(content.splitlines())

            elif name.startswith("vault/") and not name.endswith("/"):
                rel = name[len("vault/"):]
                target_file = (vault_root / rel).resolve()
                if not target_file.is_relative_to(vault_root.resolve()):
                    return {
                        "success": False,
                        "errors": [
                            f"Unsafe path in bundle (escapes vault root): {name}"
                        ],
                    }
                target_file.parent.mkdir(parents=True, exist_ok=True)
                target_file.write_bytes(zf.read(name))
                imported_vault_files += 1

    return {
        "success": True,
        "mode": mode,
        "imported_registries": imported_registries,
        "imported_records": imported_records,
        "imported_vault_files": imported_vault_files,
        "target_storage_root": str(target),
    }
