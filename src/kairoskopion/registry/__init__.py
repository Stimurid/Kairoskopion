"""Registry-first acquisition pipeline (P6).

Provides:
- Record models for disciplines, epistemic frameworks, venues,
  venue sections, classification systems, subject categories,
  venue classifications, venue metrics, source packets, acquisition tasks.
- Generic JSONL-backed registry with search/accept/reject lifecycle.
- record_usage_status() for downstream canonical/provisional distinction.
- Legacy JSONL append/read_all/list_ids/find_by_id (from old registry.py).
"""

from .models import (
    EvidenceRef,
    SourcePacket,
    DisciplineRecord,
    EpistemicFrameworkRecord,
    VenueRegistryRecord,
    VenueSectionRecord,
    ClassificationSystemRecord,
    SubjectCategoryRecord,
    VenueClassificationRecord,
    VenueMetricRecord,
    SourceAcquisitionTask,
    SOURCE_STATUSES,
    REVIEW_STATUSES,
    TASK_STATUSES,
)
from .store import BaseRegistry, load_registry
from .status import record_usage_status
from .legacy import append, read_all, list_ids, find_by_id, registry_exists
from .store import SourcePacketStore, AcquisitionTaskStore
from .services import RegistryHub
from .integration import RegistryIntegrationService

__all__ = [
    # P6 models
    "EvidenceRef",
    "SourcePacket",
    "DisciplineRecord",
    "EpistemicFrameworkRecord",
    "VenueRegistryRecord",
    "VenueSectionRecord",
    "ClassificationSystemRecord",
    "SubjectCategoryRecord",
    "VenueClassificationRecord",
    "VenueMetricRecord",
    "SourceAcquisitionTask",
    "SOURCE_STATUSES",
    "REVIEW_STATUSES",
    "TASK_STATUSES",
    # P6 store
    "BaseRegistry",
    "load_registry",
    "record_usage_status",
    # P6 services
    "RegistryHub",
    "RegistryIntegrationService",
    "SourcePacketStore",
    "AcquisitionTaskStore",
    # Legacy JSONL (from old registry.py)
    "append",
    "read_all",
    "list_ids",
    "find_by_id",
    "registry_exists",
]
