"""Disciplinary landscape registry (Phase B).

A discipline is modelled as a **working tool for downstream agents**,
not an encyclopedia entry. The registry holds seed cards (LLM drafts
from official sources: ВАК passports, ERC descriptors, OECD FORD,
ISCED-F) and continuously-added candidates surfaced by
``semantic_profiler`` on real cases.

Public surface:

- ``DisciplineModel`` — dataclass mirroring
  ``data/disciplinary_landscape/schema/discipline_model.schema.json``.
- ``DisciplineRegistry`` — loader, region filter, matcher helpers.
- ``DisciplineSourcePacket`` — provenance container the seeder consumes
  before producing a DisciplineCard.

NOTHING here changes LLM provider params. The registry is consumed by
agents that may or may not call the LLM — its responsibility is data,
not orchestration.
"""

from .source_packet import DisciplineSourcePacket
from .model import DisciplineModel, KeyAuthor, EvidenceRef
from .loader import (
    DisciplineRegistry,
    load_default_registry,
    load_registry_from_paths,
)

__all__ = [
    "DisciplineModel",
    "DisciplineRegistry",
    "DisciplineSourcePacket",
    "EvidenceRef",
    "KeyAuthor",
    "load_default_registry",
    "load_registry_from_paths",
]
