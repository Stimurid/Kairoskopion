# Vault Backend Architecture

## Overview

Content-addressed storage for venue evidence artifacts. Each object is stored with a SHA-256[:16] content hash, enabling deduplication and integrity verification.

## Components

### VaultObjectKind (8 types)
- `venue_snapshot` — HTML captures of venue homepages
- `corpus_article` — individual article texts/metadata
- `corpus_sample` — aggregated corpus samples
- `adapter_response` — raw API responses from adapters
- `evidence_claim` — individual evidence claims
- `evidence_pack` — assembled evidence packs
- `analysis_result` — corpus/citation analysis outputs
- `user_annotation` — user-provided notes and outcomes

### VaultObjectRef
Content-addressed reference: `content_hash` + `kind` + `metadata`.

### VaultBackend ABC
```python
class VaultBackend(ABC):
    def write_bytes(self, kind, key, data, metadata) -> VaultObjectRef
    def read_bytes(self, kind, key) -> bytes
    def exists(self, kind, key) -> bool
    def list_by_prefix(self, kind, prefix) -> list[str]
    def delete(self, kind, key) -> bool
    def get_metadata(self, kind, key) -> dict | None
```

### LocalFsVault
Filesystem implementation storing objects under `{root}/{kind.value}/{key}` with `.meta.json` sidecars.

## Content hashing

`compute_content_hash(data: bytes) -> str` — SHA-256 of the content, truncated to 16 hex characters. Used as the canonical identifier for deduplication.

## Integration points

- `VenueSnapshotCrawler.store_html()` writes snapshots to vault
- `build_venue_evidence_stack()` can optionally accept a vault for persistent storage
- CLI commands operate without vault by default (in-memory only)

## Code locations

- `src/kairoskopion/storage/vault_backend.py` — ABC and primitives
- `src/kairoskopion/storage/local_fs_vault.py` — filesystem implementation
- `tests/test_venue_evidence_stack.py::TestLocalFsVault` — 10 tests
