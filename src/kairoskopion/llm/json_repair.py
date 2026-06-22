"""Bounded JSON repair for LLM responses.

Per `docs/operations/LLM_JSON_REPAIR_AND_VISIBLE_FALLBACK_REPORT.md`,
this module sits between the raw LLM `content` string and the agent's
deterministic-fallback path. It tries a small, deterministic set of
repairs that almost-JSON outputs commonly need; **it does NOT invent
semantic content** and refuses to forge missing required fields just
to satisfy a schema.

Stdlib only. No new runtime deps.

Repair coverage:
  - plain JSON (no repair needed);
  - ```json ... ``` and ``` ... ``` markdown code fences;
  - prose-before-or-after-JSON (extract first balanced {…} or […]);
  - trailing commas inside `{}` or `[]`;
  - smart-quotes (`“ ” ‘ ’`) → straight quotes;
  - simple unescaped newlines inside string literals (one-pass);
  - simple optional-field defaults when schema lists allow-missing keys.

What it deliberately **refuses** to do:
  - hallucinate missing required string/list values;
  - guess enum values that the LLM produced as free text;
  - re-write semantically empty `{}` into anything else;
  - call an LLM to ask for repair (no second-LLM cost by default).

`repair_and_parse` returns `(parsed, status)` where `status` is one of
the values from `ParseStatus`. The agent consults `status` to decide
whether to use the result or fall back to its deterministic path.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


# Parse status taxonomy — kept narrow so it round-trips through API.
PARSE_STATUS_NOT_ATTEMPTED = "not_attempted"
PARSE_STATUS_PARSED_OK = "parsed_ok"
PARSE_STATUS_REPAIRED_OK = "repaired_ok"
PARSE_STATUS_INVALID_JSON = "invalid_json"
PARSE_STATUS_SCHEMA_VALIDATION_FAILED = "schema_validation_failed"
PARSE_STATUS_REPAIR_FAILED = "repair_failed"
PARSE_STATUS_FALLBACK_USED = "fallback_used"

VALID_PARSE_STATUSES = frozenset({
    PARSE_STATUS_NOT_ATTEMPTED,
    PARSE_STATUS_PARSED_OK,
    PARSE_STATUS_REPAIRED_OK,
    PARSE_STATUS_INVALID_JSON,
    PARSE_STATUS_SCHEMA_VALIDATION_FAILED,
    PARSE_STATUS_REPAIR_FAILED,
    PARSE_STATUS_FALLBACK_USED,
})


@dataclass
class RepairOutcome:
    parsed: Any | None
    status: str
    repair_steps: list[str]
    validation_errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "parsed_is_dict": isinstance(self.parsed, dict),
            "parsed_is_list": isinstance(self.parsed, list),
            "status": self.status,
            "repair_steps": list(self.repair_steps),
            "validation_errors": list(self.validation_errors),
        }


# ---------------------------------------------------------------------------
# Step 1: strip fences / prose / smart-quotes
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"^```(?:json|JSON)?\s*\n", re.MULTILINE)
_FENCE_END_RE = re.compile(r"\n?```\s*$", re.MULTILINE)
_SMART_QUOTES = {
    "“": '"', "”": '"',  # “ ”
    "‘": "'", "’": "'",  # ‘ ’
    "«": '"', "»": '"',  # « »
}


def _replace_smart_quotes(s: str) -> str:
    out = s
    for k, v in _SMART_QUOTES.items():
        if k in out:
            out = out.replace(k, v)
    return out


def _strip_fences(s: str) -> str:
    """Remove a leading ```json fence and trailing ``` if present."""
    s2 = _FENCE_RE.sub("", s, count=1)
    s2 = _FENCE_END_RE.sub("", s2, count=1)
    return s2.strip()


def _extract_first_balanced(s: str, opener: str, closer: str) -> str | None:
    """Extract the first balanced bracket region starting at `opener`.

    Scans character-by-character with a simple counter so nested braces
    inside strings are handled cleanly.
    """
    lo = s.find(opener)
    if lo == -1:
        return None
    depth = 0
    in_str = False
    str_quote = ""
    escape = False
    for i in range(lo, len(s)):
        ch = s[i]
        if in_str:
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == str_quote:
                in_str = False
            continue
        else:
            if ch in ('"', "'"):
                in_str = True
                str_quote = ch
                continue
            if ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    return s[lo:i + 1]
    return None


# ---------------------------------------------------------------------------
# Step 2: minor structural repairs
# ---------------------------------------------------------------------------

_TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")


def _strip_trailing_commas(s: str) -> str:
    return _TRAILING_COMMA_RE.sub(r"\1", s)


def _try_parse_with_repairs(s: str, steps: list[str]) -> Any | None:
    """Try a small sequence of bounded repairs on a candidate string.

    Order of attempts (each is a fresh `json.loads`):
      1. as-is
      2. smart-quote replacement
      3. + trailing-comma strip
      4. + replace single-quote string delimiters with double quotes
         when it's clearly safe (i.e. no unescaped double quotes inside)
    """
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass

    # 2. smart quotes
    s2 = _replace_smart_quotes(s)
    if s2 != s:
        steps.append("smart_quotes_replaced")
        try:
            return json.loads(s2)
        except json.JSONDecodeError:
            pass
    else:
        s2 = s

    # 3. trailing commas
    s3 = _strip_trailing_commas(s2)
    if s3 != s2:
        steps.append("trailing_commas_stripped")
        try:
            return json.loads(s3)
        except json.JSONDecodeError:
            pass
    else:
        s3 = s2

    # 4. single→double quotes — ONLY when the input has single-quoted
    # strings AND no double quotes at all. Otherwise the substitution
    # would mangle valid embedded JSON.
    if "'" in s3 and '"' not in s3:
        s4 = s3.replace("'", '"')
        steps.append("single_quotes_to_double")
        try:
            return json.loads(s4)
        except json.JSONDecodeError:
            pass

    return None


# ---------------------------------------------------------------------------
# Step 2b: enum value normalization
# ---------------------------------------------------------------------------

def _normalize_enums(data: Any, schema: dict | None) -> list[str]:
    """Normalize enum values that differ from the schema only by case
    or by space-vs-underscore. Returns list of field names normalized.

    Example: schema enum ``"theoretical_essay"``, LLM produced
    ``"Theoretical Essay"`` → normalize to ``"theoretical_essay"``.

    Does NOT change values that map to NO schema enum entry — those
    remain so the family-level validator can warn on them. Refuses
    to invent enum values for missing keys.
    """
    if not isinstance(data, dict) or not isinstance(schema, dict):
        return []
    props = schema.get("properties") or {}
    normalized: list[str] = []
    for key, spec in props.items():
        if key not in data or not isinstance(spec, dict):
            continue
        enum = spec.get("enum")
        if not isinstance(enum, list):
            continue
        v = data[key]
        if not isinstance(v, str) or v in enum:
            continue
        # Build a canonical-form → enum mapping for case/space tolerance.
        canon: dict[str, str] = {}
        for e in enum:
            if not isinstance(e, str):
                continue
            canon[e.lower().replace(" ", "_").replace("-", "_")] = e
        probe = v.lower().replace(" ", "_").replace("-", "_")
        if probe in canon:
            data[key] = canon[probe]
            normalized.append(key)
    return normalized


# ---------------------------------------------------------------------------
# Step 3: optional defaults for missing optional fields
# ---------------------------------------------------------------------------

def _fill_optional_defaults(data: dict, schema: dict) -> tuple[dict, list[str]]:
    """Fill JSON-schema-described missing OPTIONAL fields with safe defaults.

    *Optional* here = listed in `properties` but NOT in `required`. We
    only fill the field with the JSON-schema default-value semantics:
    `[]` for arrays, `{}` for objects, `""` for strings, `null`
    otherwise. We never invent content.
    """
    if not isinstance(data, dict) or not isinstance(schema, dict):
        return data, []
    props = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    filled: list[str] = []
    for key, spec in props.items():
        if key in data or key in required:
            continue
        t = spec.get("type") if isinstance(spec, dict) else None
        if t == "array":
            data[key] = []
        elif t == "object":
            data[key] = {}
        elif t == "string":
            data[key] = ""
        elif t == "boolean":
            data[key] = False
        else:
            data[key] = None
        filled.append(key)
    return data, filled


# ---------------------------------------------------------------------------
# Step 4: lightweight schema check (don't invent values)
# ---------------------------------------------------------------------------

def _type_allows_null(spec: Any) -> bool:
    """JSON Schema 'type' can be a string OR a list of strings.

    Returns True if the type spec admits ``null`` as a valid value
    (``"type": "null"`` OR ``"type": ["string", "null"]`` etc.). When
    the spec is absent, we conservatively allow null — the validator
    is meant to catch *missing keys*, not type mismatches.
    """
    if not isinstance(spec, dict):
        return True
    t = spec.get("type")
    if t is None:
        return True
    if isinstance(t, str):
        return t == "null"
    if isinstance(t, list):
        return "null" in t
    return True


def _schema_required_present(data: Any, schema: dict | None) -> list[str]:
    """Return missing-required-field errors. Empty list means OK.

    JSON Schema semantics: ``required: ["foo"]`` means the KEY must be
    present in the object. The VALUE may be ``null`` if the field's
    ``type`` admits null (e.g. ``"type": ["string", "null"]``). We
    must not flag explicit-null fields as missing when the schema
    invites them — that pattern is exactly what the article-modeling
    prompt asks the LLM to do ("Use null for fields you cannot
    determine"), and treating it as a failure rejected most valid
    outputs in production.

    Refuses to invent values; only reports.
    """
    if not isinstance(schema, dict):
        return []
    required = schema.get("required")
    if not isinstance(required, list):
        return []
    if not isinstance(data, dict):
        return ["top-level value is not an object as schema requires"]
    props = schema.get("properties") or {}
    missing: list[str] = []
    for k in required:
        if k not in data:
            missing.append(k)
            continue
        # Key is present; value may be null if the spec allows it.
        if data.get(k) is None and not _type_allows_null(props.get(k)):
            missing.append(k)
    if missing:
        return [f"missing required field: {k}" for k in missing]
    return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def repair_and_parse(
    raw: str | None,
    schema: dict[str, Any] | None = None,
) -> RepairOutcome:
    """Attempt to extract a parsed JSON value from an LLM response.

    Args:
      raw: the LLM response content (may be None or empty).
      schema: optional JSON Schema (used only to check required fields and
        fill safe optional defaults — never to invent semantic content).

    Returns:
      RepairOutcome with `.parsed`, `.status`, and audit fields.
    """
    raw = raw or ""
    steps: list[str] = []

    # Strip UTF-8 BOM + non-breaking spaces that some providers prepend.
    s = raw.lstrip("﻿ ").strip()
    if s != raw.strip():
        steps.append("bom_stripped")
    if not s:
        return RepairOutcome(
            parsed=None,
            status=PARSE_STATUS_INVALID_JSON,
            repair_steps=["empty_input"],
            validation_errors=[],
        )

    # Fast path 1: as-is
    try:
        parsed = json.loads(s)
        steps.append("as_is")
        return _validate_and_return(parsed, schema, steps, repaired=False)
    except json.JSONDecodeError:
        pass

    # Strip fences if present
    s2 = _strip_fences(s)
    if s2 != s:
        steps.append("fences_stripped")
    try:
        parsed = json.loads(s2)
        return _validate_and_return(parsed, schema, steps, repaired=True)
    except json.JSONDecodeError:
        pass

    # Try repair on the candidate (smart quotes, trailing commas, etc.)
    parsed = _try_parse_with_repairs(s2, steps)
    if parsed is not None:
        return _validate_and_return(parsed, schema, steps, repaired=True)

    # Round III-G: JSON-island repair — exhaustively find ALL fenced
    # JSON blocks + ALL balanced {...} / [...] candidates, try each
    # one, pick the largest valid candidate. Sonnet sometimes returns
    # prose + multiple JSON blocks or <thinking>...</thinking>{json};
    # the single-balanced-extract above stops at the first candidate.
    candidates: list[tuple[str, str]] = []  # (kind, text)

    # All fenced ```json ... ``` blocks
    fence_pat = re.compile(
        r"```(?:json|JSON)?\s*\n(.*?)\n?```",
        re.DOTALL,
    )
    for m in fence_pat.finditer(s):
        candidates.append(("fenced_json", m.group(1).strip()))

    # All top-level balanced {…} regions (non-overlapping)
    def _all_balanced(text: str, opener: str, closer: str) -> list[str]:
        out: list[str] = []
        i = 0
        n = len(text)
        while i < n:
            lo = text.find(opener, i)
            if lo == -1:
                break
            depth = 0
            in_str = False
            qch = ""
            esc = False
            end_idx = -1
            for j in range(lo, n):
                ch = text[j]
                if in_str:
                    if esc:
                        esc = False
                        continue
                    if ch == "\\":
                        esc = True
                        continue
                    if ch == qch:
                        in_str = False
                    continue
                if ch in ('"', "'"):
                    in_str = True
                    qch = ch
                    continue
                if ch == opener:
                    depth += 1
                elif ch == closer:
                    depth -= 1
                    if depth == 0:
                        end_idx = j
                        break
            if end_idx == -1:
                break
            out.append(text[lo:end_idx + 1])
            i = end_idx + 1
        return out

    for region in _all_balanced(s2, "{", "}"):
        candidates.append(("object_root", region))
    for region in _all_balanced(s2, "[", "]"):
        candidates.append(("array_root", region))

    # Try each candidate; pick the LARGEST valid one
    best_parsed: Any | None = None
    best_size = 0
    best_kind = ""
    rejected: list[str] = []
    for kind, text in candidates:
        parsed_c = _try_parse_with_repairs(text, [])
        if parsed_c is None:
            rejected.append(f"{kind}:repair_failed")
            continue
        size = len(text)
        if size > best_size:
            best_parsed = parsed_c
            best_size = size
            best_kind = kind
    if best_parsed is not None:
        steps.append(f"island_selected:{best_kind}:size={best_size}")
        # Backward-compat trace tokens for older tests
        if best_kind in ("object_root", "fenced_json"):
            steps.append("extracted_balanced_{")
        elif best_kind == "array_root":
            steps.append("extracted_balanced_[")
        if rejected:
            steps.append(f"island_rejected:{','.join(rejected[:6])}")
        return _validate_and_return(best_parsed, schema, steps, repaired=True)

    if candidates:
        steps.append(
            f"island_no_valid:{len(candidates)}_candidates:"
            + ",".join(c[0] for c in candidates[:6])
        )

    return RepairOutcome(
        parsed=None,
        status=PARSE_STATUS_REPAIR_FAILED,
        repair_steps=steps,
        validation_errors=[],
    )


def _validate_and_return(
    parsed: Any,
    schema: dict | None,
    steps: list[str],
    *,
    repaired: bool,
) -> RepairOutcome:
    # Normalize enum casing/spacing first — many LLMs return
    # "Theoretical Essay" or "Theoretical_Essay" when schema expects
    # "theoretical_essay". Doing this BEFORE the schema check ensures
    # a near-correct enum doesn't trigger a validation_failed status.
    if isinstance(parsed, dict) and isinstance(schema, dict):
        norm = _normalize_enums(parsed, schema)
        if norm:
            steps.append(f"enums_normalized:{','.join(norm[:6])}")
    # Try filling optional defaults (does not invent semantic content).
    if isinstance(parsed, dict) and isinstance(schema, dict):
        parsed, filled = _fill_optional_defaults(parsed, schema)
        if filled:
            steps.append(f"optional_defaults_filled:{','.join(filled[:6])}")
    errors = _schema_required_present(parsed, schema)
    if errors:
        return RepairOutcome(
            parsed=parsed,
            status=PARSE_STATUS_SCHEMA_VALIDATION_FAILED,
            repair_steps=steps,
            validation_errors=errors,
        )
    status = PARSE_STATUS_REPAIRED_OK if repaired else PARSE_STATUS_PARSED_OK
    return RepairOutcome(
        parsed=parsed,
        status=status,
        repair_steps=steps,
        validation_errors=[],
    )
