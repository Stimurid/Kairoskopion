/**
 * API client for Kairoskopion backend.
 */

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

// --- Bearer token (staging soft-auth) ---
const TOKEN_KEY = 'kairoskopion_token';

export function getToken(): string | null {
  try { return localStorage.getItem(TOKEN_KEY); }
  catch { return null; }
}

export function setToken(token: string): void {
  try { localStorage.setItem(TOKEN_KEY, token); } catch { /* private mode */ }
}

export function clearToken(): void {
  try { localStorage.removeItem(TOKEN_KEY); } catch { /* private mode */ }
}

export class UnauthorizedError extends Error {
  constructor(public body: string) {
    super(`API 401: ${body}`);
    this.name = 'UnauthorizedError';
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    ...((init?.headers as Record<string, string>) ?? {}),
  };
  // Only set Content-Type for JSON requests; multipart uploads set their own.
  if (!headers['Content-Type'] && !(init?.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }
  const tok = getToken();
  if (tok && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${tok}`;
  }
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    const body = await res.text();
    if (res.status === 401) {
      // Token gone bad — surface so the gate can re-prompt
      clearToken();
      throw new UnauthorizedError(body);
    }
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json();
}

function get<T>(path: string) {
  return request<T>(path);
}

function post<T>(path: string, body?: unknown) {
  return request<T>(path, {
    method: 'POST',
    body: body != null ? JSON.stringify(body) : undefined,
  });
}

function del<T>(path: string) {
  return request<T>(path, { method: 'DELETE' });
}

function patch<T>(path: string, body?: unknown) {
  return request<T>(path, {
    method: 'PATCH',
    body: body != null ? JSON.stringify(body) : undefined,
  });
}

// --- Cases ---

import type {
  CaseSummary,
  CaseDetail,
  ArticleModel,
  SubmissionScenario,
  DisciplinaryPathway,
  FitAssessment,
  MismatchMap,
  QualityGateResult,
  EvidenceDetail,
  DecisionLogEntry,
  Dossier,
  HumanDossier,
  VenueInvestigationResult,
} from '../types/domain';

export interface AuthUser {
  user_id: string;
  display_name: string;
  email: string | null;
  created_at: string;
}

export interface AuthResponse {
  user: AuthUser;
  session_token: string;
}

export interface RegistryRecord {
  [key: string]: unknown;
  _usage_status?: string;
  _record_type?: string;
  source_status?: string;
  review_status?: string;
  canonical_name?: string;
  venue_id?: string;
  discipline_id?: string;
  section_id?: string;
}

export const api = {
  health: () => get<{ status: string; version: string }>('/health'),

  // Auth (staging soft-auth: no password, no verification)
  signup: (displayName: string, email?: string) =>
    post<AuthResponse>('/auth/signup', { display_name: displayName, email: email || null }),
  continueSession: (email: string) =>
    post<AuthResponse>('/auth/continue', { email }),
  me: () => get<{ user: AuthUser }>('/auth/me'),
  logout: () => post<{ revoked: boolean }>('/auth/logout'),

  // Cases
  listCases: () => get<CaseSummary[]>('/cases'),
  createCase: (title: string) => post<CaseSummary>('/cases', { title }),
  getCase: (id: string) => get<CaseDetail>(`/cases/${id}`),
  deleteCase: (id: string) => del<{ deleted: string }>(`/cases/${id}`),

  // Intake
  intakeText: (id: string, text: string, inputType = 'auto', searchDepth = 'none', region = 'auto') =>
    post<{ input_type: string; text_length: number; article_model_built: boolean; venue_investigated: boolean; stage: string; enrichment?: { status: string; fields_updated?: string[]; unknowns_resolved?: string[] } }>(
      `/cases/${id}/intake/text`,
      { text, input_type: inputType, search_depth: searchDepth, region },
    ),

  intakeFile: async (id: string, file: File, inputType = 'auto', region = 'auto') => {
    const form = new FormData();
    form.append('file', file);
    form.append('input_type', inputType);
    form.append('region', region);
    // Use fetch directly (FormData), but inject the Bearer header so
    // user-scoped upload reaches the right workspace.
    const tok = getToken();
    const headers: Record<string, string> = {};
    if (tok) headers['Authorization'] = `Bearer ${tok}`;
    const res = await fetch(`${BASE}/cases/${id}/intake/file`, {
      method: 'POST',
      body: form,
      headers,
    });
    if (!res.ok) {
      const body = await res.text();
      if (res.status === 401) {
        clearToken();
        throw new UnauthorizedError(body);
      }
      throw new Error(`API ${res.status}: ${body}`);
    }
    return res.json() as Promise<{
      input_type: string; text_length: number; article_model_built: boolean;
      venue_investigated: boolean; stage: string; filename: string; extraction_status: string;
    }>;
  },

  // Venue investigation
  investigateVenue: (id: string, text: string) =>
    post<VenueInvestigationResult>(`/cases/${id}/investigate-venue`, { text }),
  getInvestigatedVenue: (id: string) =>
    get<VenueInvestigationResult>(`/cases/${id}/investigated-venue`),

  // Intake override (Track A, intake-choice-and-routing-seam)
  overrideIntakeType: (id: string, chosenType: string) =>
    post<{
      input_type: string;
      effective_input_type: string;
      classifier_input_type: string | null;
      classifier_confidence: string | null;
      user_selected_input_type: string;
      override_source: string;
      override_at: string;
      text_length: number;
      article_model_built: boolean;
      venue_investigated: boolean;
      stage: string;
    }>(`/cases/${id}/intake/override`, { chosen_type: chosenType }),

  // Disciplines (Phase B2)
  getDisciplineMatches: (id: string) =>
    get<{
      region_hint: string;
      matched: { discipline_id: string; strength: string; why: string }[];
      new_candidate: { display_name: string; reason: string } | null;
      confidence: 'high' | 'medium' | 'low';
      reasoning: string;
    }>(`/cases/${id}/discipline-matches`),

  // Article
  getArticleModel: (id: string) => get<ArticleModel>(`/cases/${id}/article-model`),
  confirmArticleModel: (
    id: string,
    protectedCore?: string[],
    corrections?: Record<string, unknown>,
  ) =>
    post<{ confirmed: boolean; protected_core: string[]; lifecycle_status: string }>(
      `/cases/${id}/article-model/confirm`,
      { protected_core: protectedCore, corrections },
    ),

  // Refinement dialog (M-8)
  refineArticleModel: (id: string, message: string) =>
    post<{ reply: string; suggestions: { field: string; value: string; reason: string }[]; llm_available: boolean }>(
      `/cases/${id}/article-model/refine`,
      { message },
    ),
  getRefinementChat: (id: string) =>
    get<{ role: string; content: string; suggestions?: { field: string; value: string; reason: string }[]; timestamp: string }[]>(
      `/cases/${id}/article-model/refinement-chat`,
    ),

  // Correction signals (M-9)
  getCorrectionSignals: (minOccurrences = 3) =>
    get<{ signals: { type: string; field?: string; block_id?: string; correction_count?: number; rejection_count?: number; most_common_override?: string; severity: string; message: string }[]; total: number }>(
      `/correction-signals?min_occurrences=${minOccurrences}`,
    ),

  // Scenario
  getScenario: (id: string) => get<SubmissionScenario>(`/cases/${id}/scenario`),
  setScenario: (id: string, data: Record<string, unknown>) =>
    post<SubmissionScenario>(`/cases/${id}/scenario`, data),

  // Pathways
  getPathways: (id: string) => get<DisciplinaryPathway[]>(`/cases/${id}/pathways`),

  // Venue pool
  discoverVenues: (id: string) =>
    post<{ candidates: unknown[]; status?: string }>(`/cases/${id}/discover-venues`),
  getVenuePool: (id: string) =>
    get<{ candidates: unknown[]; status?: string }>(`/cases/${id}/venue-pool`),

  // Venue selection & fit
  selectVenue: (caseId: string, venueId: string) =>
    post<{ selected_venue_id: string; stage: string; fit_available?: boolean; mismatch_count?: number; rewrite_plan_available?: boolean }>(`/cases/${caseId}/select-venue/${venueId}`),
  getFit: (id: string) => get<FitAssessment | { status: string }>(`/cases/${id}/fit`),
  getMismatchMap: (id: string) => get<MismatchMap | { mismatches: []; status: string }>(`/cases/${id}/mismatch-map`),

  // Adaptation
  getAdaptationPlan: (id: string) =>
    get<Record<string, unknown>>(`/cases/${id}/adaptation-plan`),
  applyDecisions: (id: string, decisions: { change_id: string; action: string; reason?: string }[]) =>
    post<Record<string, unknown>>(`/cases/${id}/decisions`, decisions),

  // Evidence
  getEvidence: (caseId: string, entityType: string, fieldPath: string) =>
    get<EvidenceDetail>(`/cases/${caseId}/evidence/${entityType}/${fieldPath}`),

  // Quality gates
  getQualityGates: (id: string) =>
    get<Record<string, QualityGateResult>>(`/cases/${id}/quality-gates`),

  // Dossier
  getDossier: (id: string) => get<Dossier>(`/cases/${id}/dossier`),
  getHumanDossier: (id: string) => get<HumanDossier>(`/cases/${id}/human-dossier`),

  // Decision log
  getDecisionLog: (id: string) => get<DecisionLogEntry[]>(`/cases/${id}/decision-log`),

  // Agent map
  getAgentMap: () => get<AgentMapData>('/agents/map'),

  // Phase 1: venue investigation by URL
  investigateVenueByUrl: (id: string, url: string) =>
    post<VenueInvestigationResult>(`/cases/${id}/investigate-venue-by-url`, { url }),

  // Phase 2: enrich venue, profile package, compliance, submission pack
  enrichVenue: (id: string) =>
    post<Record<string, unknown>>(`/cases/${id}/enrich-venue`),
  getVenueProfilePackage: (id: string) =>
    get<Record<string, unknown>>(`/cases/${id}/venue-profile-package`),
  getCompliance: (id: string) =>
    get<Record<string, unknown>>(`/cases/${id}/compliance`),
  buildSubmissionPack: (id: string) =>
    post<Record<string, unknown>>(`/cases/${id}/build-submission-pack`),

  // Phase 3: discipline intent, venue family, venue matrix
  setDisciplineIntent: (id: string, description: string, region?: string, constraints?: string[]) =>
    post<Record<string, unknown>>(`/cases/${id}/set-discipline-intent`, {
      description, region, constraints,
    }),
  getVenueFamilyContext: (id: string) =>
    get<Record<string, unknown>>(`/cases/${id}/venue-family-context`),
  getVenueMatrix: (id: string) =>
    get<Record<string, unknown>>(`/cases/${id}/venue-matrix`),

  // Phase 4: venue memory
  listVenueMemory: () => get<Record<string, unknown>[]>('/venue-memory'),
  getVenueMemory: (vmid: string) => get<Record<string, unknown>>(`/venue-memory/${vmid}`),

  // Phase 5: depth mode & budget
  setDepthMode: (id: string, mode: string) =>
    post<Record<string, unknown>>(`/cases/${id}/set-depth-mode`, { mode }),
  setBudget: (id: string, maxApiCalls?: number, maxTokens?: number) =>
    post<Record<string, unknown>>(`/cases/${id}/set-budget`, {
      max_api_calls: maxApiCalls, max_tokens: maxTokens,
    }),
  getCostEstimate: (id: string) =>
    get<Record<string, unknown>>(`/cases/${id}/cost-estimate`),

  // Phase 6: registry
  listRegistryTypes: () => get<string[]>('/api/registry/types'),
  listRegistryRecords: (recordType: string, q = '', limit = 50) =>
    get<RegistryRecord[]>(`/api/registry/${recordType}?q=${encodeURIComponent(q)}&limit=${limit}`),
  getRegistryRecord: (recordType: string, recordId: string) =>
    get<RegistryRecord>(`/api/registry/${recordType}/${recordId}`),
  acceptRegistryRecord: (recordType: string, recordId: string, note?: string) =>
    post<RegistryRecord>(`/api/registry/${recordType}/${recordId}/accept`, { note: note ?? null }),
  rejectRegistryRecord: (recordType: string, recordId: string, note?: string) =>
    post<RegistryRecord>(`/api/registry/${recordType}/${recordId}/reject`, { note: note ?? null }),
  getReviewQueue: (limit = 100) =>
    get<RegistryRecord[]>(`/api/registry/review-queue?limit=${limit}`),
  listOpenTasks: () => get<Record<string, unknown>[]>('/api/registry/tasks/open'),
};

// --- Agent Map types ---

export interface AgentMapAgent {
  role_id: string;
  display_name: string;
  layer: string;
  implementation_status: string;
  execution_mode: string;
  prompt_family_ids: string[];
  input_contract: Record<string, string>;
  output_contract: Record<string, string>;
  mvp_phase: string;
  first_workflows: string[];
  has_real_llm: boolean;
  has_orphaned_prompt: boolean;
}

export interface AgentMapWorkflowStep {
  step_index: number;
  agent_role_id: string;
  output_key: string;
  input_keys: string[];
  skip_if_missing: string[];
  required: boolean;
  description: string;
}

export interface AgentMapWorkflow {
  workflow_id: string;
  display_name: string;
  description: string;
  implementation_status: string;
  steps: AgentMapWorkflowStep[];
}

export interface AgentMapPrompt {
  family_id: string;
  agent_role_id: string;
  version: string;
  system_prompt: string;
  user_prompt_template: string;
  system_prompt_lines: number;
  user_prompt_lines: number;
  output_schema_fields: string[];
  purpose: string;
  forbidden_behaviors?: string[];
  evidence_requirements?: string[];
}

export interface AgentMapData {
  agents: AgentMapAgent[];
  workflows: AgentMapWorkflow[];
  prompts: Record<string, AgentMapPrompt>;
  llm: Record<string, unknown>;
}

// --- P11 Prompt Pipeline Workbench ---

export interface PromptFamilyInfo {
  prompt_family_id: string;
  path: string;
  source_module: string;
  version_hash: string;
  has_schema?: boolean;
  schema_ref?: string;
  agent_ref?: string;
  description?: string;
  system_prompt?: string;
  user_template?: string;
}

export interface PipelineStage {
  stage_id: string;
  label: string;
  producer: string;
  service: string;
  prompt_family: string | null;
}

export interface PipelineRunSummary {
  run_id: string;
  case_id?: string;
  trigger: string;
  status: string;
  started_at: string;
  completed_at?: string;
  node_ids: string[];
  base_run_id?: string;
  prompt_override_ids?: string[];
  gates_summary?: Record<string, unknown>;
}

export interface PipelineNodeInfo {
  node_id: string;
  run_id: string;
  stage_id: string;
  stage_label: string;
  order_index: number;
  producer_type: string;
  service_or_agent: string;
  prompt_family_id?: string;
  status: string;
  rerunnable?: boolean;
  output_hash?: string;
  prompt_override_id?: string;
}

export interface PromptRunRecordInfo {
  prompt_run_id: string;
  node_id: string;
  prompt_family_id: string;
  prompt_version_hash: string;
  rendered_system_prompt: string;
  rendered_user_prompt: string;
  provider_status?: string;
  response_status?: string;
}

export interface PromptOverrideInfo {
  override_id: string;
  case_id: string;
  base_prompt_family_id: string;
  status: string;
  edited_system_prompt?: string;
  edited_user_template?: string;
  notes?: string;
}

export interface RunDiffEntry {
  stage_id: string;
  field: string;
  run_a: unknown;
  run_b: unknown;
  changed: boolean;
}

export const workbench = {
  listPrompts: () => get<PromptFamilyInfo[]>('/api/prompts'),
  getPrompt: (id: string) => get<PromptFamilyInfo>(`/api/prompts/${id}`),
  listStages: () => get<PipelineStage[]>('/api/pipeline-stages'),

  listRuns: (caseId: string) =>
    get<PipelineRunSummary[]>(`/api/cases/${caseId}/pipeline-runs`),
  getRun: (caseId: string, runId: string) =>
    get<PipelineRunSummary>(`/api/cases/${caseId}/pipeline-runs/${runId}`),
  listNodes: (caseId: string, runId: string) =>
    get<PipelineNodeInfo[]>(`/api/cases/${caseId}/pipeline-runs/${runId}/nodes`),
  getNodePrompt: (caseId: string, runId: string, nodeId: string) =>
    get<PromptRunRecordInfo[]>(`/api/cases/${caseId}/pipeline-runs/${runId}/nodes/${nodeId}/prompt`),

  listOverrides: (caseId: string) =>
    get<PromptOverrideInfo[]>(`/api/cases/${caseId}/prompt-overrides`),
  createOverride: (caseId: string, body: {
    base_prompt_family_id: string;
    edited_system_prompt?: string;
    edited_user_template?: string;
    notes?: string;
  }) => post<PromptOverrideInfo>(`/api/cases/${caseId}/prompt-overrides`, body),
  updateOverride: (caseId: string, overrideId: string, body: {
    status?: string;
    edited_system_prompt?: string;
    edited_user_template?: string;
    notes?: string;
  }) => patch<PromptOverrideInfo>(`/api/cases/${caseId}/prompt-overrides/${overrideId}`, body),

  rerunAll: (caseId: string, overrideIds?: string[]) =>
    post<PipelineRunSummary>(`/api/cases/${caseId}/rerun`, { prompt_override_ids: overrideIds ?? [] }),
  rerunStage: (caseId: string, stageId: string, baseRunId?: string, overrideIds?: string[]) =>
    post<PipelineRunSummary>(`/api/cases/${caseId}/rerun-stage`, {
      stage_id: stageId, base_run_id: baseRunId, prompt_override_ids: overrideIds ?? [],
    }),
  rerunFromStage: (caseId: string, stageId: string, baseRunId?: string, overrideIds?: string[]) =>
    post<PipelineRunSummary>(`/api/cases/${caseId}/rerun-from-stage`, {
      stage_id: stageId, base_run_id: baseRunId, prompt_override_ids: overrideIds ?? [],
    }),

  diffRuns: (caseId: string, runA: string, runB: string) =>
    get<RunDiffEntry[]>(`/api/cases/${caseId}/pipeline-diff?run_a=${runA}&run_b=${runB}`),

  createCorrection: (caseId: string, body: {
    node_id: string;
    correction_type: string;
    user_note: string;
    affected_prompt_family_id: string;
    proposed_change?: string;
  }) => post<unknown>(`/api/cases/${caseId}/corrections`, body),
};
