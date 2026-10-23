"""Independent bytes-first attestation of a reported Indago passage.

The provider's own SHA, locator, and occurrence count are claims.  Only the
bytes at an operator-chosen local witness path may promote a proposed anchor.
No restriction on the origin/purchase of the witness bytes is imposed.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any


class WitnessRefusal(ValueError):
    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


def _norm(value: str) -> str:
    return " ".join(value.split())


def attest_passages(
    source: dict[str, Any], passages: list[dict[str, Any]],
    witness_path: Path | None,
) -> dict[str, Any]:
    """Return a *measured* anchor status without trusting provider assertions.

    With no original bytes, the only legal state is UNVERIFIED, never ANCHORED.
    Printed-page locators are not assumed to be PDF page indices.
    """
    if witness_path is None:
        return {"status": "WITNESS_BYTES_UNAVAILABLE", "bytes_verified": False,
                "locator_verified": False, "uniqueness_verified": False,
                "actual_passage_occurrences": None}
    path = Path(witness_path)
    if not path.is_file():
        raise WitnessRefusal("Operator witness path does not exist", "WITNESS_FILE_MISSING")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise WitnessRefusal("Operator witness bytes unreadable", "WITNESS_READ_FAILED") from exc
    observed_sha = hashlib.sha256(raw).hexdigest()
    if source.get("source_sha256", "").lower() != observed_sha:
        raise WitnessRefusal("Witness bytes differ from returned source digest",
                             "WITNESS_HASH_MISMATCH")
    declared_id = source.get("witness_id", "").split(":", 1)[-1].lower()
    if re.fullmatch("[0-9a-f]{64}", declared_id) and declared_id != observed_sha:
        raise WitnessRefusal("Witness identity conflicts with actual bytes",
                             "WITNESS_ID_MISMATCH")

    is_pdf = raw.startswith(b"%PDF")
    pages: list[str] = []
    if is_pdf:
        try:
            import pymupdf
            doc = pymupdf.open(stream=raw, filetype="pdf")
            pages = [p.get_text(sort=True) for p in doc]
            doc.close()
        except (ImportError, ValueError, RuntimeError) as exc:
            raise WitnessRefusal("PDF witness could not be read as page text",
                                 "WITNESS_PDF_UNREADABLE") from exc
    elif path.suffix.lower() in {".md", ".txt"}:
        try:
            pages = [raw.decode("utf-8-sig")]
        except UnicodeError as exc:
            raise WitnessRefusal("Text witness is not UTF-8", "WITNESS_TEXT_UNREADABLE") from exc
    else:
        # A .docx witness needs a separate stable element locator adapter:
        # bytes-checking alone cannot certify a Word paragraph position.
        return {"status": "WITNESS_FORMAT_NOT_YET_SUPPORTED",
                "bytes_verified": True, "locator_verified": False,
                "uniqueness_verified": False, "witness_sha256": observed_sha,
                "actual_passage_occurrences": None}

    if not passages or any(not isinstance(p.get("exact_text"), str)
                           or not p["exact_text"].strip() for p in passages):
        return {"status": "PASSAGE_TEXT_UNAVAILABLE",
                "bytes_verified": True, "locator_verified": False,
                "uniqueness_verified": False, "witness_sha256": observed_sha,
                "actual_passage_occurrences": None}

    item_count = []
    for p in passages:
        needle = _norm(p["exact_text"]) if is_pdf else p["exact_text"]
        normalized_pages = [_norm(x) for x in pages] if is_pdf else pages
        occurrences = sum(x.count(needle) for x in normalized_pages)
        item_count.append(occurrences)
        if occurrences == 0:
            raise WitnessRefusal("Reported quotation absent from actual witness text",
                                 "PASSAGE_NOT_IN_WITNESS")
        if is_pdf:
            match = re.fullmatch(r"pdf-page-index:(\d+)", p["locator"])
            if match is None:
                return {"status": "LOCATOR_UNVERIFIED",
                        "bytes_verified": True, "locator_verified": False,
                        "uniqueness_verified": False, "witness_sha256": observed_sha,
                        "actual_passage_occurrences": occurrences}
            page_idx = int(match.group(1))
            if page_idx >= len(pages) or needle not in normalized_pages[page_idx]:
                raise WitnessRefusal("PDF locator does not contain the cited phrase",
                                     "LOCATOR_DISAGREEMENT")
        else:
            match = re.fullmatch(r"text-char-offset:(\d+)", p["locator"])
            if match is None:
                return {"status": "LOCATOR_UNVERIFIED",
                        "bytes_verified": True, "locator_verified": False,
                        "uniqueness_verified": False, "witness_sha256": observed_sha,
                        "actual_passage_occurrences": occurrences}
            offset = int(match.group(1))
            if not pages[0].startswith(needle, offset):
                raise WitnessRefusal("Text offset does not contain the cited phrase",
                                     "LOCATOR_DISAGREEMENT")
    unique = len(passages) == 1 and len(item_count) == 1 and item_count[0] == 1
    return {"status": "VERIFIED_UNIQUE" if unique else "ANCHOR_AMBIGUOUS",
            "bytes_verified": True, "locator_verified": True,
            "uniqueness_verified": unique,
            "witness_sha256": observed_sha,
            "actual_passage_occurrences": item_count[0] if len(item_count) == 1 else item_count}
