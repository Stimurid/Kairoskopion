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
    TargetWorldSnapshot,
)
from .adapter import pressure_pack_from_diagnostics

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
    "TargetWorldSnapshot",
    "pressure_pack_from_diagnostics",
]
