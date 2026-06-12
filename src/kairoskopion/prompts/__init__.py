"""Prompt families for Kairoskopion agents (spec §69)."""

from .article_modeling import ARTICLE_MODELING_FAMILY
from .venue_fact_extraction import VENUE_FACT_EXTRACTION_FAMILY
from .fit_assessment import FIT_ASSESSMENT_FAMILY

__all__ = [
    "ARTICLE_MODELING_FAMILY",
    "VENUE_FACT_EXTRACTION_FAMILY",
    "FIT_ASSESSMENT_FAMILY",
]
