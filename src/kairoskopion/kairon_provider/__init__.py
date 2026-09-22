"""Kairoskopion binding for the canonical ARTIKL.KAIRON provider contract.

This package is deliberately additive. It does not replace the existing Case
pipeline; it exposes a normalized boundary that can be consumed by Kairon while
the older internal entities are gradually retyped.
"""

from .models import (
    ArtiklStatePointer,
    CorpusArtifact,
    CorpusArtifactManifest,
    EditorScientificProfile,
    KaironProviderRequest,
    KaironProviderResponse,
    RoundTripComparison,
    TargetPressureItem,
    TargetPressurePack,
    TargetModelBundle,
    TargetWorldSnapshot,
)
from .adapter import pressure_pack_from_diagnostics
from .target_world import build_target_world_snapshot
from .round_trip import compare_round_trip

__all__ = [
    "ArtiklStatePointer",
    "CorpusArtifact",
    "CorpusArtifactManifest",
    "EditorScientificProfile",
    "KaironProviderRequest",
    "KaironProviderResponse",
    "RoundTripComparison",
    "TargetPressureItem",
    "TargetPressurePack",
    "TargetModelBundle",
    "TargetWorldSnapshot",
    "pressure_pack_from_diagnostics",
    "build_target_world_snapshot",
    "compare_round_trip",
]
