"""Private W12 research-stage admission: NOT Article/venue/route acceptance.

A trusted local operator supplies an authorized private Drive ZIP and pinned
hashes. No public upload or automatic editorial send is implemented here.
"""
from __future__ import annotations

from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
from typing import Any
from zipfile import BadZipFile, ZipFile


RECEIPT_SCHEMA = "W12_PRIVATE_SOURCE_ADMISSION_v1"
RUNTIME_SCHEMA = "W12_PRIVATE_RUNTIME_RESEARCH_STAGE_v1"
STAGE_RELATIVE = Path("kairon_provider") / "w12_private_research"
MEMBERS = frozenset({
    "W12_MAI_PRIVATE_RESEARCH_STAGE.sqlite",
    "W12_MAI_IMPORT_RECEIPT.json",
    "w12_stage_private.py",
})
DB_MEMBER = "W12_MAI_PRIVATE_RESEARCH_STAGE.sqlite"
RECEIPT_MEMBER = "W12_MAI_IMPORT_RECEIPT.json"
MAX_ZIP = 5 * 1024 * 1024
MAX_UNPACKED = 12 * 1024 * 1024
TABLE_COUNTS = {
    "sheet": 21, "row_snapshot": 728, "seed": 6, "venue": 81,
    "research_version": 27, "route": 53, "editorial_action": 67,
    "evidence": 43, "event": 1,
}
SOURCE_CLASSES = {
    "seeds": 6, "venues": 81, "versions": 27, "routes": 53,
    "abstracts": 53, "channels": 53, "requirements": 53,
    "evidence": 43, "actions": 67, "cards": 53, "author_fields": 53,
}
SHA_PATTERN = re.compile(r"^[a-f0-9]{64}$")


class W12AdmissionError(ValueError):
    """A source failed the evidence, privacy or non-promotion gate."""


def _sha(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _pin(value: str, label: str) -> str:
    if not isinstance(value, str) or not SHA_PATTERN.fullmatch(value.lower()):
        raise W12AdmissionError(f"{label} must be pinned by SHA-256")
    return value.lower()


def _object(raw: bytes, kind: str) -> dict[str, Any]:
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise W12AdmissionError(f"invalid {kind} JSON") from exc
    if not isinstance(data, dict):
        raise W12AdmissionError(f"{kind} must be a JSON object")
    return data


def _stage(owner_root: Path) -> Path:
    root = Path(owner_root)
    if root.is_symlink():
        raise W12AdmissionError("user workspace cannot be a symlink")
    path = root / STAGE_RELATIVE
    if path.is_symlink():
        raise W12AdmissionError("private stage cannot be a symlink")
    return path


def _unpack(raw: bytes, expected_archive_sha256: str) -> tuple[bytes, dict[str, Any]]:
    if _sha(raw) != _pin(expected_archive_sha256, "archive SHA"):
        raise W12AdmissionError("W12 ZIP sha256 mismatch")
    if not 0 < len(raw) <= MAX_ZIP:
        raise W12AdmissionError("W12 ZIP exceeds bounded size")
    try:
        with ZipFile(BytesIO(raw)) as archive:
            infos = archive.infolist()
            if len(infos) != len(MEMBERS) or {x.filename for x in infos} != MEMBERS:
                raise W12AdmissionError("unexpected private ZIP member")
            if any(x.is_dir() or x.file_size > MAX_UNPACKED for x in infos):
                raise W12AdmissionError("unsafe ZIP member type/size")
            if sum(x.file_size for x in infos) > MAX_UNPACKED or archive.testzip() is not None:
                raise W12AdmissionError("W12 ZIP fails integrity/bounds")
            db = archive.read(DB_MEMBER)
            receipt = _object(archive.read(RECEIPT_MEMBER), "W12 receipt")
    except (BadZipFile, OSError, EOFError) as exc:
        raise W12AdmissionError("invalid W12 ZIP") from exc
    if receipt.get("schema") != RECEIPT_SCHEMA:
        raise W12AdmissionError("unsupported W12 source receipt")
    if receipt.get("db_table_counts") != TABLE_COUNTS:
        raise W12AdmissionError("private W12 table counts conflict")
    if receipt.get("declared_counts_verified") != SOURCE_CLASSES:
        raise W12AdmissionError("W12 source-card counts conflict")
    if receipt.get("source_sheet_count") != 21 or receipt.get("byte_count") != 251033:
        raise W12AdmissionError("W12 original byte/sheet counts conflict")
    if _sha(db) != _pin(receipt.get("private_store_sha256"), "SQLite SHA"):
        raise W12AdmissionError("SQLite bytes do not match source receipt")
    for key, expected in (
        ("admission_phase", "RESEARCH_STAGED_NOT_ARTIKL_ADMITTED"),
        ("full_text_qualified", 0),
        ("source_policy_qualified", 0),
        ("independent_article_promotions", 0),
        ("external_submission_events", 0),
        ("author_decisions_synthesized", 0),
    ):
        if receipt.get(key) != expected:
            raise W12AdmissionError(f"source receipt violates {key}")
    return db, {
        "schema": RUNTIME_SCHEMA,
        "status": "PRIVATE_RESEARCH_STAGED",
        "archive_sha256": _sha(raw),
        "source_sha256": _pin(receipt.get("source_sha256"), "original XLSX SHA"),
        "sqlite_sha256": _sha(db),
        "research_source_counts": TABLE_COUNTS,
        "research_claimed_counts": SOURCE_CLASSES,
        "read_depth_qualified_fulltext": 0,
        "editorial_route_policy_qualified": 0,
        "independent_articles_admitted": 0,
        "author_decisions_admitted": 0,
        "external_submissions": 0,
        "private_stage_not_authoritative_article_store": True,
    }


def _validate_sqlite(path: Path, source_sha: str) -> None:
    """Every source snapshot hash, cross-sheet FK and blocked gate is checked."""
    try:
        conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        try:
            conn.execute("PRAGMA query_only=ON")
            conn.execute("PRAGMA trusted_schema=OFF")
            if conn.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                raise W12AdmissionError("SQLite integrity failure")
            if conn.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise W12AdmissionError("broken W12 source foreign keys")
            for table, expected in TABLE_COUNTS.items():
                if conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0] != expected:
                    raise W12AdmissionError(f"W12 source table count conflict: {table}")
            row = conn.execute(
                "SELECT source_sha256,bytes,sheet_count,admission_phase,full_text_qualified FROM source"
            ).fetchone()
            if row != (source_sha, 251033, 21, "RESEARCH_STAGED_NOT_ARTIKL_ADMITTED", 0):
                raise W12AdmissionError("SQLite source witness mismatch")
            for sheet, number, src, digest, encoded in conn.execute(
                "SELECT sheet,excel_row,source_sha256,row_digest,fields_json FROM row_snapshot"
            ):
                if src != source_sha or _sha(encoded.encode("utf-8")) != digest:
                    raise W12AdmissionError(f"source row digest mismatch {sheet}:{number}")
                if not isinstance(json.loads(encoded), dict):
                    raise W12AdmissionError("row snapshot is not a field map")
            gates = (
                ("venue", "current_policy_qualified!=0", "journal falsely qualified"),
                ("research_version", "independent_article_certified!=0", "research version promoted to article"),
                ("seed", "author_authority!='INDAGO_RESEARCH_CANDIDATE'", "seed authority widened"),
                ("route",
                 "route_type!='POLICY_UNVERIFIED' OR source_policy_qualified!=0 OR external_send_status!='NOT_SENT'",
                 "editorial route falsely accepted/sent"),
                ("evidence",
                 "full_text_qualified!=0 OR read_depth NOT IN ('ABSTRACT','SECTIONS','INDEX_ONLY')",
                 "source read depth falsely promoted"),
                ("event",
                 "event_type!='SOURCE_BYTE_VERIFIED_AND_STAGED' OR phase!='RESEARCH_STAGED_NOT_ARTIKL_ADMITTED'",
                 "unexpected author/external event"),
            )
            for table, condition, reason in gates:
                if conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {condition}").fetchone()[0]:
                    raise W12AdmissionError(reason)
        finally:
            conn.close()
    except (sqlite3.DatabaseError, UnicodeError, json.JSONDecodeError) as exc:
        raise W12AdmissionError("unreadable W12 source SQLite") from exc


def _write_once(path: Path, content: bytes) -> None:
    fd, temp = tempfile.mkstemp(prefix=".w12-pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as fp:
            fp.write(content)
            fp.flush()
            os.fsync(fp.fileno())
        try:
            os.chmod(temp, 0o600)
        except OSError:
            pass  # A Windows operator must separately provision user ACLs.
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def _current(stage: Path) -> tuple[dict[str, Any], Path] | None:
    manifest_path, db_path = stage / "admission.json", stage / "stage.sqlite"
    if not manifest_path.exists() and not db_path.exists():
        return None
    if not manifest_path.is_file() or not db_path.is_file():
        raise W12AdmissionError("incomplete private import; operator recovery required")
    if manifest_path.is_symlink() or db_path.is_symlink():
        raise W12AdmissionError("private source stage cannot be symlinked")
    manifest = _object(manifest_path.read_bytes(), "runtime admission")
    if manifest.get("schema") != RUNTIME_SCHEMA or manifest.get("status") != "PRIVATE_RESEARCH_STAGED":
        raise W12AdmissionError("invalid research stage manifest")
    if _sha(db_path.read_bytes()) != _pin(manifest.get("sqlite_sha256"), "stage DB SHA"):
        raise W12AdmissionError("staged SQLite mutated")
    return manifest, db_path


def stage_private_research(
    source_zip_path: str | Path,
    owner_root: str | Path,
    *,
    expected_archive_sha256: str,
    expected_source_sha256: str,
) -> dict[str, Any]:
    """Trusted local import, only within the caller-validated owner's root."""
    source = Path(source_zip_path)
    if not source.is_file() or source.is_symlink() or not 0 < source.stat().st_size <= MAX_ZIP:
        raise W12AdmissionError("authorized bounded local ZIP path required")
    db, manifest = _unpack(source.read_bytes(), expected_archive_sha256)
    if manifest["source_sha256"] != _pin(expected_source_sha256, "original XLSX SHA"):
        raise W12AdmissionError("pinned original W12 XLSX does not match")
    stage = _stage(Path(owner_root))
    if stage.exists():
        previous = _current(stage)
        if previous:
            if previous[0].get("archive_sha256") != manifest["archive_sha256"] or previous[0].get("source_sha256") != manifest["source_sha256"]:
                raise W12AdmissionError("cannot overwrite immutable private source admission")
            return dict(previous[0])
    stage.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock = stage / ".import.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise W12AdmissionError("concurrent import or stale lock; operator recovery needed") from exc
    try:
        os.close(fd)
        with tempfile.TemporaryDirectory(prefix="w12-inspection-", dir=stage) as temp:
            db_path = Path(temp) / "inspect.sqlite"
            db_path.write_bytes(db)
            _validate_sqlite(db_path, manifest["source_sha256"])
        _write_once(stage / "stage.sqlite", db)
        _write_once(
            stage / "admission.json",
            json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8"),
        )
        return dict(manifest)
    finally:
        lock.unlink(missing_ok=True)


def research_stage_projection(
    owner_root: str | Path, *, offset: int = 0, limit: int = 100,
) -> dict[str, Any]:
    """User-private research candidates, NEVER ArticleOpportunity records.

    Sensitive author fields, contact details and any unpublished source text
    outside the selected route summary stay in the private SQLite, not the API.
    """
    if not isinstance(offset, int) or not 0 <= offset <= 100_000:
        raise W12AdmissionError("invalid offset")
    if not isinstance(limit, int) or not 1 <= limit <= 100:
        raise W12AdmissionError("limit must be in 1..100")
    current = _current(_stage(Path(owner_root)))
    if current is None:
        return {
            "status": "RUNTIME_IMPORT_PENDING",
            "source_available_in_private_drive": True,
            "imported_research_records": 0,
            "artikl_articles_admitted": 0,
            "editorial_routes_qualified": 0,
            "external_submissions": 0,
            "rows": [],
        }
    manifest, db_path = current
    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        conn.execute("PRAGMA query_only=ON")
        candidates = conn.execute("""
            SELECT r.route_id,r.excel_row,r.seed_id,r.version_id,r.venue_id,
                   v.canonical_name,r.route_type,r.external_send_status,
                   s.row_digest,s.fields_json
            FROM route AS r JOIN venue AS v ON r.venue_id=v.venue_id
            JOIN row_snapshot AS s ON s.sheet='06_МАРШРУТЫ' AND s.excel_row=r.excel_row
            ORDER BY r.route_id LIMIT ? OFFSET ?
        """, (limit, offset)).fetchall()
    finally:
        conn.close()
    rows = []
    for rid, excel_row, seed_id, variant, vid, journal, route_type, sent, digest, raw in candidates:
        fields = json.loads(raw)
        rows.append({
            "routeId": rid, "sourceRowRef": f"06_МАРШРУТЫ!{excel_row}",
            "sourceRowSha256": digest,
            "seedId": seed_id, "researchVersionId": variant,
            "venueId": vid, "journalName": journal,
            "workingTitle": str(fields.get("Название для авторской вычитки") or ""),
            "scholarlyOpponent": str(fields.get("Опубликованный противник") or ""),
            "researchPressure": str(fields.get("Давление журнала на идею") or ""),
            "evidenceDebt": str(fields.get("Главный научный или правовой долг") or ""),
            "routeType": route_type,
            "policyStatus": "POLICY_UNVERIFIED",
            "sourceClaimOnly": True, "readDepthStatus": "NO_QUALIFIED_FULLTEXT",
            "authorDecision": "HOLD", "articleStatus": "NOT_ARTIKL_ADMITTED",
            "externalSubmission": sent,
        })
    return {
        "status": manifest["status"], "schema": RUNTIME_SCHEMA,
        "sourceSha256": manifest["source_sha256"],
        "archiveSha256": manifest["archive_sha256"],
        "sourceRowsStaged": manifest["research_source_counts"]["row_snapshot"],
        "researchSeedCount": manifest["research_source_counts"]["seed"],
        "researchVenueCount": manifest["research_source_counts"]["venue"],
        "researchVersionCount": manifest["research_source_counts"]["research_version"],
        "researchRouteCount": manifest["research_source_counts"]["route"],
        "researchActionCount": manifest["research_source_counts"]["editorial_action"],
        "editorial_routes_qualified": 0, "artikl_articles_admitted": 0,
        "external_submissions": 0, "offset": offset, "limit": limit, "rows": rows,
    }
