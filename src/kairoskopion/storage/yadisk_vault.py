"""Yandex Disk vault backend for production storage.

Uses Yandex Disk REST API v1 (https://yandex.ru/dev/disk-api/doc/dg/concepts/about.html).
No external SDK required — pure httpx/urllib.

Env vars:
  KAIRON_VAULT_YADISK_TOKEN  — OAuth token (starts with y0__)
  KAIRON_VAULT_YADISK_ROOT   — root folder on disk (default: app:/kairoskopion/vault)
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .vault_backend import VaultBackend, VaultObjectRef, compute_content_hash

logger = logging.getLogger(__name__)

_API = "https://cloud-api.yandex.net/v1/disk"
_DEFAULT_ROOT = "app:/kairoskopion/vault"


class YandexDiskVault(VaultBackend):
    """Vault backed by Yandex Disk REST API."""

    def __init__(
        self,
        token: str | None = None,
        root: str | None = None,
    ) -> None:
        self._token = token or os.environ.get("KAIRON_VAULT_YADISK_TOKEN", "")
        if not self._token:
            raise ValueError("Yandex Disk token not provided (KAIRON_VAULT_YADISK_TOKEN)")
        self._root = root or os.environ.get("KAIRON_VAULT_YADISK_ROOT", _DEFAULT_ROOT)
        self._root_ensured = False

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"OAuth {self._token}"}

    def _disk_path(self, vault_path: str) -> str:
        return f"{self._root}/{vault_path}"

    def _api_get(self, url: str) -> Any:
        req = urllib.request.Request(url, headers=self._headers())
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _api_request(self, url: str, method: str = "GET", data: bytes | None = None) -> int:
        req = urllib.request.Request(url, method=method, headers=self._headers(), data=data)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status
        except urllib.error.HTTPError as e:
            return e.code

    def _ensure_folder(self, path: str):
        parts = path.split("/")
        for i in range(1, len(parts) + 1):
            sub = "/".join(parts[:i])
            encoded = urllib.parse.quote(sub, safe=":/")
            url = f"{_API}/resources?path={encoded}"
            status = self._api_request(url, method="PUT")
            if status not in (201, 409):
                logger.debug("mkdir %s → %d", sub, status)

    def _lazy_ensure_root(self):
        if not self._root_ensured:
            try:
                self._ensure_folder(self._root)
                self._root_ensured = True
            except Exception as exc:
                logger.warning("Could not ensure vault root folder: %s", exc)

    def write_bytes(
        self,
        vault_path: str,
        content: bytes,
        kind: str,
        metadata: dict[str, Any] | None = None,
    ) -> VaultObjectRef:
        self._lazy_ensure_root()
        disk_path = self._disk_path(vault_path)
        content_hash = compute_content_hash(content)

        # Ensure parent folder
        parent = "/".join(disk_path.split("/")[:-1])
        if parent:
            self._ensure_folder(parent)

        # Get upload URL
        encoded = urllib.parse.quote(disk_path, safe=":/")
        info = self._api_get(f"{_API}/resources/upload?path={encoded}&overwrite=true")
        upload_url = info["href"]

        # Upload content
        req = urllib.request.Request(upload_url, method="PUT", data=content)
        req.add_header("Content-Type", "application/octet-stream")
        with urllib.request.urlopen(req, timeout=60) as resp:
            if resp.status not in (200, 201, 202):
                raise IOError(f"Upload failed: {resp.status}")

        # Upload metadata sidecar
        meta = dict(metadata or {})
        meta["content_hash"] = content_hash
        meta["kind"] = kind
        meta["size_bytes"] = len(content)
        meta_bytes = json.dumps(meta, indent=2, ensure_ascii=False, default=str).encode("utf-8")
        meta_path = f"{disk_path}.meta.json"
        encoded_meta = urllib.parse.quote(meta_path, safe=":/")
        try:
            meta_info = self._api_get(f"{_API}/resources/upload?path={encoded_meta}&overwrite=true")
            req2 = urllib.request.Request(meta_info["href"], method="PUT", data=meta_bytes)
            req2.add_header("Content-Type", "application/json")
            urllib.request.urlopen(req2, timeout=30)
        except Exception as exc:
            logger.warning("Failed to upload metadata for %s: %s", vault_path, exc)

        logger.info("Uploaded %s (%d bytes, hash=%s)", vault_path, len(content), content_hash)

        return VaultObjectRef(
            vault_path=vault_path,
            content_hash=content_hash,
            content_type=self._guess_content_type(vault_path),
            size_bytes=len(content),
            kind=kind,
            metadata=meta,
        )

    def read_bytes(self, vault_path: str) -> bytes:
        disk_path = self._disk_path(vault_path)
        encoded = urllib.parse.quote(disk_path, safe=":/")
        info = self._api_get(f"{_API}/resources/download?path={encoded}")
        download_url = info["href"]
        req = urllib.request.Request(download_url)
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()

    def exists(self, vault_path: str) -> bool:
        disk_path = self._disk_path(vault_path)
        encoded = urllib.parse.quote(disk_path, safe=":/")
        try:
            self._api_get(f"{_API}/resources?path={encoded}")
            return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
            raise

    def list_by_prefix(self, prefix: str) -> list[str]:
        disk_path = self._disk_path(prefix)
        encoded = urllib.parse.quote(disk_path, safe=":/")
        try:
            info = self._api_get(f"{_API}/resources?path={encoded}&limit=1000")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return []
            raise

        results: list[str] = []
        embedded = info.get("_embedded", {})
        for item in embedded.get("items", []):
            name = item.get("name", "")
            if name.endswith(".meta.json"):
                continue
            if item.get("type") == "file":
                results.append(f"{prefix}/{name}" if prefix else name)
            elif item.get("type") == "dir":
                sub = self.list_by_prefix(f"{prefix}/{name}" if prefix else name)
                results.extend(sub)

        return sorted(results)

    def delete(self, vault_path: str) -> bool:
        disk_path = self._disk_path(vault_path)
        encoded = urllib.parse.quote(disk_path, safe=":/")
        status = self._api_request(f"{_API}/resources?path={encoded}&permanently=false", method="DELETE")
        if status in (202, 204):
            # Also delete metadata
            meta_path = f"{disk_path}.meta.json"
            encoded_meta = urllib.parse.quote(meta_path, safe=":/")
            self._api_request(f"{_API}/resources?path={encoded_meta}&permanently=false", method="DELETE")
            return True
        return False

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


def get_vault() -> VaultBackend:
    """Factory: return YandexDiskVault if token is configured, else LocalFsVault."""
    token = os.environ.get("KAIRON_VAULT_YADISK_TOKEN")
    if token:
        return YandexDiskVault(token=token)

    from .local_fs_vault import LocalFsVault
    from pathlib import Path

    vault_dir = os.environ.get("KAIRON_VAULT_DIR", ".kairoskopion/vault")
    return LocalFsVault(Path(vault_dir))
