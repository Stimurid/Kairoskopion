"""Prompt families for Kairoskopion agents (spec §69)."""

from .article_modeling import ARTICLE_MODELING_FAMILY
from .discipline_matching import DISCIPLINE_MATCHING_FAMILY
from .disciplinary_mapping import DISCIPLINARY_MAPPING_FAMILY
from .field_positioning import (
    ARTICLE_FIELD_POSITION_FAMILY,
    VENUE_FIELD_POSITION_FAMILY,
)
from .fit_assessment import FIT_ASSESSMENT_FAMILY
from .input_classification import INPUT_CLASSIFICATION_FAMILY
from .semantic_profiling import SEMANTIC_PROFILING_FAMILY
from .venue_fact_extraction import VENUE_FACT_EXTRACTION_FAMILY

__all__ = [
    "ARTICLE_FIELD_POSITION_FAMILY",
    "ARTICLE_MODELING_FAMILY",
    "DISCIPLINARY_MAPPING_FAMILY",
    "DISCIPLINE_MATCHING_FAMILY",
    "FIT_ASSESSMENT_FAMILY",
    "INPUT_CLASSIFICATION_FAMILY",
    "SEMANTIC_PROFILING_FAMILY",
    "VENUE_FACT_EXTRACTION_FAMILY",
    "VENUE_FIELD_POSITION_FAMILY",
]
