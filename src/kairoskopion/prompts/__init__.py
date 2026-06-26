"""Prompt families for Kairoskopion agents (spec §69)."""

from .article_modeling import ARTICLE_MODELING_FAMILY
from .citation_ecology_analysis import CITATION_ECOLOGY_FAMILY
from .compliance_assessment import COMPLIANCE_ASSESSMENT_FAMILY
from .depth_recommendation import DEPTH_RECOMMENDATION_FAMILY
from .discipline_intent_parsing import DISCIPLINE_INTENT_FAMILY
from .discipline_matching import DISCIPLINE_MATCHING_FAMILY
from .discipline_seeding import DISCIPLINE_SEEDING_FAMILY
from .discipline_source_acquisition import DISCIPLINE_SOURCE_ACQUISITION_FAMILY
from .disciplinary_mapping import DISCIPLINARY_MAPPING_FAMILY
from .field_positioning import (
    ARTICLE_FIELD_POSITION_FAMILY,
    VENUE_FIELD_POSITION_FAMILY,
)
from .fit_assessment import FIT_ASSESSMENT_FAMILY
from .input_classification import INPUT_CLASSIFICATION_FAMILY
from .mismatch_narrative import MISMATCH_NARRATIVE_FAMILY
from .rewrite_planning import REWRITE_PLANNING_FAMILY
from .semantic_profiling import SEMANTIC_PROFILING_FAMILY
from .venue_fact_extraction import VENUE_FACT_EXTRACTION_FAMILY
from .venue_family_context import VENUE_FAMILY_CONTEXT_FAMILY
from .venue_funnel_planning import VENUE_FUNNEL_FAMILY
from .venue_matrix_assessment import VENUE_MATRIX_FAMILY

__all__ = [
    "ARTICLE_FIELD_POSITION_FAMILY",
    "ARTICLE_MODELING_FAMILY",
    "CITATION_ECOLOGY_FAMILY",
    "COMPLIANCE_ASSESSMENT_FAMILY",
    "DEPTH_RECOMMENDATION_FAMILY",
    "DISCIPLINARY_MAPPING_FAMILY",
    "DISCIPLINE_INTENT_FAMILY",
    "DISCIPLINE_MATCHING_FAMILY",
    "DISCIPLINE_SEEDING_FAMILY",
    "DISCIPLINE_SOURCE_ACQUISITION_FAMILY",
    "FIT_ASSESSMENT_FAMILY",
    "INPUT_CLASSIFICATION_FAMILY",
    "MISMATCH_NARRATIVE_FAMILY",
    "REWRITE_PLANNING_FAMILY",
    "SEMANTIC_PROFILING_FAMILY",
    "VENUE_FACT_EXTRACTION_FAMILY",
    "VENUE_FAMILY_CONTEXT_FAMILY",
    "VENUE_FIELD_POSITION_FAMILY",
    "VENUE_FUNNEL_FAMILY",
    "VENUE_MATRIX_FAMILY",
]
