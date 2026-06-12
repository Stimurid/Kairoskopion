"""Vault backend abstraction (ADR-16).

Content-addressed storage for venue artifacts: HTML snapshots, PDFs,
venue cards, corpus samples, editorial board JSON, etc.

Index stays local (JSONL registries on VPS).
Content lives in an external vault (local FS for dev, Yandex Disk for prod).
"""

from __future__ import annotations

import dataclasses as dc
import hashlib
import json
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any


class VaultObjectKind(str, Enum):
    HTML_SNAPSHOT = "html_snapshot"
    PDF_ARTICLE = "pdf_article"
    ARTICLE_TEXT = "article_text"
    VENUE_CARD_MD = "venue_card_md"
    CORPUS_SAMPLE = "corpus_sample"
    EDITORIAL_BOARD_JSON = "editorial_board_json"
    ADAPTER_SNAPSHOT_JSON = "adapter_snapshot_json"
    EVIDENCE_BUNDLE = "evidence_bundle"


@dc.dataclass
class VaultObjectRef:
    """Reference to content stored in the vault."""

    vault_path: str
    content_hash: str
    content_type: str
    size_bytes: int | None = None
    kind: str = VaultObjectKind.ARTICLE_TEXT.value
    metadata: dict[str, Any] = dc.field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "vault_path": self.vault_path,
            "content_hash": self.content_hash,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "kind": self.kind,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VaultObjectRef:
        field_names = {f.name for f in dc.fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in field_names})


def compute_content_hash(content: bytes) -> str:
    """SHA-256 truncated to 16 hex chars for vault addressing."""
    return hashlib.sha256(content).hexdigest()[:16]


class VaultBackend(ABC):
    """Abstract vault storage interface."""

    @abstractmethod
    def write_bytes(self, vault_path: str, content: bytes, kind: str, metadata: dict[str, Any] | None = None) -> VaultObjectRef:
        ...

    @abstractmethod
    def read_bytes(self, vault_path: str) -> bytes:
        ...

    @abstractmethod
    def exists(self, vault_path: str) -> bool:
        ...

    @abstractmethod
    def list_by_prefix(self, prefix: str) -> list[str]:
        ...

    @abstractmethod
    def delete(self, vault_path: str) -> bool:
        ...

    def write_text(self, vault_path: str, text: str, kind: str, metadata: dict[str, Any] | None = None) -> VaultObjectRef:
        content = text.encode("utf-8")
        return self.write_bytes(vault_path, content, kind, metadata)

    def read_text(self, vault_path: str) -> str:
        return self.read_bytes(vault_path).decode("utf-8")

    def write_json(self, vault_path: str, data: Any, kind: str, metadata: dict[str, Any] | None = None) -> VaultObjectRef:
        text = json.dumps(data, indent=2, ensure_ascii=False, default=str)
        return self.write_text(vault_path, text, kind, metadata)

    def read_json(self, vault_path: str) -> Any:
        return json.loads(self.read_text(vault_path))
