/**
 * API client for Kairoskopion backend.
 */

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.text();
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
  VenueInvestigationResult,
} from '../types/domain';

export const api = {
  health: () => get<{ status: string; version: string }>('/health'),

  // Cases
  listCases: () => get<CaseSummary[]>('/cases'),
  createCase: (title: string) => post<CaseSummary>('/cases', { title }),
  getCase: (id: string) => get<CaseDetail>(`/cases/${id}`),
  deleteCase: (id: string) => del<{ deleted: string }>(`/cases/${id}`),

  // Intake
  intakeText: (id: string, text: string, inputType = 'auto', searchDepth = 'none') =>
    post<{ input_type: string; text_length: number; article_model_built: boolean; venue_investigated: boolean; stage: string; enrichment?: { status: string; fields_updated?: string[]; unknowns_resolved?: string[] } }>(
      `/cases/${id}/intake/text`,
      { text, input_type: inputType, search_depth: searchDepth },
    ),

  intakeFile: async (id: string, file: File, inputType = 'auto') => {
    const form = new FormData();
    form.append('file', file);
    form.append('input_type', inputType);
    const res = await fetch(`${BASE}/cases/${id}/intake/file`, {
      method: 'POST',
      body: form,
    });
    if (!res.ok) {
      const body = await res.text();
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

  // Decision log
  getDecisionLog: (id: string) => get<DecisionLogEntry[]>(`/cases/${id}/decision-log`),

  // Agent map
  getAgentMap: () => get<AgentMapData>('/agents/map'),
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
