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
}

export interface DisciplinaryPathway {
  disciplinary_pathway_id: string;
  discipline_name: string;
  fit_strength: string;
  required_adaptations: string[];
  field_core_risk: FieldCoreImpact;
  venue_type_hints: string[];
  example_venue_names: string[];
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
}

export interface MismatchMap {
  mismatch_map_id: string;
  mismatches: MismatchItem[];
  critical_mismatches: string[];
  summary: string;
  unknowns: string[];
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
  estimated_effort: string;
  field_core_risk: FieldCoreImpact;
  requires_user_acceptance: boolean;
  summary: string;
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
  decision_log: DecisionLogEntry[];
  quality_gates: Record<string, QualityGateResult>;
}
