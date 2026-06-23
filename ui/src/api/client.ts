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
