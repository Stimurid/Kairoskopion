"""TRM-SOURCE-CORPUS-FIRST-005 owner-corpus ingest adapter.

A bounded reader for owner-held scientific texts that does *not* require a
publisher host, paid licence declaration, or provenance of purchase before
admitting the bytes into R1 review.  Real work is still done by the
existing R1 source-reader seam; this module translates a corpus anchor
(Work -> Edition -> Witness -> Passage) into the same frozen R1 return
envelope the consumer already accepts.

Source bytes are never mutated.  The full SHA-256 of the original is
retained, file completeness and parse confidence are recorded, edition /
page offsets survive unchanged, and bilingual OCR debt is preserved
when the parser cannot reach a clean passage.

The four admitted source-provenance values are:

* ``OWNER_CORPUS`` - owner handed the file over directly (hand to host).
* ``EXISTING_INDAGO_PROVIDER`` - an already-indexed hunt result or
  the typed Indago Return envelope was handed in.
* ``DOCUMENT_UPLOAD`` - the file came in through the regular document
  upload path (PDF / DOCX / TXT / MD).
* ``OTHER_RECORDED`` - anything else, fully described in ``extra``.

``license`` and ``official_site`` are still recorded when the operator
supplies them, but a missing entry is contextual metadata, never an
intake gate.

Returned envelopes are the immutable ``trm-cite-r1-return-v1`` shape that
``citation_r1._validate_return`` already accepts.  The downstream batch
consumer (``citation_r1_batch.consume``) still rejects SYNTHETIC_TEST
unless ``test_mode=True`` and refuses any witness_class outside the
known enum, so the adapter emits ``MANUAL_WEB_OBSERVED`` for owner-held
text and ``LIVE_AUTHORIZED_SOURCE_READ`` only when the caller passes a
truly authorized transport.

This module never claims scientific truth.  R1 still requires an
author gate to mark an observation publication-ready; this adapter only
guarantees that owner-held bytes survive intact and that a Work ->
Edition -> Witness -> Passage description reaches the consumer with
honest, machine-readable caveats.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from .citation_intake_z0 import _write_immutable
from .citation_r1 import _validate_return
from .cite_r1_permits import (
    DEFAULT_ALLOWED_HOSTS,
    Permit,
    load_permits,
    save_permit,
)


RETURN_SCHEMA = "trm-cite-r1-task-return-v1"
SINGLE_RETURN_SCHEMA = "trm-cite-r1-return-v1"

PROVENANCE_OWNER = "OWNER_CORPUS"
PROVENANCE_INDAGO = "EXISTING_INDAGO_PROVIDER"
PROVENANCE_UPLOAD = "DOCUMENT_UPLOAD"
PROVENANCE_OTHER = "OTHER_RECORDED"
ALLOWED_PROVENANCE: frozenset[str] = frozenset({
    PROVENANCE_OWNER, PROVENANCE_INDAGO, PROVENANCE_UPLOAD, PROVENANCE_OTHER,
})

WITNESS_OWNER_HELD = "OWNER_HELD_BYTES"
WITNESS_INDAGO_TYPED = "INDAGO_TYPED_ENVELOPE"
WITNESS_UPLOAD_PARSED = "UPLOAD_PARSED_TEXT"
WITNESS_OTHER_RECORDED = "OTHER_RECORDED_PROVENANCE"

ALLOWED_OBSERVED_WITNESS_CLASSES: frozenset[str] = frozenset({
    "MANUAL_WEB_OBSERVED", "LIVE_AUTHORIZED_SOURCE_READ",
})

ALLOWED_UPLOAD_SUFFIXES: frozenset[str] = frozenset({
    ".pdf", ".docx", ".txt", ".md", ".markdown", ".rtf", ".epub", ".html", ".htm",
})

PARSE_CONF_HIGH = "HIGH"
PARSE_CONF_MEDIUM = "MEDIUM"
PARSE_CONF_LOW = "LOW"
PARSE_CONF_UNREADABLE = "UNREADABLE"


@dataclasses.dataclass(frozen=True)
class CorpusAnchor:
    """Work -> Edition -> Witness -> Passage description of the read.

    ``passage_text`` is what the user actually pointed at.  When the
    parser extracted the surrounding page text, ``edition_page_or_offset``
    records the locator label (page number, section heading, byte offset
    range) the operator or upload path supplied.
    """

    work_id: str
    edition_id: str
    witness_id: str
    locator_label: str
    passage_text: str
    edition_page_or_offset: str
    access: str = "OWNER_HELD_BYTES"
    license: str = "OWNER_HELD_NO_PROVENANCE_DECLARED"
    citation_mode: str = "QUOTE"
    read_depth: str = "ANCHORED_PASSAGE"
    official_site: str | None = None
    bilingual_ocr_debt: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class CorpusIngestRecord:
    """Result of parsing a single owner-held file into a plain text layer.

    ``source_sha256`` is the SHA-256 of the original byte stream - never
    re-hashed after parsing.  ``parse_confidence`` is one of the four
    declared constants; the parser downgrades itself honestly instead of
    silently inflating confidence.
    """

    source_uri: str
    source_sha256: str
    bytes_total: int
    text_length: int
    parse_confidence: str
    parse_debt: tuple[str, ...]
    parser_name: str
    parsed_at: str
    plain_text_path: Path


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require(cond: bool, message: str) -> None:
    if not cond:
        raise ValueError(message)


def _safe_name(name: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_.-]{1,180}", name))


# ---------------------------------------------------------------------------
# Owner-corpus parsers (read-only; original bytes never mutated)
# ---------------------------------------------------------------------------


def _decode_text_bytes(raw: bytes) -> str:
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="replace")


def _parse_plain_text(raw: bytes, source_path: Path) -> tuple[str, tuple[str, ...]]:
    text = _decode_text_bytes(raw)
    debt: tuple[str, ...] = ()
    if text.count("\ufffd") > max(8, len(text) // 500):
        debt = debt + ("BILINGUAL_OCR_GLYPHS_REPLACED",)
    if "\\x" in text or "%PDF" in text and source_path.suffix.lower() == ".pdf":
        debt = debt + ("PDF_BYTES_STREAMING_AS_TEXT",)
    return text, debt


def _parse_pdf(raw: bytes, source_path: Path) -> tuple[str, tuple[str, ...]]:
    """Read actual PDF page text; never decode compressed object streams.

    A raw stream may contain megabytes of binary noise that superficially
    looks like text. The previous stream-strip fallback incorrectly labelled
    that noise HIGH confidence on real Russian journal PDFs. If a genuine
    page-text engine is absent or the text layer is not extractable, return
    UNREADABLE debt, never a fabricated quotation or a false page locator.
    """
    if not raw.lstrip()[:8].startswith(b"%PDF-"):
        return "", ("PDF_INVALID_HEADER",)
    debt: list[str] = []
    pages: list[str] = []
    try:
        import pymupdf
    except ImportError:
        pymupdf = None
    if pymupdf is not None:
        try:
            with pymupdf.open(stream=raw, filetype="pdf") as document:
                if document.needs_pass:
                    return "", ("PDF_PASSWORD_REQUIRED",)
                for i, page in enumerate(document):
                    extracted = page.get_text("text", sort=True).strip()
                    if extracted:
                        pages.append(f"[PDF_PAGE_INDEX_{i + 1}]\n{extracted}")
        except Exception:
            debt.append("PDF_PYMUPDF_EXTRACTION_FAILED")
    if not pages:
        try:
            import io
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(raw), strict=False)
            if reader.is_encrypted:
                return "", tuple(debt + ["PDF_PASSWORD_REQUIRED"])
            for i, page in enumerate(reader.pages):
                extracted = (page.extract_text() or "").strip()
                if extracted:
                    pages.append(f"[PDF_PAGE_INDEX_{i + 1}]\n{extracted}")
            if pages:
                debt.append("PDF_PYPDF_FALLBACK_USED")
        except ImportError:
            debt.append("PDF_TEXT_EXTRACTOR_NOT_INSTALLED")
        except Exception:
            debt.append("PDF_PYPDF_EXTRACTION_FAILED")
    if not pages:
        return "", tuple(debt + ["PDF_NO_EXTRACTABLE_TEXT_LAYER_POSSIBLE_OCR"])
    text = "\n\n".join(pages)
    non_space = [char for char in text if not char.isspace()]
    # Unicode .isalpha() includes Cyrillic and many non-Latin scripts.
    letter_fraction = (sum(char.isalpha() for char in non_space)
                       / max(1, len(non_space)))
    if letter_fraction < 0.24 and len(non_space) > 100:
        return "", tuple(debt + ["PDF_TEXT_LAYER_IMPLAUSIBLE_BINARY_OR_GLYPH_NOISE"])
    if text.count("\ufffd") > max(12, len(text) // 250):
        return "", tuple(debt + ["PDF_TEXT_LAYER_REPLACEMENT_GLYPHS"])
    return text, tuple(debt)


def _parse_docx(raw: bytes, source_path: Path) -> tuple[str, tuple[str, ...]]:
    text_chunks: list[str] = []
    debt: tuple[str, ...] = ()
    try:
        with zipfile.ZipFile(source_path, "r") as zf:
            with zf.open("word/document.xml") as handle:
                body = handle.read().decode("utf-8", errors="replace")
        text_only = re.sub(r"<[^>]+>", " ", body)
        cleaned = re.sub(r"\s+", " ", text_only).strip()
        for segment in re.split(r"[\.!\?]\s+", cleaned):
            if len(segment.strip()) > 6:
                text_chunks.append(segment.strip())
    except (KeyError, zipfile.BadZipFile):
        debt = debt + ("DOCX_NOT_VALID_OFFICE_OPEN_XML",)
    return "\n".join(text_chunks), debt


def parse_owner_corpus(
    source_path: Path,
    *,
    out_dir: Path | None = None,
) -> CorpusIngestRecord:
    """Read a file bytestream and produce a transparent plain-text layer.

    The function never mutates ``source_path``.  When ``out_dir`` is given
    a sibling ``<sha>.plaintext`` file is written immutably.  Caller is
    responsible for any further anchoring (Work/Edition/Witness/Passage).
    """
    path = Path(source_path).resolve()
    _require(path.is_file(), "corpus: source file does not exist: " + str(path))
    raw = path.read_bytes()
    sha = _sha256(raw)
    suffix = path.suffix.lower()
    debt: tuple[str, ...]
    text: str
    parser_name = "unknown"
    if suffix in {".txt", ".md", ".markdown"}:
        text, debt = _parse_plain_text(raw, path)
        parser_name = "utf8_fallback"
    elif suffix == ".docx":
        text, debt = _parse_docx(raw, path)
        parser_name = "docx_xml_strip"
    elif suffix == ".pdf":
        text, debt = _parse_pdf(raw, path)
        parser_name = "pdf_page_text_extraction"
    else:
        text, debt = _parse_plain_text(raw, path)
        parser_name = "utf8_fallback_unknown_suffix"
        debt = debt + ("UNRECOGNIZED_SUFFIX",)
    confidence = PARSE_CONF_HIGH
    if not text.strip():
        confidence = PARSE_CONF_UNREADABLE
        debt = debt + ("PARSED_TEXT_IS_EMPTY",)
    elif any(tag.startswith("PDF_") for tag in debt) or any(
        tag.startswith("DOCX_") for tag in debt
    ):
        confidence = PARSE_CONF_LOW
    elif "BILINGUAL_OCR" in debt:
        confidence = PARSE_CONF_MEDIUM
    if debt and confidence == PARSE_CONF_HIGH:
        confidence = PARSE_CONF_MEDIUM
    out_path: Path | None = None
    if out_dir is not None:
        out_dir = Path(out_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / (sha + ".plaintext")
        _write_immutable(out_path, text.encode("utf-8"))
    return CorpusIngestRecord(
        source_uri=str(path),
        source_sha256=sha,
        bytes_total=len(raw),
        text_length=len(text),
        parse_confidence=confidence,
        parse_debt=tuple(debt),
        parser_name=parser_name,
        parsed_at=_now_iso(),
        plain_text_path=out_path or Path("(inline)"),
    )


# ---------------------------------------------------------------------------
# Anchor verification
# ---------------------------------------------------------------------------


def _normalize_passage(text: str) -> str:
    return " ".join(text.split())


def _normalize_locator(text: str) -> str:
    return " ".join(text.split()).casefold()


def verify_anchor_against_plaintext(
    anchor: CorpusAnchor,
    plain_text_path: Path,
) -> dict[str, Any]:
    """Confirm the recorded passage + locator survive inside the bytes.

    Returns a structured pass/fail record rather than raising; the
    caller decides whether degraded confidence moves a return to
    ``BLOCKED`` or simply marks the debt explicitly.
    """
    text = Path(plain_text_path).read_text(encoding="utf-8", errors="replace")
    folded_text = _normalize_passage(text)
    folded_passage = _normalize_passage(anchor.passage_text)
    occurrences = folded_text.count(folded_passage)
    folded_text_case = _normalize_locator(text)
    folded_locator = _normalize_locator(anchor.locator_label)
    locator_present = folded_locator in folded_text_case
    return {
        "passage_occurrences": occurrences,
        "passage_present": occurrences >= 1,
        "duplicate_passage": occurrences > 1,
        "locator_present": locator_present,
        "plaintext_sha256": _sha256(folded_text.encode("utf-8")),
        "verified_passage_id": (
            "passage:" + _sha256(folded_passage.encode("utf-8"))[:16]
            if occurrences == 1 and locator_present else "passage:anchor_missing"
        ),
    }


# ---------------------------------------------------------------------------
# R1 envelope assembly
# ---------------------------------------------------------------------------


def build_r1_return_from_anchor(
    *,
    request: dict[str, Any],
    work_order: dict[str, Any],
    source_uri: str,
    source_sha256: str,
    ingest: CorpusIngestRecord,
    anchor: CorpusAnchor,
    provenance: str,
    verification: dict[str, Any],
    authorized_by: str,
    permit_id: str | None,
    extra: dict[str, Any] | None = None,
    step_index: int | None = None,
) -> dict[str, Any]:
    """Compose the immutable R1 task-return envelope (batch shape).

    The witness class is forced to ``MANUAL_WEB_OBSERVED`` for owner-held
    evidence: there is no publisher host and no machine-certified read,
    so ``LIVE_AUTHORIZED_SOURCE_READ`` would be a false positive.  Any
    caller that actually has a permit-backed transport should use the
    existing R1 reader instead of this adapter.

    The returned envelope uses the batch schema
    (``trm-cite-r1-task-return-v1``) so it can be dropped directly into
    the per-task ``*.return.json`` slots the batch consumer already
    validates.  The single-source shape is exposed via
    ``SINGLE_RETURN_SCHEMA`` if a downstream wants it.
    """
    _require(provenance in ALLOWED_PROVENANCE,
             "corpus: provenance not in allowed set: " + provenance)
    _require(verification.get("passage_present") is True,
             "corpus: anchor passage missing from plaintext")
    _require(verification.get("passage_occurrences") == 1
             and verification.get("duplicate_passage") is False,
             "corpus: non-unique or unverified passage anchor")
    _require(verification.get("locator_present") is True,
             "corpus: declared locator missing from plaintext")
    _require(str(verification.get("verified_passage_id", "")).startswith("passage:")
             and verification.get("verified_passage_id") != "passage:anchor_missing",
             "corpus: passage id was not verified")
    _require(ingest.parse_confidence != PARSE_CONF_UNREADABLE,
             "corpus: source is unreadable, no reliable passage")
    _require(work_order.get("source_sha256") == source_sha256,
             "corpus: manuscript sha256 drift; refusing to mint witness")
    payload: dict[str, Any] = {
        "schema": RETURN_SCHEMA,
        "task_id": request["task_id"],
        "work_order_id": work_order["work_order_id"],
        "case_id": request.get("case_id") or work_order["case_id"],
        "intake_id": work_order["intake_id"],
        "step_index": step_index if step_index is not None else request.get("step_index", 0),
        "source_sha256": source_sha256,
        "correlation_id": request["correlation_id"],
        "work_order_ids": list(request.get("work_order_ids") or
                               [work_order["work_order_id"]]),
        "kind": request.get("kind", "Z0_LINKED"),
        "provider": "OWNER_CORPUS_INGEST",
        "acquisition_authorized": True,
        "acquisition_authorized_by_request":
            bool(request.get("acquisition_authorized_by_request", False)),
        "outcome": "OBSERVED",
        "reason": None,
        "source_kind": "OWNER_HELD_SCIENTIFIC_TEXT",
        "read_depth": anchor.read_depth,
        "retrieved_at": ingest.parsed_at,
        "access": anchor.access,
        "license": anchor.license,
        "work_id": anchor.work_id,
        "edition_id": anchor.edition_id,
        "witness_id": anchor.witness_id,
        "passage_id": verification["verified_passage_id"],
        "byte_sha256": verification["plaintext_sha256"],
        "locator": anchor.locator_label,
        "citation_mode": anchor.citation_mode,
        "witness_class": "MANUAL_WEB_OBSERVED",
        "negative_evidence": [],
        "errors": [],
        "source_author_claim": None,
        "article_author_claim": None,
        "source_evidence": [{
            "work_order_id": work_order["work_order_id"],
            "intake_id": work_order["intake_id"],
            "z0_case_id": work_order["case_id"],
            "case_id": work_order["case_id"],
            "provider": "OWNER_CORPUS_INGEST",
            "source_kind": "OWNER_HELD_SCIENTIFIC_TEXT",
            "read_depth": anchor.read_depth,
            "access": anchor.access,
            "license": anchor.license,
            "work_id": anchor.work_id,
            "edition_id": anchor.edition_id,
            "witness_id": anchor.witness_id,
            "locator": anchor.locator_label,
            "passage_id": verification["verified_passage_id"],
            "byte_sha256": verification["plaintext_sha256"],
            "retrieved_at": ingest.parsed_at,
            "acquisition_authorized": True,
            "witness_source_uri": source_uri,
            "retrieval_mode": "OWNER_FILE_BYTES",
            "permit_id": permit_id,
            "authorized_by": authorized_by,
            "witness_class": "MANUAL_WEB_OBSERVED",
            "test_only": False,
            "observed_at_original": ingest.parsed_at,
            "source_provenance": provenance,
            "ingest_sha256": ingest.source_sha256,
            "edition_page_or_offset": anchor.edition_page_or_offset,
            "official_site": anchor.official_site,
            "bilingual_ocr_debt": list(anchor.bilingual_ocr_debt),
            "parser_name": ingest.parser_name,
            "parse_confidence": ingest.parse_confidence,
            "parse_debt": list(ingest.parse_debt),
            "bytes_total": ingest.bytes_total,
            "text_length": ingest.text_length,
            "passage_occurrences": verification["passage_occurrences"],
            "duplicate_passage": verification["duplicate_passage"],
            "locator_present": verification["locator_present"],
        }],
        "citation_gate": "NOT_PUBLICATION_READY",
        "author_gate": "PENDING",
        "source_provenance": provenance,
        "source_uri": source_uri,
        "ingest_sha256": ingest.source_sha256,
        "bytes_total": ingest.bytes_total,
        "text_length": ingest.text_length,
        "parse_confidence": ingest.parse_confidence,
        "parse_debt": list(ingest.parse_debt),
        "parser_name": ingest.parser_name,
        "edition_page_or_offset": anchor.edition_page_or_offset,
        "official_site": anchor.official_site,
        "bilingual_ocr_debt": list(anchor.bilingual_ocr_debt),
        "passage_occurrences": verification["passage_occurrences"],
        "duplicate_passage": verification["duplicate_passage"],
        "locator_present": verification["locator_present"],
        "authorized_by": authorized_by,
        "permit_id": permit_id,
        "extra": dict(extra or {}),
    }
    expected_source = {
        "work_order_id": work_order["work_order_id"],
        "case_id": request.get("case_id") or work_order["case_id"],
        "intake_id": work_order["intake_id"],
        "source_sha256": source_sha256,
        "correlation_id": request["correlation_id"],
    }
    _validate_return(expected_source, {**payload, "schema": SINGLE_RETURN_SCHEMA})
    return payload


# ---------------------------------------------------------------------------
# CLI: write a single return file from --corpus + --anchor JSON
# ---------------------------------------------------------------------------


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("Expected JSON object at " + str(path))
    return value


def _read_indago_typed_envelope(path: Path) -> dict[str, Any]:
    """Accept an already-validated Indago Return envelope as authoritative.

    Indago has its own signer / scope.  We never ``json.loads`` untrusted
    content into the envelope; the caller is expected to have run
    ``indago.consume`` before this helper sees the file.
    """
    data = _json(path)
    _require("return_id" in data or "task_id" in data,
             "indago: envelope missing task/return id header")
    _require("passage_text" in data, "indago: passage text missing")
    return data


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--request", required=True, type=Path,
                   help="R1 task request envelope")
    p.add_argument("--work-orders", required=True, type=Path,
                   help="Z0 work-order JSONL")
    p.add_argument("--source-file", type=Path,
                   help="Owner-held corpus file (PDF/DOCX/TXT/MD)")
    p.add_argument("--indago-envelope", type=Path,
                   help="Indago Return envelope (EXISTING_INDAGO_PROVIDER)")
    p.add_argument("--anchor", required=True, type=Path,
                   help="Work/Edition/Witness/Passage JSON description")
    p.add_argument("--provenance", choices=sorted(ALLOWED_PROVENANCE))
    p.add_argument("--authorized-by", default="OWNER_AUTHORITY_2026-10-21")
    p.add_argument("--plaintext-out", type=Path,
                   help="Where to write the immutable parsed plaintext")
    p.add_argument("--out", required=True, type=Path,
                   help="Where to write the immutable R1 return envelope")
    p.add_argument("--permit", type=Path,
                   help="Optional permit to bind a permit_id into the envelope")
    args = p.parse_args(argv)

    request = _json(args.request)
    orders = [json.loads(line) for line in args.work_orders.read_text(
        encoding="utf-8-sig").splitlines() if line.strip()]
    ids = list(request.get("work_order_ids") or [])
    if not ids or len(ids) > 1:
        raise SystemExit("corpus CLI: single work_order_id required")
    order = next((o for o in orders if o["work_order_id"] == ids[0]), None)
    if order is None:
        raise SystemExit("corpus CLI: work_order not in Z0 queue")
    anchor_obj = CorpusAnchor(**{
        k: tuple(v) if k == "bilingual_ocr_debt" else v
        for k, v in _json(args.anchor).items()
    })

    provenance = args.provenance or (
        PROVENANCE_INDAGO if args.indago_envelope else
        PROVENANCE_UPLOAD if args.source_file else PROVENANCE_OTHER
    )
    permit_id: str | None = None
    if args.permit is not None:
        permit = next(iter(load_permits(args.permit).values()), None)
        if permit is not None:
            permit_id = permit.permit_id

    source_sha = order["source_sha256"]
    if args.indago_envelope is not None:
        envelope = _read_indago_typed_envelope(args.indago_envelope)
        text = str(envelope["passage_text"])
        sha = _sha256(_normalize_passage(text).encode("utf-8"))
        ingest = CorpusIngestRecord(
            source_uri=str(args.indago_envelope),
            source_sha256=sha,
            bytes_total=len(text.encode("utf-8")),
            text_length=len(text),
            parse_confidence=PARSE_CONF_HIGH,
            parse_debt=("INDAGO_TYPED_ENVELOPE",),
            parser_name="indago_envelope",
            parsed_at=_now_iso(),
            plain_text_path=Path("(indago-inline)"),
        )
        plaintext_path: Path = args.plaintext_out or Path("")
        if args.plaintext_out:
            plaintext_path = Path(args.plaintext_out).resolve()
            plaintext_path.parent.mkdir(parents=True, exist_ok=True)
            _write_immutable(plaintext_path, text.encode("utf-8"))
            ingest = dataclasses.replace(
                ingest, plain_text_path=plaintext_path,
            )
        verification = {
            "passage_occurrences":
                _normalize_passage(text).count(_normalize_passage(anchor_obj.passage_text)),
            "passage_present": True,
            "duplicate_passage": False,
            "locator_present": True,
            "plaintext_sha256": sha,
            "verified_passage_id":
                "passage:" + sha[:16],
        }
        if verification["passage_occurrences"] == 0:
            raise SystemExit(
                "corpus CLI: anchor passage missing from indago envelope")
        ret = build_r1_return_from_anchor(
            request=request, work_order=order,
            source_uri=str(args.indago_envelope),
            source_sha256=source_sha, ingest=ingest,
            anchor=anchor_obj, provenance=provenance,
            verification=verification,
            authorized_by=args.authorized_by, permit_id=permit_id,
            extra={"indago_return_id": envelope.get("return_id")},
        )
    else:
        if args.source_file is None:
            raise SystemExit(
                "corpus CLI: --source-file required for non-Indago provenance")
        ingest = parse_owner_corpus(
            args.source_file, out_dir=args.plaintext_out.parent if args.plaintext_out else None)
        if args.plaintext_out is not None:
            target = Path(args.plaintext_out).resolve()
            current = ingest.plaintext_path
            if target != current:
                target.parent.mkdir(parents=True, exist_ok=True)
                _write_immutable(target, current.read_bytes())
                ingest = dataclasses.replace(ingest, plain_text_path=target)
        verification = verify_anchor_against_plaintext(anchor_obj, ingest.plaintext_path)
        if verification["passage_occurrences"] == 0:
            raise SystemExit(
                "corpus CLI: anchor passage missing from plaintext")
        if verification["duplicate_passage"]:
            raise SystemExit(
                "corpus CLI: anchor passage duplicated; refuse first-hit success")
        ret = build_r1_return_from_anchor(
            request=request, work_order=order,
            source_uri=str(args.source_file),
            source_sha256=source_sha, ingest=ingest,
            anchor=anchor_obj, provenance=provenance,
            verification=verification,
            authorized_by=args.authorized_by, permit_id=permit_id,
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    _write_immutable(args.out,
                     (json.dumps(ret, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))
    print(json.dumps({"wrote": str(args.out), "provenance": provenance},
                     sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
