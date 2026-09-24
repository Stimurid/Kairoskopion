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
    ManuscriptSurfaceProfile,
    RoundTripComparison,
    TargetPressureItem,
    TargetPressurePack,
    TargetModelBundle,
    TargetWorldSnapshot,
)
from .batch import (
    AcademicWorldNode,
    BatchArticleInput,
    BatchCell,
    BatchQualificationPlan,
    BatchQualificationSpec,
    BatchTargetInput,
    LocalFirstAuditReceipt,
    build_batch_qualification_plan,
)
from .batch_runtime import (
    AcademicWorldStore,
    BatchRunStore,
    authorize_external_discovery,
    persist_target_world_refresh,
    probe_local_first,
)
from .batch_executor import (
    BatchCellQualificationReceipt,
    BatchQualificationReceiptStore,
    qualify_batch_cell,
    run_batch_qualification_slice,
)
from .adapter import pressure_pack_from_diagnostics
from .artikl_projection import bind_artikl_projection
from .target_world import build_target_world_snapshot
from .round_trip import compare_round_trip
from .reconcile import reconcile_target_pressure_pack, derive_transition_class
from .transition import propose_transition

__all__ = [
    "AcademicWorldNode",
    "BatchArticleInput",
    "BatchCell",
    "BatchQualificationPlan",
    "BatchQualificationSpec",
    "AcademicWorldStore",
    "BatchRunStore",
    "authorize_external_discovery",
    "persist_target_world_refresh",
    "probe_local_first",
    "BatchTargetInput",
    "LocalFirstAuditReceipt",
    "build_batch_qualification_plan",
    "BatchCellQualificationReceipt",
    "BatchQualificationReceiptStore",
    "qualify_batch_cell",
    "run_batch_qualification_slice",
    "ArtiklArticleProjection",
    "ArtiklStatePointer",
    "CorpusArtifact",
    "CorpusArtifactManifest",
    "EditorScientificProfile",
    "KaironProviderRequest",
    "KaironTransitionDecision",
    "KaironProviderResponse",
    "ManuscriptSurfaceProfile",
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