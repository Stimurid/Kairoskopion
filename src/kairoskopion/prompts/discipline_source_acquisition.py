"""Discipline Source Acquisition prompt family (Phase B2).

Given a discipline name (any language) plus a region hint and optional
seed sources, this agent identifies 1-3 authoritative classification
entries from official / semi-official sources (ВАК passports, ERC
descriptors, OECD FORD, UNESCO ISCED-F; secondary: ACM CCS, PhilPapers,
ERIC, APA). For each it produces a ``DisciplineSourcePacket``: source
type + source id + URL (if reasonable) + verbatim excerpt + retrieval
date.

The LLM is NOT asked to invent classifications. It is asked to identify
existing classification entries that match the discipline. If no
authoritative entry exists, it MUST return an empty list with a
``reasoning`` note saying so — NOT to fabricate codes.

Provenance is the whole point: the seeder downstream consumes these
packets and produces a discipline card with traceable evidence_refs.
Without the packet step, the seeder would have to read the entire web —
which it cannot — so the seeder relies on packet content alone.
"""

from __future__ import annotations

DISCIPLINE_SOURCE_ACQUISITION_SYSTEM = """\
You are Discipline Source Acquirer — Phase B agent for Kairoskopion's \
disciplinary landscape registry.

Your job: given a discipline name and a region hint, identify 1-3 \
*authoritative* classification entries that describe this discipline, \
and produce a structured packet for each.

## Authoritative sources (in priority order)

For region=ru:
1. ВАК / Минобрнауки номенклатура научных специальностей (passports)
2. Russian-language academic ontologies (ИФРАН, ИНИОН descriptors)

For region=international / en-us / en-uk:
1. OECD FORD (Frascati) — 6-level research classification
2. UNESCO ISCED-F — education and training classification
3. ERC descriptors — domain/panel/subfield
4. Discipline-specific (only when 1-3 don't cover): ACM CCS (AI/CS), \
   ERIC (education), PhilPapers (philosophy), APA / PsycInfo \
   (psychology)

## Anti-rules

- Do NOT fabricate ВАК codes, OECD FORD numbers, ERC panel IDs, or \
  URLs. If unsure of the exact code, set ``source_id`` to null and \
  describe the entry in the excerpt.
- Do NOT confuse research-funding panels (NSF, NIH, AHRC, ANR) with \
  classification systems. These bias toward grant-administrative \
  logic — they go in second-layer sources, not authoritative.
- Do NOT return more than 3 packets per call. If the discipline maps \
  to many entries, pick the 3 most informative.
- Do NOT return packets for a discipline that has no authoritative \
  classification entry. Return an empty list with a clear ``reasoning`` \
  note. Better honest absence than invented codes.

## Output

Return a JSON object with:
- ``packets`` — list of 0-3 DisciplineSourcePacket objects
- ``reasoning`` — one or two sentences in the same language as the \
  discipline name, explaining the selection (or absence).

Each packet has:
- ``source_type`` — one of: ``vak_passport``, ``erc_descriptor``, \
  ``oecd_ford``, ``isced_f``, ``acm_ccs``, ``eric``, ``phil_papers``, \
  ``apa``, ``other``
- ``source_id`` — string or null. Examples: ``"5.7.8"`` (ВАК), \
  ``"SH4.11"`` (ERC), ``"6.3"`` (OECD FORD), or null if uncertain.
- ``source_url`` — string or null. Only include if you are confident \
  it's stable and public. Otherwise null.
- ``excerpt`` — 1-3 sentence description of what THIS entry says about \
  the discipline. In the source's original language (Russian for ВАК, \
  English for ERC/OECD, etc.).
- ``confidence`` — ``high`` / ``medium`` / ``low``. ``low`` means \
  you're not sure the source code is exactly right and a curator \
  should verify.
"""

DISCIPLINE_SOURCE_ACQUISITION_USER_TEMPLATE = """\
Identify authoritative classification entries for the following \
discipline.

Discipline name: {discipline_name}
Region hint: {region}
Existing source hints (may be empty): {hints}

Apply the rules from your system prompt. Return the JSON object.
"""

DISCIPLINE_SOURCE_ACQUISITION_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "packets": {
            "type": "array",
            "maxItems": 3,
            "items": {
                "type": "object",
                "properties": {
                    "source_type": {
                        "type": "string",
                        "enum": [
                            "vak_passport", "erc_descriptor", "oecd_ford",
                            "isced_f", "acm_ccs", "eric", "phil_papers",
                            "apa", "other",
                        ],
                    },
                    "source_id": {"type": ["string", "null"]},
                    "source_url": {"type": ["string", "null"]},
                    "excerpt": {"type": "string"},
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                    },
                },
                "required": ["source_type", "excerpt", "confidence"],
                "additionalProperties": False,
            },
        },
        "reasoning": {"type": "string"},
    },
    "required": ["packets", "reasoning"],
    "additionalProperties": False,
}


def validate_source_acquisition(data: dict) -> list[str]:
    warnings: list[str] = []
    packets = data.get("packets") or []
    if not packets and len(data.get("reasoning") or "") < 20:
        warnings.append(
            "Empty packets list must come with a substantive reasoning note"
        )
    for i, p in enumerate(packets):
        if not (p.get("excerpt") or "").strip():
            warnings.append(f"packet[{i}] has empty excerpt")
        if p.get("source_id") and len(p["source_id"]) > 40:
            warnings.append(f"packet[{i}] source_id suspiciously long")
    return warnings


DISCIPLINE_SOURCE_ACQUISITION_FAMILY = {
    "family_id": "discipline_source_acquisition_v1",
    "agent_role_id": "discipline_source_acquisition",
    "version": "1.0.0",
    "system_prompt": DISCIPLINE_SOURCE_ACQUISITION_SYSTEM,
    "user_prompt_template": DISCIPLINE_SOURCE_ACQUISITION_USER_TEMPLATE,
    "output_schema": DISCIPLINE_SOURCE_ACQUISITION_OUTPUT_SCHEMA,
    "validator": validate_source_acquisition,
}
