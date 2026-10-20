"""TRM-CITE-001 Z0: preservation-first, read-only citation intake.

No reference found here is certified. Detection creates an immutable original
snapshot and typed work orders for independent Z2-Z7 source verification.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import re
import shutil
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

VERSION = "trm-cite-z0-v01"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PKG = "{http://schemas.openxmlformats.org/package/2006/relationships}"

DESIRED = [
    re.compile(r"\[\s*(?:citation needed|needs citation|нужна\s+(?:ссылка|цитата)|тут\s+цитата|цитата\s+[^\]\n]{2,80})\s*\]", re.I),
    re.compile(r"\b(?:TODO|FIXME)\s*:\s*(?:cite|citation|ссылк\w*|цитат\w*)[^\n;.]{0,90}", re.I),
    re.compile(r"\b(?:тут|здесь|сюда)\s+(?:нужн[ао]\s+|добавить\s+|найти\s+|поставить\s+)?(?:цитат\w*|ссылк\w*)(?:\s+(?:(?:из|по|у)\s+)?[А-ЯЁA-Z][^\]\n.,;]{0,65})?", re.I),
    re.compile(r"\b(?:кто[- ]?то\s+из\s+великих\s+сказал|как\s+(?:говорил|писал)\s+[А-ЯЁ][\wёЁ-]{2,})", re.I),
]
PATTERNS = [
    ("AUTHOR_YEAR", re.compile(r"\([A-ZА-ЯЁ][A-Za-zА-Яа-яЁё.'’-]{2,}(?:\s+(?:et\s+al\.?|и\s+др\.?))?,?\s+(?:1[5-9]\d{2}|20\d{2}|21\d{2})(?:[,;:]\s*(?:с\.|p\.|pp\.)?\s*\d+(?:[-–]\d+)?)?\)")),
    ("NUMERIC_REFERENCE", re.compile(r"(?<!\w)\[\d{1,3}(?:\s*,\s*\d{1,3})*\](?!\w)")),
    ("FOOTNOTE_REFERENCE", re.compile(r"\[\^[\w-]+\]")),
    ("DOI_REFERENCE", re.compile(r"\b10\.\d{4,9}/[-._;()/:\w]+\b", re.I)),
    ("CITEKEY", re.compile(r"(?<!\w)@[A-Za-z][A-Za-z0-9:_-]{2,}")),
    ("LATEX_CITE", re.compile(r"\\cite(?:p|t|author|year)?\{[^{}\n]{1,120}\}")),
]
QUOTE = re.compile(r"«[^»\n]{18,}»|“[^”\n]{18,}”|\"[^\"\n]{22,}\"")
BIB = re.compile(r"^\s*(?:#{1,6}\s*)?(?:References|Bibliography|Works\s+Cited|Список\s+(?:использованной\s+)?литературы|Библиография|Литература)\s*:?\s*$", re.I)


@dataclass(frozen=True)
class Section:
    surface: str
    locator: str
    text: str
    parent_anchor: str | None = None
    fields: tuple[str, ...] = ()
    links: tuple[str, ...] = ()
    is_heading: bool = False


@dataclass(frozen=True)
class CitationIntake:
    intake_id: str
    origin_type: str
    kind: str
    surface: str
    anchor: dict[str, Any]
    original_fragment: str
    claim_context: str
    source_hints: tuple[str, ...]
    parent_anchor: str | None
    source_sha256: str
    verification_status: str = "NOT_CHECKED"
    source_read_depth: str = "NONE"
    classification: str = "CANDIDATE_ONLY"


@dataclass(frozen=True)
class CitationRepairCase:
    case_id: str
    intake_id: str
    status: str
    original_preserved: bool
    reason_codes: tuple[str, ...]
    required_operations: tuple[str, ...]
    verification: dict[str, str]
    author_gate: str
    proposed_patch: None = None


@dataclass
class CitationAudit:
    schema_version: str
    source: dict[str, Any]
    coverage: dict[str, Any]
    intakes: list[CitationIntake]
    repair_cases: list[CitationRepairCase]

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def _id(prefix: str, *s: str) -> str:
    return prefix + "_" + hashlib.sha256("\x1f".join(s).encode()).hexdigest()[:20]


def _word_text(p: ET.Element, surface: str, locator: str,
               parent: str | None, links: dict[str, str]) -> Section:
    text: list[str] = []
    instr: list[str] = []
    urls: list[str] = []
    for el in p.iter():
        if el.tag == W + "t":
            text.append(el.text or "")
        elif el.tag == W + "tab":
            text.append("\t")
        elif el.tag in (W + "br", W + "cr"):
            text.append("\n")
        elif el.tag == W + "instrText":
            instr.append(el.text or "")
        elif el.tag == W + "fldSimple":
            instr.append(el.get(W + "instr", ""))
        elif el.tag == W + "hyperlink":
            rid = el.get(R + "id")
            if rid in links:
                urls.append(links[rid])
    field_text = "".join(instr).strip()
    style = p.find(".//" + W + "pStyle")
    value = (style.get(W + "val", "") if style is not None else "")
    heading = bool(re.match(r"^(?:Heading|Заголовок)\s*\d+", value, re.I))
    return Section(surface, locator, "".join(text), parent,
                   (field_text,) if field_text else (),
                   tuple(dict.fromkeys(urls)), heading)


def _docx_sections(path: Path) -> tuple[list[Section], dict[str, Any]]:
    sections: list[Section] = []
    surfaces: dict[str, str] = {}
    debts: list[str] = []
    with zipfile.ZipFile(path) as z:
        members = set(z.namelist())
        if "word/document.xml" not in members:
            raise ValueError("DOCX has no document.xml")
        for name in members:
            if name.startswith("word/") and name.endswith(".xml") and (
                name == "word/document.xml" or
                name in ("word/comments.xml", "word/footnotes.xml",
                         "word/endnotes.xml") or
                re.fullmatch(r"word/(?:header|footer)\d+\.xml", name)
            ):
                if z.getinfo(name).file_size > 32 * 1024 * 1024:
                    raise ValueError("Oversized XML part: " + name)
        links: dict[str, str] = {}
        rel_name = "word/_rels/document.xml.rels"
        if rel_name in members:
            rels = ET.fromstring(z.read(rel_name))
            links = {
                el.get("Id", ""): el.get("Target", "")
                for el in rels.findall(PKG + "Relationship")
                if el.get("TargetMode") == "External" and el.get("Id")
            }
        body = ET.fromstring(z.read("word/document.xml"))
        parent_refs: dict[tuple[str, str], str] = {}
        for i, p in enumerate(body.iter(W + "p")):
            locator = f"word/document.xml/p[{i}]"
            sections.append(_word_text(p, "body", locator, None, links))
            for el in p.iter():
                typ = {
                    W + "commentRangeStart": "comment",
                    W + "commentReference": "comment",
                    W + "footnoteReference": "footnote",
                    W + "endnoteReference": "endnote",
                }.get(el.tag)
                if typ and el.get(W + "id") is not None:
                    parent_refs[(typ, el.get(W + "id", ""))] = locator
        surfaces["body"] = "SCANNED"
        for name, element, surface in (
            ("word/comments.xml", "comment", "comment"),
            ("word/footnotes.xml", "footnote", "footnote"),
            ("word/endnotes.xml", "endnote", "endnote"),
        ):
            if name not in members:
                surfaces[surface] = "ABSENT"
                continue
            try:
                root = ET.fromstring(z.read(name))
                for node in root.iter(W + element):
                    key = node.get(W + "id", "unknown")
                    if node.get(W + "type") in ("separator", "continuationSeparator"):
                        continue
                    parent = parent_refs.get((surface, key))
                    if parent is None:
                        debts.append(f"{surface}[{key}] has no body anchor")
                    for i, p in enumerate(node.iter(W + "p")):
                        sections.append(_word_text(
                            p, surface, f"{name}/{element}[{key}]/p[{i}]",
                            parent, {},
                        ))
                surfaces[surface] = "SCANNED"
            except ET.ParseError:
                surfaces[surface] = "FAILED"
                debts.append("Failed to parse " + name)
        for name in sorted(members):
            if re.fullmatch(r"word/(?:header|footer)\d+\.xml", name):
                surface = "header" if "header" in name else "footer"
                try:
                    root = ET.fromstring(z.read(name))
                    for i, p in enumerate(root.iter(W + "p")):
                        sections.append(_word_text(
                            p, surface, f"{name}/p[{i}]", None, {},
                        ))
                    surfaces[surface] = "SCANNED"
                except ET.ParseError:
                    surfaces[surface] = "FAILED"
                    debts.append("Failed to parse " + name)
        if any("commentsExtended" in m or "commentsIds" in m for m in members):
            debts.append("Modern comment threads not fully supported")
        if body.find(".//" + W + "del") is not None:
            debts.append("Tracked deletions excluded from visible text")
        if body.find(".//" + W + "altChunk") is not None:
            debts.append("Embedded altChunk not scanned")
        if body.find(".//" + W + "object") is not None:
            debts.append("Embedded OLE object not scanned")
    return sections, {"surfaces": surfaces, "debts": debts}


def _load_sections(path: Path) -> tuple[list[Section], dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix in (".md", ".txt"):
        sections = []
        debt = []
        fenced = False
        for i, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            if suffix == ".md" and re.match(r"^\s*(?:\x60{3}|~{3})", line):
                fenced = not fenced
                continue
            if fenced:
                if "Markdown code fence skipped" not in debt:
                    debt.append("Markdown code fence skipped")
                continue
            sections.append(Section("body", f"line:{i}", line))
        if fenced:
            debt.append("Markdown code fence unclosed")
        return sections, {
            "surfaces": {"body": "SCANNED", "editor_comments": "UNKNOWN"},
            "debts": debt + ["No editor comment extraction for plain text"],
        }
    if suffix == ".docx":
        return _docx_sections(path)
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("format") != "trm-cite-sections-v1":
            raise ValueError("Invalid Z0 structured manuscript envelope")
        source = data.get("sections")
        if not isinstance(source, list) or not source or len(source) > 200000:
            raise ValueError("Missing, invalid or oversized sections")
        sections = []
        for i, sec in enumerate(source):
            if not isinstance(sec, dict) or not isinstance(sec.get("text"), str):
                raise ValueError(f"Invalid section[{i}]")
            sections.append(Section(
                str(sec.get("surface", "body")),
                str(sec.get("locator", f"section:{i}")), sec["text"],
                sec.get("parent_anchor"),
                tuple(str(x) for x in sec.get("field_instructions", [])),
                tuple(str(x) for x in sec.get("links", [])),
            ))
        coverage = data.get("coverage", {})
        if not isinstance(coverage, dict):
            coverage = {}
        debt = [
            f"{name} coverage unproven"
            for name in ("body", "comments", "footnotes", "bibliography")
            if coverage.get(name) not in ("SCANNED", "ABSENT")
        ]
        return sections, {"surfaces": coverage, "debts": debt}
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as e:
            raise ValueError("PDF requires optional pypdf") from e
        pdf = PdfReader(str(path))
        if pdf.is_encrypted:
            raise ValueError("Encrypted PDF cannot be scanned")
        sections = [Section("pdf_page", f"page:{i+1}",
                            page.extract_text() or "")
                    for i, page in enumerate(pdf.pages)]
        debt = ["PDF annotations not read", "PDF exact viewer anchors untested"]
        if not any(x.text.strip() for x in sections):
            debt.append("No PDF text extracted; OCR needed")
        return sections, {"surfaces": {"pdf_page": "SCANNED"},
                          "debts": debt}
    raise ValueError("Supported manuscripts: .md .txt .docx .pdf .json")


def _intake(sha: str, sec: Section, origin: str, kind: str,
            start: int, end: int, raw: str,
            classification: str = "CANDIDATE_ONLY") -> CitationIntake:
    anchor = {
        "locator": sec.locator,
        "start_codepoint": start, "end_codepoint": end,
        "start_utf8_byte": len(sec.text[:start].encode("utf-8")),
        "end_utf8_byte": len(sec.text[:end].encode("utf-8")),
        "offset_scope": "extracted_text_only",
        "exact_editor_selection_verified": False,
    }
    return CitationIntake(
        _id("ci", sha, sec.surface, sec.locator, origin, kind,
            str(start), str(end), raw), origin, kind, sec.surface,
        anchor, raw, sec.text, (raw,), sec.parent_anchor, sha,
        classification=classification,
    )


def _scan(sec: Section, sha: str, bibliography: bool) -> list[CitationIntake]:
    found: list[CitationIntake] = []
    text = sec.text
    if bibliography:
        if text.strip() and not BIB.match(text):
            found.append(_intake(sha, sec, "EXISTING",
                                 "BIBLIOGRAPHY_ENTRY", 0, len(text), text))
    else:
        for pattern in DESIRED:
            for m in pattern.finditer(text):
                found.append(_intake(
                    sha, sec, "AUTHOR_DESIRED", "CITATION_WISH",
                    m.start(), m.end(), m.group(0),
                ))
        for kind, pattern in PATTERNS:
            for m in pattern.finditer(text):
                found.append(_intake(
                    sha, sec, "EXISTING", kind,
                    m.start(), m.end(), m.group(0),
                ))
        for m in QUOTE.finditer(text):
            has_ref = any(
                c.origin_type == "EXISTING" and
                0 <= c.anchor["start_codepoint"] - m.end() <= 85
                for c in found
            )
            if not has_ref:
                found.append(_intake(
                    sha, sec, "EXISTING", "UNATTRIBUTED_QUOTE_CANDIDATE",
                    m.start(), m.end(), m.group(0), "HEURISTIC_ONLY",
                ))
    for instr in sec.fields:
        kind = ("ZOTERO_FIELD" if "ZOTERO_ITEM" in instr.upper()
                else "ZOTERO_BIBLIOGRAPHY_FIELD"
                if "ZOTERO_BIBL" in instr.upper() else "WORD_FIELD")
        found.append(_intake(
            sha, sec, "EXISTING", kind, 0, len(text), instr,
        ))
    for link in sec.links:
        if link.startswith(("http://", "https://")):
            found.append(_intake(
                sha, sec, "EXISTING", "EMBEDDED_HYPERLINK",
                0, len(text), link, "LINK_TARGET_ONLY",
            ))
    return sorted(
        {c.intake_id: c for c in found}.values(),
        key=lambda c: (c.anchor["start_codepoint"], c.kind),
    )


def _repair_case(ci: CitationIntake) -> CitationRepairCase:
    if ci.origin_type == "AUTHOR_DESIRED":
        reason = ("AUTHOR_REQUEST_PENDING",)
        operations = (
            "Z2_CONDENSE_ORIGINAL_AUTHOR_INTENT",
            "Z3_SOURCE_AND_OPPOSING_EVIDENCE_HUNT",
            "Z4_RESOLVE_WORK_EDITION_WITNESS",
            "Z5_EXACT_PASSAGE_AND_ANCHOR",
            "Z6_INDEPENDENT_V1_V5_AND_AUTHOR_GATE",
            "Z7_PROPOSE_REVERSIBLE_INSERTION_AND_RECHECK",
        )
    elif ci.kind == "UNATTRIBUTED_QUOTE_CANDIDATE":
        reason = ("ATTRIBUTION_UNCONFIRMED",)
        operations = (
            "Z2_DETERMINE_QUOTE_FUNCTION",
            "Z3_FIND_ATTESTED_SOURCE_OR_NEGATIVE_RESULT",
            "Z4_RESOLVE_WORK_EDITION_WITNESS",
            "Z5_VERIFY_VERBATIM_AND_CONTEXT",
            "Z6_INDEPENDENT_V1_V5_AND_AUTHOR_GATE",
            "Z7_PROPOSE_REPAIR_AND_RECHECK",
        )
    else:
        reason = ("EXISTING_CITATION_NOT_AUDITED",)
        operations = (
            "R1_AUDIT_ORIGINAL_WITHOUT_ASSUME_DEFECT",
            "Z4_RESOLVE_ASSERTED_WORK_EDITION_WITNESS",
            "Z5_CHECK_QUOTE_AND_REAL_ANCHOR",
            "Z6_INDEPENDENT_V1_V5",
            "R2_IF_DEFECT_RECOVER_AUTHOR_INTENT",
            "R3_IF_DEFECT_REENTER_FULL_Z2_TO_Z7",
            "R4_OFFER_ALTERNATIVES_AND_AUTHOR_GATE",
            "R5_REVERSIBLE_PATCH_PROPOSAL",
            "R6_READBACK_CLICKTEST_AND_NEGATIVE_TRAIL",
        )
    return CitationRepairCase(
        _id("cr", ci.intake_id), ci.intake_id, "OPEN_UNVERIFIED",
        True, reason, operations,
        {f"V{i}": "NOT_CHECKED" for i in range(1, 6)},
        "REQUIRED_IF_MEANING_CHANGES",
    )


def audit_manuscript(path: str | Path) -> CitationAudit:
    """Build typed unverified objects without modifying the manuscript."""
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    sections, coverage = _load_sections(path)
    found: list[CitationIntake] = []
    bib_state: dict[str, bool] = {}
    for sec in sections:
        if BIB.match(sec.text):
            bib_state[sec.surface] = True
            continue
        if bib_state.get(sec.surface, False) and (
            sec.is_heading or re.match(r"^\s*#{1,6}\s+\S", sec.text)
        ):
            bib_state[sec.surface] = False
        found.extend(_scan(sec, sha, bib_state.get(sec.surface, False)))
    found = sorted(
        {ci.intake_id: ci for ci in found}.values(),
        key=lambda ci: (ci.surface, ci.anchor["locator"],
                        ci.anchor["start_codepoint"], ci.kind),
    )
    debts = sorted(set(coverage["debts"]))
    return CitationAudit(
        VERSION,
        {
            "input_path": str(path), "source_name": path.name,
            "sha256": sha, "byte_length": len(raw),
            "editor_revision_verified": False,
        },
        {
            "status": ("PARTIAL_WITH_COVERAGE_DEBT" if debts
                       else "SCANNED_SURFACES_ONLY"),
            "surfaces": coverage["surfaces"],
            "sections_scanned": len(sections),
            "debts": debts,
            "all_citations_scientifically_verified": False,
            "manuscript_mutated": False,
        },
        found, [_repair_case(ci) for ci in found],
    )


def persist_audit(source_path: str | Path,
                  output_dir: str | Path) -> tuple[CitationAudit, Path]:
    """Store byte-exact original (exclusive create) and immutable JSON receipt."""
    src = Path(source_path).resolve()
    output = Path(output_dir).resolve()
    audit = audit_manuscript(src)
    sha = audit.source["sha256"]
    store = output / "original_snapshots"
    store.mkdir(parents=True, exist_ok=True)
    snap = store / (sha + src.suffix.lower())
    if not snap.exists():
        with snap.open("xb") as dst, src.open("rb") as data:
            shutil.copyfileobj(data, dst)
    if hashlib.sha256(snap.read_bytes()).hexdigest() != sha:
        raise RuntimeError("Original snapshot SHA256 mismatch")
    audit.source["original_snapshot_path"] = str(snap)
    audit.source["original_snapshot_sha256_verified"] = True
    folder = output / "runs" / (VERSION + "_" + sha[:20])
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / "citation_intake.json"
    payload = (json.dumps(audit.to_dict(), ensure_ascii=False,
                          sort_keys=True, indent=2) + "\n").encode()
    if dest.exists():
        if dest.read_bytes() != payload:
            raise RuntimeError("Immutable report conflict; open a new run")
    else:
        with dest.open("xb") as file:
            file.write(payload)
    return audit, dest
