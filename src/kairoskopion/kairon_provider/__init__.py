"""Kairoskopion binding for the canonical ARTIKL.KAIRON provider contract.

This package is deliberately additive. It does not replace the existing Case
pipeline; it exposes a normalized boundary that can be consumed by Kairon while
the older internal entities are gradually retyped.
"""

from .models import (
    ArtiklArticleProjection,
    ArtiklStatePointer,
    CorpusArtifact,
    CorpusArtifactManifest,
    EditorScientificProfile,
    KaironProviderRequest,
    KaironTransitionDecision,
    KaironProviderResponse,
    RoundTripComparison,
    TargetPressureItem,
    TargetPressurePack,
    TargetModelBundle,
    TargetWorldSnapshot,
)
from .adapter import pressure_pack_from_diagnostics
from .artikl_projection import bind_artikl_projection
from .target_world import build_target_world_snapshot
from .round_trip import compare_round_trip
from .reconcile import reconcile_target_pressure_pack, derive_transition_class
from .transition import propose_transition

__all__ = [
    "ArtiklArticleProjection",
    "ArtiklStatePointer",
    "CorpusArtifact",
    "CorpusArtifactManifest",
    "EditorScientificProfile",
    "KaironProviderRequest",
    "KaironTransitionDecision",
    "KaironProviderResponse",
    "RoundTripComparison",
    "TargetPressureItem",
    "TargetPressurePack",
    "TargetModelBundle",
    "TargetWorldSnapshot",
    "pressure_pack_from_diagnostics",
    "bind_artikl_projection",
    "build_target_world_snapshot",
    "compare_round_trip",
    "reconcile_target_pressure_pack",
    "derive_transition_class",
    "propose_transition",
]
