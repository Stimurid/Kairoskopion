"""Resolve venue evidence packs from local files by ISSN or name.

Scans known evidence-pack directories for markdown files, extracts
ISSN and canonical name from the content, and returns the file text
for piping into investigate_venue().
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import NamedTuple

logger = logging.getLogger(__name__)

_ISSN_RE = re.compile(r"\*\*ISSN:\*\*\s*(\d{4}-\d{3}[\dXx])")
_NAME_RE = re.compile(r"^#\s+Venue Evidence Pack:\s*(.+)", re.MULTILINE)


class ResolvedPack(NamedTuple):
    path: Path
    issn: str | None
    canonical_name: str | None
    text: str


def _evidence_pack_dirs(project_root: Path | None = None) -> list[Path]:
    if project_root is None:
        project_root = Path(__file__).resolve().parents[3]
    return [
        project_root / "data" / "venue_evidence_packs",
        project_root / "private_inputs" / "logos_trial",
    ]


def _extract_issn(text: str) -> str | None:
    m = _ISSN_RE.search(text)
    return m.group(1) if m else None


def _extract_name(text: str) -> str | None:
    m = _NAME_RE.search(text)
    if m:
        raw = m.group(1).strip()
        if "/" in raw:
            raw = raw.split("/")[0].strip()
        return raw
    return None


def scan_evidence_packs(
    project_root: Path | None = None,
) -> list[ResolvedPack]:
    packs: list[ResolvedPack] = []
    for d in _evidence_pack_dirs(project_root):
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir()):
            if not f.suffix == ".md":
                continue
            if "evidence_pack" not in f.name:
                continue
            try:
                text = f.read_text(encoding="utf-8")
            except OSError:
                logger.warning("Cannot read evidence pack: %s", f)
                continue
            packs.append(ResolvedPack(
                path=f,
                issn=_extract_issn(text),
                canonical_name=_extract_name(text),
                text=text,
            ))
    return packs


def resolve_by_issn(
    issn: str,
    project_root: Path | None = None,
) -> ResolvedPack | None:
    issn = issn.strip()
    for pack in scan_evidence_packs(project_root):
        if pack.issn and pack.issn == issn:
            return pack
    return None


def resolve_by_name(
    name: str,
    project_root: Path | None = None,
) -> ResolvedPack | None:
    name_lower = name.strip().lower()
    for pack in scan_evidence_packs(project_root):
        if pack.canonical_name and pack.canonical_name.lower() == name_lower:
            return pack
    return None


def resolve(
    *,
    issn: str | None = None,
    name: str | None = None,
    project_root: Path | None = None,
) -> ResolvedPack | None:
    if issn:
        result = resolve_by_issn(issn, project_root)
        if result:
            return result
    if name:
        result = resolve_by_name(name, project_root)
        if result:
            return result
    return None
