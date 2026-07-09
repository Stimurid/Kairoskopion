/**
 * Domain types mirroring Python schema.
 * Generated from kairoskopion.schema + kairoskopion.enums.
 */

// --- Evidence Status ---

export type EvidenceStatus =
  | 'fact_from_source'
  | 'fact_from_api_metadata'
  | 'vendor_claim'
  | 'corpus_observation'
  | 'inference'
  | 'tacit_signal'
  | 'user_note'
  | 'prior_outcome'
  | 'unknown'
  | 'inaccessible'
  | 'stale'
  | 'conflicting_evidence';

export type LifecycleStatus =
  | 'created' | 'draft' | 'needs_sources' | 'needs_user_input'
  | 'evidence_collected' | 'analyzed' | 'preliminary' | 'confirmed'
  | 'accepted_by_user' | 'used_in_output' | 'stale' | 'superseded'
  | 'archived' | 'error';

export type FitLabel =
  | 'strong_candidate' | 'possible' | 'possible_but_costly'
  | 'poor_fit' | 'high_risk' | 'not_enough_data';

export type MismatchSeverity = 'blocking' | 'major' | 'minor' | 'informational';

export type FieldCoreImpact =
  | 'core_preserving' | 'core_touching' | 'core_transforming'
  | 'core_destroying_risk' | 'unknown_core_impact';

export type FitAxisValue = 'strong' | 'medium' | 'weak' | 'bad' | 'unknown';

export type QualityGateStatus =
  | 'passed' | 'passed_with_warnings' | 'failed_blocking'
  | 'failed_but_preliminary_output_allowed'
  | 'needs_user_input' | 'needs_source_refresh' | 'not_applicable';

export type OutputLevel =
  | 'rough_note' | 'preliminary' | 'light_profile'
  | 'evidence_backed' | 'submission_ready' | 'post_outcome';

// --- Case ---

export type CaseStage =
  | 'empty' | 'intake' | 'article_model' | 'scenario'
  | 'pathways' | 'venue_pool' | 'venue_selected'
  | 'fit_assessed' | 'adapting' | 'submission_pack' | 'dossier';

export interface CaseSummary {
  case_id: string;
  title: string;
  stage: CaseStage;
  created_at: string;
  objects_present: Record<string, boolean>;
}

export interface CaseDetail extends CaseSummary {
  input_text_length: number;
  input_type: string;
  decision_log_count: number;
  quality_gates: Record<string, QualityGateResult>;
  article_model_id?: string;
  scenario_id?: string;
  selected_venue_id?: string;
  fit_label?: FitLabel;
}

// --- Article Model ---

export interface ArticleModel {
  article_model_id: string;
  title: string;
  abstract: string;
  problem_statement: string;
  research_question: string;
  object_of_inquiry: string;
  core_claims: string[];
  genre: string;
  novelty_mode: string;
  method_status: string;
  method_description: string;
  disciplinary_register_current: string[];
  theoretical_shoulders: string[];
  protected_core: string[];
  mutable_zones: string[];
  high_risk_zones: string[];
  unknowns: string[];
  confidence: string;
  lifecycle_status: LifecycleStatus;
  evidence_refs: string[];
  extraction_attempt?: ExtractionAttempt | null;
}

// --- Semantic Profile ---

export interface ArticleSemanticProfile {
  article_semantic_profile_id: string;
  disciplinary_registers: string[];
  schools_and_traditions: string[];
  argument_move_type: string;
  protected_core_candidates: string[];
  mutable_zones: string[];
  intended_audience: string;
  extraction_attempt?: ExtractionAttempt | null;
}

// --- Scenario ---

export interface SubmissionScenario {
  submission_scenario_id: string;
  article_model_id: string;
  goal: string;
  prestige_priority: string;
  speed_priority: string;
  apc_max: number | null;
  deadline: string | null;
  rewrite_depth_allowed: string;
  risk_tolerance: string;
  target_indexing: string[];
  language: string;
  // feature/venue-fit-dossier-slice: when fit ran without operator-
  // provided scenario, _run_fit_chain synthesizes a preliminary one
  // and sets this flag. UI shows a banner so verdict reads as preliminary.
  scenario_preliminary?: boolean;
}

// --- Pathway ---

export interface LLMModelAttemptRecord {
  attempt_index: number;
  model: string;
  agent_role: string;
  latency_ms: number;
  provider_status: string;
  response_status: string;
  parse_status: string;
  error_code: string;
  retryable: boolean;
  transition: string;
}

export interface ExtractionAttempt {
  llm_attempted?: boolean;
  llm_provider?: string | null;
  llm_model?: string | null;
  llm_latency_ms?: number | null;
  parse_status?: string;
  fallback_used?: boolean;
  fallback_reason?: string;
  warning_for_user?: string | null;
  repair_attempted?: boolean;
  repair_status?: string;
  raw_output_ref?: string | null;
  requested_model?: string | null;
  effective_model?: string | null;
  attempt_count?: number;
  attempts?: LLMModelAttemptRecord[];
  final_error_code?: string | null;
  agent_role?: string;
}

export interface DisciplinaryPathway {
  disciplinary_pathway_id: string;
  discipline_name: string;
  fit_strength: string;
  required_adaptations: string[];
  field_core_risk: FieldCoreImpact;
  venue_type_hints: string[];
  venue_search_queries: string[];
  rank: number;
  strategic_value_notes: string;
  reasoning?: string;
  confidence?: string;
  extraction_attempt?: ExtractionAttempt | null;
}

// --- Venue ---

export interface VenueCandidate {
  venue_candidate_id: string;
  canonical_name: string;
  issn: string;
  status: string;
  confidence: string;
  discovery_reasons: string[];
  authority_assessments: Record<string, unknown>[];
}

export interface VenueCandidatePool {
  venue_candidate_pool_id: string;
  article_model_id: string;
  candidates: VenueCandidate[];
}

export interface VenueModel {
  venue_model_id: string;
  canonical_name: string;
  venue_type: string;
  scope_summary: string;
  article_types_supported: string[];
  publication_regime_id: string;
  indexing_claims: Record<string, unknown>[];
  apc_policy: string;
  ai_policy: string;
  open_access_status: string;
  unknowns: string[];
  confidence: string;
  lifecycle_status: LifecycleStatus;
}

// --- Fit ---

export interface FitAxis {
  axis: string;
  value: FitAxisValue;
  evidence_refs: string[];
  confidence: string;
  notes: string;
  // services/fit_assessment.py _axis() also emits this field; the
  // Dossier UI's Fit matrix renders unknowns under the axis row.
  unknowns?: string[];
}

export interface FitAssessment {
  fit_assessment_id: string;
  overall_label: FitLabel;
  assessment_level: string;
  axes: FitAxis[];
  confidence: string;
  mismatch_map_id: string;
  recommendation: string;
  unknowns: string[];
  extraction_attempt?: ExtractionAttempt | null;
}

// --- Risk Report (built by Case._run_fit_chain after select_venue) ---

export interface RiskItem {
  risk_id: string;
  risk_type: string;
  description: string;
  severity: 'blocking' | 'major' | 'minor' | 'informational' | string;
  likelihood?: string | null;
  evidence_refs?: string[];
  mitigation?: string | null;
  requires_user_action?: boolean;
}

export interface RiskReport {
  risk_report_id: string;
  article_model_id?: string | null;
  venue_model_id?: string | null;
  submission_scenario_id?: string | null;
  risk_items: RiskItem[];
  overall_risk_label?: string | null;
  blocking_risks: string[];
  warnings: string[];
  unknowns: string[];
  evidence_refs: string[];
  lifecycle_status?: string;
  created_at?: string;
  // Round II-B
  field_origins?: Record<string, string>;
  semantic_status?: string;
}

// --- Mismatch ---

export interface MismatchItem {
  mismatch_id: string;
  axis: string;
  article_side: string;
  venue_side: string;
  severity: MismatchSeverity;
  description: string;
  possible_actions: string[];
  field_core_risk: FieldCoreImpact;
  // V2-B1 per-mismatch narrative status (written by _run_fit_chain).
  // Distinguishes llm_filled from honestly-empty cases.
  narrative_status?:
    | 'llm_filled' | 'needs_llm' | 'unknown_due_to_venue_evidence'
    | 'missing_from_llm_output' | 'axis_unmatched' | 'parse_failed'
    | 'provider_error' | string;
}

// V2-B1/B2: structured narrator coverage diagnostic. Backend populates
// on _run_fit_chain after MismatchNarrator runs. Distinguishes 11
// narrator-status modes; for parse_failed, surfaces 6 redacted V2-B2
// fields (no raw LLM output).
export interface NarratorCoverage {
  narrator_attempted: boolean;
  narrator_status:
    | 'not_attempted' | 'filled' | 'partial' | 'empty_valid_unknown'
    | 'empty_llm_output' | 'missing_axes' | 'axis_match_failure'
    | 'parse_failed' | 'provider_error' | 'input_insufficient'
    | 'unknown' | string;
  filled_count: number;
  total_count: number;
  missing_axes: string[];
  unmatched_axes: string[];
  parse_status?: string | null;
  used_model?: string | null;
  latency_ms?: number | null;
  empty_reason?: string | null;
  parse_failure_category?: string | null;
  parse_failure_reason?: string | null;
  schema_failure_path?: string | null;
  schema_failure_rule?: string | null;
  repair_failure_stage?: string | null;
  repair_steps_attempted?: string[];
}

export interface MismatchMap {
  mismatch_map_id: string;
  mismatches: MismatchItem[];
  critical_mismatches: string[];
  summary: string;
  unknowns: string[];
  narrator_coverage?: NarratorCoverage | null;
}

// --- Rewrite Plan ---

export interface RewriteChange {
  change_id: string;
  target_block: string;
  desired_state: string;
  reason: string;
  status: string;
  field_core_risk: FieldCoreImpact;
  _blocked_reason?: string;
  _matched_core_elements?: string[];
}

export interface RewritePlan {
  rewrite_plan_id: string;
  changes: RewriteChange[];
  estimated_effort: string | null;
  field_core_risk: FieldCoreImpact;
  requires_user_acceptance: boolean;
  summary: string | null;
  // Round II-B
  field_origins?: Record<string, string>;
  semantic_status?: string;
  unknowns?: string[];
}

// --- Quality Gate ---

export interface QualityGateResult {
  gate_id: string;
  gate_name: string;
  status: QualityGateStatus;
  blocking_issues: string[];
  warnings: string[];
  notes: string;
}

// --- Evidence ---

export interface EvidenceDetail {
  entity_type: string;
  field_path: string;
  evidence_status: EvidenceStatus;
  source: string | null;
  confidence: string;
  note: string;
}

// --- Decision ---

export interface DecisionLogEntry {
  action: string;
  details: Record<string, unknown>;
  timestamp: string;
}

// --- Publication Regime ---

export interface PublicationRegimeModel {
  publication_regime_id: string;
  venue_model_id: string;
  regime_type: string;
  review_type: string;
  typical_review_rounds: number;
  typical_turnaround_weeks: string;
  article_types_supported: string[];
  special_issues_active: boolean;
  submission_system: string;
  formatting_strictness: string;
  unknowns: string[];
  confidence: string;
  lifecycle_status: LifecycleStatus;
}

// --- Venue Investigation Result ---

export interface VenueInvestigationResult {
  venue: VenueModel;
  publication_regime?: PublicationRegimeModel;
}

// --- Dossier ---

export interface Dossier {
  case_id: string;
  title: string;
  stage: CaseStage;
  created_at: string;
  generated_at: string;
  article_model?: ArticleModel;
  semantic_profile?: ArticleSemanticProfile;
  scenario?: SubmissionScenario;
  pathways?: DisciplinaryPathway[];
  venue_pool?: VenueCandidatePool;
  selected_venue?: VenueModel;
  fit_assessment?: FitAssessment;
  mismatch_map?: MismatchMap;
  rewrite_plan?: RewritePlan;
  risk_report?: RiskReport;
  // V2-D minimal-real lanes. When absent → V2-C placeholders render.
  citation_plan?: CitationPlanV2D | null;
  compliance_checklist?: ComplianceChecklistV2D | null;
  submission_pack?: SubmissionPackV2D | null;
  // V2-E structural BibliographyProfile
  bibliography_profile?: BibliographyProfileV2E | null;
  decision_log: DecisionLogEntry[];
  quality_gates: Record<string, QualityGateResult>;
}

// --- Round III-H: human-readable Russian author dossier ---
// Presentation layer only; built by services/human_dossier.py from the
// same case object — no LLM, no fabrication.
export interface HumanSubsection {
  title_ru: string;
  paragraphs: string[];
  bullets: string[];
  status_ru?: string | null;
  badge?: string | null;
}

export interface HumanSection {
  id: string;
  title_ru: string;
  paragraphs: string[];
  bullets: string[];
  subsections: HumanSubsection[];
}

export interface HumanSourceHeader {
  source_filename_ru: string;
  source_type_ru: string;
  size_ru: string;
  document_title_ru: string;
  case_id_ru: string;
  generated_at_ru: string;
  notes: string[];
}

export interface HumanAgentEntry {
  lane: string;
  role: string;
  model_role?: string;
  provider_status?: string;
  parse_status?: string;
  repair_status?: string;
  semantic_status?: string;
  fallback_reason?: string;
  rubric_active?: boolean;
  latency_ms?: number;
  raw_output_exposed?: boolean;
  filled_count?: number;
  total_count?: number;
}

export interface HumanTechnicalFooter {
  input_metadata: Record<string, string | number | boolean | null>;
  pipeline_metadata: Record<string, string | number | null>;
  agent_metadata: HumanAgentEntry[];
  token_metadata: Record<string, string | number | null>;
  safety_gates: Record<string, string | number | boolean | null>;
  known_limitations: string[];
}

export interface HumanDossier {
  case_id: string;
  title_ru: string;
  venue_name_ru: string;
  stage_ru: string;
  generated_at?: string | null;
  sections: HumanSection[];
  source_header: HumanSourceHeader;
  technical_footer: HumanTechnicalFooter;
}

// V2-D minimal-real CitationPlan. Builder:
// services/citation_plan_minimal.py. No invented references.
export interface CitationPlanV2D {
  citation_plan_id: string;
  article_model_id?: string | null;
  venue_model_id?: string | null;
  fit_assessment_id?: string | null;
  // Round-II semantic provenance
  field_origins?: Record<string, string>;
  semantic_status?: string;
  status:
    | 'not_built' | 'draft' | 'needs_bibliography' | 'needs_venue_corpus'
    | 'search_tasks_ready' | 'partially_ready' | 'blocked_missing_evidence'
    | string;
  current_bibliography_status?: string | null;
  venue_citation_expectation_status?: string | null;
  citation_gap_categories: string[];
  missing_bridge_categories: string[];
  recommended_reference_search_tasks: string[];
  verification_tasks: string[];
  dangerous_padding_warnings: string[];
  risk_flags: string[];
  unknowns: string[];
  created_from: string[];
  confidence?: string | null;
}

// V2-D minimal-real ComplianceChecklist.
export interface ComplianceItemV2D {
  item_id: string;
  category: string;
  requirement: string;
  status:
    | 'satisfied' | 'missing' | 'needs_user_input'
    | 'unknown_not_verified' | 'not_applicable' | 'warning' | 'blocked'
    | string;
  source_status?: string;
  evidence_refs?: string[];
  user_action_needed?: boolean;
  notes?: string;
}

export interface ComplianceChecklistV2D {
  compliance_checklist_id: string;
  article_model_id?: string | null;
  venue_model_id?: string | null;
  submission_scenario_id?: string | null;
  field_origins?: Record<string, string>;
  semantic_status?: string;
  status:
    | 'not_built' | 'draft' | 'partial' | 'ready' | 'blocked' | string;
  checklist_items: ComplianceItemV2D[];
  missing_items: string[];
  blocking_items: string[];
  warnings: string[];
  unknowns: string[];
  created_from: string[];
  confidence?: string | null;
}

// V2-E minimal-real BibliographyProfile (structural-extraction).
export interface BibliographyReferenceV2E {
  reference_id: string;
  raw_text: string;
  authors_text?: string | null;
  year?: number | null;
  title_text?: string | null;
  venue_text?: string | null;
  doi?: string | null;
  url?: string | null;
  identifier_status:
    | 'doi_detected' | 'url_detected' | 'no_identifier_detected'
    | 'ambiguous_identifier' | 'unknown' | string;
  parse_status:
    | 'parsed_minimal' | 'raw_only' | 'malformed' | 'empty'
    | 'duplicate_suspect' | string;
  verification_status:
    | 'not_verified' | 'structural_only' | 'identifiers_detected'
    | 'needs_external_lookup' | 'partially_verified' | 'verified'
    | string;
  warnings: string[];
}

export interface BibliographyProfileV2E {
  bibliography_profile_id: string;
  article_model_id?: string | null;
  source?: string | null;
  field_origins?: Record<string, string>;
  semantic_status?: string;
  status:
    | 'not_found' | 'present_unparsed' | 'parsed_structural' | 'partial'
    | 'malformed' | 'needs_user_input' | 'unknown' | string;
  bibliography_text_available: boolean;
  bibliography_section_detected: boolean;
  reference_count: number;
  parsed_reference_count: number;
  unparsed_reference_count: number;
  references: BibliographyReferenceV2E[];
  detected_identifiers: Record<string, number>;
  year_distribution: Record<string, number>;
  year_min?: number | null;
  year_max?: number | null;
  doi_count: number;
  url_count: number;
  possibly_incomplete: boolean;
  malformed_count: number;
  duplicate_suspect_count: number;
  verification_status:
    | 'not_verified' | 'structural_only' | 'identifiers_detected'
    | 'needs_external_lookup' | 'partially_verified' | 'verified'
    | 'blocked_missing_bibliography' | string;
  verification_tasks: string[];
  warnings: string[];
  unknowns: string[];
  created_from: string[];
  confidence?: string | null;
}

// V2-D minimal-real SubmissionPack readiness skeleton.
export interface SubmissionPackV2D {
  submission_pack_id: string;
  article_model_id?: string | null;
  venue_model_id?: string | null;
  submission_scenario_id?: string | null;
  compliance_checklist_id?: string | null;
  citation_plan_id?: string | null;
  field_origins?: Record<string, string>;
  semantic_status?: string;
  status:
    | 'not_built' | 'draft' | 'partial' | 'ready_skeleton' | 'blocked'
    | string;
  ready_status:
    | 'not_ready' | 'needs_user_input' | 'needs_file_update'
    | 'needs_reference_verification' | 'needs_compliance_check'
    | 'ready_for_manual_submission' | 'blocked_missing_evidence'
    | string;
  files: string[];
  statements: string[];
  cover_letter?: string | null;
  metadata?: Record<string, unknown>;
  missing_items: string[];
  blocking_issues: string[];
  warnings: string[];
  next_actions: string[];
  depends_on: string[];
  created_from: string[];
  unknowns: string[];
}
