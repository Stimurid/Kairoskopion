"""Local filesystem vault backend for development."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .vault_backend import VaultBackend, VaultObjectKind, VaultObjectRef, compute_content_hash


class LocalFsVault(VaultBackend):
    """Vault backed by a local directory. Used in development and tests."""

    def __init__(self, root: Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    def _resolve(self, vault_path: str) -> Path:
        return self._root / vault_path

    def write_bytes(
        self,
        vault_path: str,
        content: bytes,
        kind: str,
        metadata: dict[str, Any] | None = None,
    ) -> VaultObjectRef:
        target = self._resolve(vault_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

        content_hash = compute_content_hash(content)

        meta = dict(metadata or {})
        meta_path = target.with_suffix(target.suffix + ".meta.json")
        meta["content_hash"] = content_hash
        meta["kind"] = kind
        meta["size_bytes"] = len(content)
        meta_path.write_text(
            json.dumps(meta, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

        return VaultObjectRef(
            vault_path=vault_path,
            content_hash=content_hash,
            content_type=self._guess_content_type(vault_path),
            size_bytes=len(content),
            kind=kind,
            metadata=meta,
        )

    def read_bytes(self, vault_path: str) -> bytes:
        target = self._resolve(vault_path)
        if not target.exists():
            raise FileNotFoundError(f"Vault object not found: {vault_path}")
        return target.read_bytes()

    def exists(self, vault_path: str) -> bool:
        return self._resolve(vault_path).exists()

    def list_by_prefix(self, prefix: str) -> list[str]:
        base = self._resolve(prefix)
        if not base.exists():
            # Try as path prefix rather than directory
            parent = base.parent
            if not parent.exists():
                return []
            name_prefix = base.name
            results = []
            for p in parent.rglob("*"):
                if p.is_file() and not p.name.endswith(".meta.json"):
                    rel = str(p.relative_to(self._root)).replace("\\", "/")
                    if rel.startswith(prefix):
                        results.append(rel)
            return sorted(results)

        results = []
        for p in base.rglob("*"):
            if p.is_file() and not p.name.endswith(".meta.json"):
                results.append(str(p.relative_to(self._root)).replace("\\", "/"))
        return sorted(results)

    def delete(self, vault_path: str) -> bool:
        target = self._resolve(vault_path)
        if not target.exists():
            return False
        target.unlink()
        meta = target.with_suffix(target.suffix + ".meta.json")
        if meta.exists():
            meta.unlink()
        return True

    def get_metadata(self, vault_path: str) -> dict[str, Any]:
        target = self._resolve(vault_path)
        meta_path = target.with_suffix(target.suffix + ".meta.json")
        if meta_path.exists():
            return json.loads(meta_path.read_text(encoding="utf-8"))
        return {}

    @staticmethod
    def _guess_content_type(vault_path: str) -> str:
        if vault_path.endswith(".html"):
            return "text/html"
        if vault_path.endswith(".md"):
            return "text/markdown"
        if vault_path.endswith(".json") or vault_path.endswith(".jsonl"):
            return "application/json"
        if vault_path.endswith(".pdf"):
            return "application/pdf"
        if vault_path.endswith(".txt"):
            return "text/plain"
        return "application/octet-stream"
