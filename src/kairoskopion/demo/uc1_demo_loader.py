"""Load and validate the UC-1 demo pack from fixture directory.

The demo pack contains all inputs needed to run the full UC-1 pipeline
offline without LLM or network access:

- draft_article.md — prototype scholarly article
- scenario.json — demo scenario metadata
- venue_seeds.json — 5 synthetic venue seed records
- venue_guidelines/*.md — per-venue author guidelines
- corpus/*.json — per-venue published article corpus samples
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEMO_PACK_DIR = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "uc1_demo_pack"


@dataclass
class UC1DemoPack:
    """Loaded UC-1 demo pack with all inputs validated."""

    draft_text: str
    scenario: dict[str, Any]
    venue_seeds: list[dict[str, Any]]
    venue_guidelines: dict[str, str]
    corpus: dict[str, list[dict[str, Any]]]
    pack_dir: Path
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def venue_names(self) -> list[str]:
        return [v["name"] for v in self.venue_seeds]

    def to_dict(self) -> dict[str, Any]:
        return {
            "draft_text_length": len(self.draft_text),
            "scenario": self.scenario,
            "venue_count": len(self.venue_seeds),
            "venue_names": self.venue_names(),
            "guidelines_count": len(self.venue_guidelines),
            "corpus_files": list(self.corpus.keys()),
            "corpus_article_counts": {
                k: len(v) for k, v in self.corpus.items()
            },
            "is_valid": self.is_valid,
            "errors": self.errors,
            "pack_dir": str(self.pack_dir),
        }


def load_uc1_demo_pack(pack_dir: Path | None = None) -> UC1DemoPack:
    """Load and validate the UC-1 demo pack.

    Args:
        pack_dir: Path to the demo pack directory. Defaults to the
                  bundled fixture at tests/fixtures/uc1_demo_pack/.

    Returns:
        UC1DemoPack with all loaded data and any validation errors.
    """
    root = pack_dir or DEMO_PACK_DIR
    errors: list[str] = []

    draft_text = _load_text(root / "draft_article.md", "draft_article.md", errors)
    scenario = _load_json(root / "scenario.json", "scenario.json", errors)
    venue_seeds = _load_json(root / "venue_seeds.json", "venue_seeds.json", errors)

    if not isinstance(venue_seeds, list):
        errors.append("venue_seeds.json must be a JSON array")
        venue_seeds = []

    venue_guidelines = _load_guidelines(root / "venue_guidelines", errors)
    corpus = _load_corpus(root / "corpus", errors)

    if draft_text and len(draft_text) < 200:
        errors.append(f"draft_article.md too short ({len(draft_text)} chars, expected >= 200)")

    if venue_seeds and len(venue_seeds) < 2:
        errors.append(f"venue_seeds.json has only {len(venue_seeds)} venues, expected >= 2")

    for i, seed in enumerate(venue_seeds):
        if "name" not in seed:
            errors.append(f"venue_seeds[{i}] missing 'name' field")

    return UC1DemoPack(
        draft_text=draft_text or "",
        scenario=scenario or {},
        venue_seeds=venue_seeds,
        venue_guidelines=venue_guidelines,
        corpus=corpus,
        pack_dir=root,
        errors=errors,
    )


def _load_text(path: Path, label: str, errors: list[str]) -> str | None:
    if not path.exists():
        errors.append(f"Missing required file: {label}")
        return None
    return path.read_text(encoding="utf-8")


def _load_json(path: Path, label: str, errors: list[str]) -> Any:
    if not path.exists():
        errors.append(f"Missing required file: {label}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in {label}: {e}")
        return None


def _load_guidelines(guidelines_dir: Path, errors: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    if not guidelines_dir.exists():
        errors.append("Missing venue_guidelines/ directory")
        return result
    for f in sorted(guidelines_dir.iterdir()):
        if f.suffix in (".md", ".html", ".txt"):
            result[f.stem] = f.read_text(encoding="utf-8")
    if not result:
        errors.append("No guideline files found in venue_guidelines/")
    return result


def _load_corpus(corpus_dir: Path, errors: list[str]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    if not corpus_dir.exists():
        errors.append("Missing corpus/ directory")
        return result
    for f in sorted(corpus_dir.iterdir()):
        if f.suffix == ".json":
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    result[f.stem] = data
                else:
                    errors.append(f"corpus/{f.name} must be a JSON array")
            except json.JSONDecodeError as e:
                errors.append(f"Invalid JSON in corpus/{f.name}: {e}")
    return result
