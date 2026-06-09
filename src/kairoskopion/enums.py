"""Enumerations for the Kairoskopion domain model."""

from __future__ import annotations

from enum import Enum


# --- Evidence statuses (Wave 1 §5.6, Wave 2 §6.1) ---

class EvidenceStatus(str, Enum):
    FACT_FROM_SOURCE = "FACT_FROM_SOURCE"
    VENDOR_CLAIM = "VENDOR_CLAIM"
    CORPUS_OBSERVATION = "CORPUS_OBSERVATION"
    INFERENCE = "INFERENCE"
    TACIT_SIGNAL = "TACIT_SIGNAL"
    USER_NOTE = "USER_NOTE"
    PRIOR_OUTCOME = "PRIOR_OUTCOME"
    UNKNOWN = "UNKNOWN"
    INACCESSIBLE = "INACCESSIBLE"
    STALE = "STALE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"


# --- Entity lifecycle (Wave 2 §7) ---

class LifecycleStatus(str, Enum):
    CREATED = "created"
    DRAFT = "draft"
    NEEDS_SOURCES = "needs_sources"
    NEEDS_USER_INPUT = "needs_user_input"
    EVIDENCE_COLLECTED = "evidence_collected"
    ANALYZED = "analyzed"
    PRELIMINARY = "preliminary"
    CONFIRMED = "confirmed"
    ACCEPTED_BY_USER = "accepted_by_user"
    USED_IN_OUTPUT = "used_in_output"
    STALE = "stale"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"
    ERROR = "error"


# --- Quality gate (Wave 5 §36.2) ---

class QualityGateStatus(str, Enum):
    PASSED = "passed"
    PASSED_WITH_WARNINGS = "passed_with_warnings"
    FAILED_BLOCKING = "failed_blocking"
    FAILED_PRELIMINARY_ALLOWED = "failed_but_preliminary_output_allowed"
    NEEDS_USER_INPUT = "needs_user_input"
    NEEDS_SOURCE_REFRESH = "needs_source_refresh"
    NOT_APPLICABLE = "not_applicable"


# --- Pipeline output maturity (Wave 5 §36.3) ---

class OutputLevel(str, Enum):
    ROUGH_NOTE = "rough_note"
    PRELIMINARY = "preliminary"
    LIGHT_PROFILE = "light_profile"
    EVIDENCE_BACKED = "evidence_backed"
    SUBMISSION_READY = "submission_ready"
    POST_OUTCOME = "post_outcome"


# --- Article stage (Wave 2 §6.3) ---

class ArticleStage(str, Enum):
    IDEA = "idea"
    ABSTRACT = "abstract"
    OUTLINE = "outline"
    DRAFT = "draft"
    FULL_MANUSCRIPT = "full_manuscript"
    SUBMISSION_READY = "submission_ready"
    REVISING = "revising"
    PUBLISHED = "published"
    UNKNOWN = "unknown"


# --- Method status (Wave 2 §6.3) ---

class MethodStatus(str, Enum):
    NO_METHOD = "no_method"
    IMPLICIT_METHOD = "implicit_method"
    CONCEPTUAL_METHOD = "conceptual_method"
    EMPIRICAL_METHOD = "empirical_method"
    CASE_BASED = "case_based"
    REVIEW_METHOD = "review_method"
    MIXED = "mixed"
    UNKNOWN = "unknown"


# --- Genre (Wave 2 §6.3) ---

class Genre(str, Enum):
    RESEARCH_ARTICLE = "research_article"
    CONCEPTUAL_ARTICLE = "conceptual_article"
    THEORETICAL_ESSAY = "theoretical_essay"
    REVIEW = "review"
    SYSTEMATIC_REVIEW = "systematic_review"
    POSITION_PAPER = "position_paper"
    COMMENTARY = "commentary"
    CONFERENCE_PAPER = "conference_paper"
    FORUM_PIECE = "forum_piece"
    BOOK_SYMPOSIUM_PIECE = "book_symposium_piece"
    UNKNOWN = "unknown"


# --- Novelty mode (Wave 2 §6.3) ---

class NoveltyMode(str, Enum):
    NEW_OBJECT = "new_object"
    NEW_THEORY = "new_theory"
    NEW_METHOD = "new_method"
    NEW_APPLICATION = "new_application"
    NEW_SYNTHESIS = "new_synthesis"
    CRITIQUE = "critique"
    TRANSLATION_BETWEEN_FIELDS = "translation_between_fields"
    CASE_CONTRIBUTION = "case_contribution"
    EMPIRICAL_FINDING = "empirical_finding"
    UNKNOWN = "unknown"


# --- Venue type (Wave 2 §6.7) ---

class VenueType(str, Enum):
    JOURNAL = "journal"
    JOURNAL_SECTION = "journal_section"
    SPECIAL_ISSUE = "special_issue"
    RESEARCH_TOPIC = "research_topic"
    CONFERENCE_PROCEEDINGS = "conference_proceedings"
    REVIEWED_PREPRINT = "reviewed_preprint"
    OPEN_REVIEW_VENUE = "open_review_venue"
    EDITED_VOLUME = "edited_volume"
    BOOK_SYMPOSIUM = "book_symposium"
    LOCAL_JOURNAL = "local_journal"
    OTHER = "other"


# --- Publication regime type (Wave 2 §6.11) ---

class RegimeType(str, Enum):
    CLASSIC_JOURNAL_ARTICLE = "classic_journal_article"
    SPECIAL_ISSUE_ARTICLE = "special_issue_article"
    RESEARCH_TOPIC_ARTICLE = "research_topic_article"
    CONFERENCE_PROCEEDINGS = "conference_proceedings"
    MEGA_JOURNAL = "mega_journal"
    REVIEWED_PREPRINT = "reviewed_preprint"
    PUBLISH_THEN_REVIEW = "publish_then_review"
    OPEN_REVIEW_CONFERENCE = "open_review_conference"
    HUMANITIES_SPECIAL_ISSUE = "humanities_special_issue"
    BOOK_SYMPOSIUM = "book_symposium"
    FOCUSED_DEBATE = "focused_debate"
    EDITED_VOLUME = "edited_volume"
    NON_FOCUS_Q3_OR_LOCAL = "non_focus_q3_or_local_journal"
    ZINE_OR_NONSTANDARD = "zine_or_nonstandard_publication_backlog"


# --- Input mode (Wave 2 §6.3) ---

class InputMode(str, Enum):
    ABSTRACT_ONLY = "abstract_only"
    DRAFT_TEXT = "draft_text"
    FULL_MANUSCRIPT = "full_manuscript"
    WHITECROW_FIELD = "whitecrow_field"
    LITOPS_CONTEXT_PACK = "litops_context_pack"
    USER_BRIEF = "user_brief"
    REVIEW_LETTER_CONTEXT = "review_letter_context"
    MIXED = "mixed"


# --- Fit label (Wave 2 §6.18) ---

class FitLabel(str, Enum):
    STRONG_CANDIDATE = "strong_candidate"
    POSSIBLE = "possible"
    POSSIBLE_BUT_COSTLY = "possible_but_costly"
    POOR_FIT = "poor_fit"
    HIGH_RISK = "high_risk"
    NOT_ENOUGH_DATA = "not_enough_data"


# --- Assessment level (Wave 2 §6.18) ---

class AssessmentLevel(str, Enum):
    QUICK_SCAN = "quick_scan"
    LIGHT_PROFILE = "light_profile"
    DEEP_PROFILE = "deep_profile"
    POST_REVIEW = "post_review"


# --- Fit axis value (qualitative, no numeric scores in MVP) ---

class FitAxisValue(str, Enum):
    STRONG = "strong"
    MEDIUM = "medium"
    WEAK = "weak"
    BAD = "bad"
    UNKNOWN = "unknown"


# --- Mismatch severity ---

class MismatchSeverity(str, Enum):
    BLOCKING = "blocking"
    MAJOR = "major"
    MINOR = "minor"
    INFORMATIONAL = "informational"


# --- Field-core impact (Wave 3 §14.3) ---

class FieldCoreImpact(str, Enum):
    CORE_PRESERVING = "core_preserving"
    CORE_TOUCHING = "core_touching"
    CORE_TRANSFORMING = "core_transforming"
    CORE_DESTROYING_RISK = "core_destroying_risk"
    UNKNOWN_CORE_IMPACT = "unknown_core_impact"


# --- Submission pack readiness (Wave 2 §6.25) ---

class SubmissionReadiness(str, Enum):
    NOT_READY = "not_ready"
    NEEDS_USER_INPUT = "needs_user_input"
    NEEDS_FILE_UPDATE = "needs_file_update"
    NEEDS_REFERENCE_VERIFICATION = "needs_reference_verification"
    NEEDS_COMPLIANCE_CHECK = "needs_compliance_check"
    READY_FOR_MANUAL_SUBMISSION = "ready_for_manual_submission"
    SUBMITTED = "submitted"
    ARCHIVED = "archived"


# --- Pipeline run status (Wave 5 §36.1) ---

class PipelineRunStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    WAITING_FOR_SOURCES = "waiting_for_sources"
    WAITING_FOR_USER = "waiting_for_user"
    PARTIAL_SUCCESS = "partial_success"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STALE = "stale"
    SUPERSEDED = "superseded"


# --- Entry channel (Wave 5 §36.1) ---

class EntryChannel(str, Enum):
    WEB_UI = "web_ui"
    TELEGRAM = "telegram"
    CLI = "cli"
    API = "api"
    WHITECROW = "whitecrow"
    LITOPS = "litops"
    SCHEDULED_JOB = "scheduled_job"
    MANUAL_ADMIN = "manual_admin"
    UNKNOWN = "unknown"


# --- Decision status (Wave 3 §20) ---

class DecisionStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MODIFIED = "modified"
    DEFERRED = "deferred"
    NEEDS_MORE_EVIDENCE = "needs_more_evidence"
    SUPERSEDED = "superseded"


# --- Rewrite depth (Wave 2 §6.17) ---

class RewriteDepth(str, Enum):
    NONE = "none"
    LIGHT = "light"
    MEDIUM = "medium"
    MAJOR = "major"
    UNKNOWN = "unknown"


# --- Staleness (Wave 4 §28) ---

class StalenessStatus(str, Enum):
    FRESH = "fresh"
    POSSIBLY_STALE = "possibly_stale"
    STALE = "stale"
    EXPIRED = "expired"
    UNKNOWN_FRESHNESS = "unknown_freshness"


# --- Reference source kind (heuristic, not verified) ---

class ReferenceSourceKind(str, Enum):
    JOURNAL_ARTICLE = "journal_article"
    BOOK = "book"
    BOOK_CHAPTER = "book_chapter"
    EDITED_VOLUME = "edited_volume"
    CONFERENCE_PAPER = "conference_paper"
    REPORT = "report"
    THESIS = "thesis"
    WEB_SOURCE = "web_source"
    PREPRINT = "preprint"
    UNKNOWN = "unknown"


# --- Citation gap severity ---

class CitationGapSeverity(str, Enum):
    BLOCKING = "blocking"
    MAJOR = "major"
    MINOR = "minor"
    INFORMATIONAL = "informational"
