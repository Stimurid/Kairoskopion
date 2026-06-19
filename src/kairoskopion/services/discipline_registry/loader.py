"""Disciplinary landscape registry loader.

Loads:
- ``data/disciplinary_landscape/seeds/*.jsonl`` — curated LLM-draft
  records that ship with the repo.
- ``data/disciplinary_landscape/registry/disciplinary_landscape.jsonl``
  — append-only live registry that accrues candidates from
  ``semantic_profiler`` and refinements from
  ``DisciplineRegistryRefinerAgent``.

Region filter and cheap keyword-matcher live here; LLM-driven matching
lives in ``agents/discipline_matcher.py``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable

from .model import DisciplineModel


# ---------------------------------------------------------------------------
# Default paths
# ---------------------------------------------------------------------------

def _repo_root() -> Path:
    # src/kairoskopion/services/discipline_registry/loader.py
    #   → src/kairoskopion/services/discipline_registry
    #   → src/kairoskopion/services
    #   → src/kairoskopion
    #   → src
    #   → <repo root>
    return Path(__file__).resolve().parents[4]


def _default_data_dir() -> Path:
    env = os.environ.get("KAIROSKOPION_DISCIPLINARY_LANDSCAPE_DIR")
    if env:
        return Path(env)
    return _repo_root() / "data" / "disciplinary_landscape"


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class DisciplineRegistry:
    """In-memory registry. Loaded once; mutations append to disk via
    the writer methods (so seed files stay immutable and live updates
    go to ``registry/disciplinary_landscape.jsonl``)."""

    def __init__(self, disciplines: Iterable[DisciplineModel] | None = None):
        self._by_id: dict[str, DisciplineModel] = {}
        for d in disciplines or ():
            self._by_id[d.discipline_id] = d

    # -- reads ---------------------------------------------------------

    def __len__(self) -> int:
        return len(self._by_id)

    def __contains__(self, discipline_id: str) -> bool:
        return discipline_id in self._by_id

    def get(self, discipline_id: str) -> DisciplineModel | None:
        return self._by_id.get(discipline_id)

    def all(self) -> list[DisciplineModel]:
        return list(self._by_id.values())

    def by_region(self, region: str) -> list[DisciplineModel]:
        """Filter by ``region``. ``'auto'`` returns everything.
        Russian-mapped international cards (``international_mapping``)
        are returned when ``region='ru'`` AS WELL — cross-region
        matching is supported from day 1.
        """
        if region == "auto":
            return self.all()
        out = [d for d in self._by_id.values() if d.region == region]
        if region == "ru":
            # Include international cards that explicitly map to a
            # Russian counterpart, so a Russian-language paper is not
            # blind to international neighbours.
            for d in self._by_id.values():
                if d.region != "ru" and d.discipline_id not in {x.discipline_id for x in out}:
                    if any(
                        m.startswith("ru-")
                        for m in d.international_mapping
                    ):
                        out.append(d)
        return out

    def candidates_keyword(
        self,
        text: str,
        region: str = "auto",
        limit: int = 25,
    ) -> list[DisciplineModel]:
        """Cheap pre-filter — used by the LLM matcher to narrow the
        context window before a final LLM-driven match. Scores by
        substring overlap on:
        - display_names (both ru/en)
        - aliases
        - legitimate_objects
        - ontologies
        - paradigm (first 400 chars)

        NOT a final match. Designed to over-fetch (recall over
        precision). The matcher agent does final selection.
        """
        if not text.strip():
            return []
        haystack = text.lower()
        pool = self.by_region(region)
        scored: list[tuple[int, DisciplineModel]] = []
        for d in pool:
            score = 0
            for name in d.display_names.values():
                if name and name.lower() in haystack:
                    score += 5
            for alias in d.aliases:
                if alias and alias.lower() in haystack:
                    score += 3
            for obj in d.legitimate_objects:
                if obj and obj.lower() in haystack:
                    score += 2
            for ont in d.ontologies:
                if ont and ont.lower() in haystack:
                    score += 2
            if d.paradigm:
                # Take first 80 chars of paradigm as a coarse signal —
                # rarely substring-matches outside very obvious cases.
                snippet = d.paradigm[:80].lower()
                if snippet and snippet[:20] in haystack:
                    score += 1
            if score > 0:
                scored.append((score, d))
        scored.sort(key=lambda x: (-x[0], x[1].discipline_id))
        return [d for _, d in scored[:limit]]

    def adjacent_of(self, discipline_id: str) -> list[DisciplineModel]:
        """Walk one hop along ``adjacent`` + ``international_mapping``.
        Useful for expanding the matcher context after the first
        candidate set."""
        seed = self._by_id.get(discipline_id)
        if seed is None:
            return []
        ids = set(seed.adjacent) | set(seed.international_mapping)
        return [self._by_id[i] for i in ids if i in self._by_id]

    # -- writes --------------------------------------------------------

    def add(self, discipline: DisciplineModel) -> None:
        self._by_id[discipline.discipline_id] = discipline


# ---------------------------------------------------------------------------
# JSONL I/O
# ---------------------------------------------------------------------------

def _iter_jsonl(path: Path) -> Iterable[dict]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON in {path}:{i}: {exc}"
                ) from exc


def load_registry_from_paths(
    seed_paths: Iterable[Path],
    live_registry_path: Path | None = None,
) -> DisciplineRegistry:
    """Load seed JSONL files (immutable, ship-with-repo) + the live
    registry JSONL (mutable, may accrue candidate records).

    Later occurrences win — so a confirmed card in the live registry
    can override an llm_draft from the seed. This is how the curator
    workflow propagates without rewriting seed files.
    """
    by_id: dict[str, DisciplineModel] = {}
    for p in seed_paths:
        for record in _iter_jsonl(p):
            d = DisciplineModel.from_dict(record)
            by_id[d.discipline_id] = d
    if live_registry_path is not None:
        for record in _iter_jsonl(live_registry_path):
            d = DisciplineModel.from_dict(record)
            by_id[d.discipline_id] = d
    return DisciplineRegistry(by_id.values())


def load_default_registry() -> DisciplineRegistry:
    """Convenience for callers — loads all ``seeds/*.jsonl`` and the
    live registry at the default location."""
    root = _default_data_dir()
    seeds_dir = root / "seeds"
    registry_path = root / "registry" / "disciplinary_landscape.jsonl"
    seed_paths = sorted(seeds_dir.glob("*.jsonl")) if seeds_dir.exists() else []
    return load_registry_from_paths(seed_paths, registry_path)
