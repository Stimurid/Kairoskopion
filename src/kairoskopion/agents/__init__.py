"""Agent roles for Kairoskopion (spec Wave 6, §52-§74)."""

from .article_field_positioner import ArticleFieldPositionerAgent
from .article_modeler import ArticleModelerAgent
from .contract import AgentInput, AgentOutput, AgentRole
from .disciplinary_mapper import DisciplinaryPathwayMapperAgent
from .fit_assessor import FitAssessorAgent
from .semantic_profiler import ArticleSemanticProfilerAgent
from .venue_field_positioner import VenueFieldPositionerAgent
from .venue_profiler import VenueProfilerAgent

from .control import (
    IntentClassifierAgent,
    ResearchPlannerAgent,
    ScenarioProberAgent,
    StatusJobAgent,
)
from .venue import (
    PublicationRegimeClassifierAgent,
    VenueDiscoveryAgent,
    VenueIdentifierAgent,
    VenuePublicationProfileBuilderAgent,
)
from .fit import (
    CitationPlannerAgent,
    MismatchMapperAgent,
    RewritePlannerAgent,
)
from .submission import (
    ComplianceAuditorAgent,
    RiskOfficerAgent,
    SubmissionPackBuilderAgent,
)
from .review import (
    RebuttalArchitectAgent,
    ReviewOutcomeAnalystAgent,
    ReviewerSimulationAgent,
    RevisionPlannerAgent,
    TacitSignalStructurerAgent,
    VenueMemoryKeeperAgent,
)
from .evidence import EvidenceAuditorAgent

__all__ = [
    "AgentInput",
    "AgentOutput",
    "AgentRole",
    # Article layer (existing)
    "ArticleModelerAgent",
    "ArticleSemanticProfilerAgent",
    "DisciplinaryPathwayMapperAgent",
    "ArticleFieldPositionerAgent",
    # Control layer
    "IntentClassifierAgent",
    "ResearchPlannerAgent",
    "ScenarioProberAgent",
    "StatusJobAgent",
    # Venue layer
    "PublicationRegimeClassifierAgent",
    "VenueDiscoveryAgent",
    "VenueIdentifierAgent",
    "VenuePublicationProfileBuilderAgent",
    "VenueProfilerAgent",
    "VenueFieldPositionerAgent",
    # Fit layer
    "CitationPlannerAgent",
    "FitAssessorAgent",
    "MismatchMapperAgent",
    "RewritePlannerAgent",
    # Submission layer
    "ComplianceAuditorAgent",
    "RiskOfficerAgent",
    "SubmissionPackBuilderAgent",
    # Review layer (all contract-only)
    "RebuttalArchitectAgent",
    "ReviewOutcomeAnalystAgent",
    "ReviewerSimulationAgent",
    "RevisionPlannerAgent",
    "TacitSignalStructurerAgent",
    "VenueMemoryKeeperAgent",
    # Evidence layer
    "EvidenceAuditorAgent",
]
