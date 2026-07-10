import { useState, useEffect, useCallback, useMemo } from 'react';
import { api } from '../api/client';
import type {
  AgentMapData,
  AgentMapAgent,
  AgentMapWorkflow,
  AgentMapPrompt,
} from '../api/client';

// --- Agent type classification ---

type AgentKind = 'llm' | 'orphaned' | 'stub' | 'deterministic';

function classifyAgent(a: AgentMapAgent): AgentKind {
  if (a.has_real_llm) return 'llm';
  if (a.has_orphaned_prompt) return 'orphaned';
  if (a.implementation_status === 'contract_only') return 'stub';
  return 'deterministic';
}

const KIND_COLORS: Record<AgentKind, string> = {
  llm: '#34c77b',
  orphaned: '#f0a040',
  stub: '#e5534b',
  deterministic: '#5d6375',
};

const KIND_BG: Record<AgentKind, string> = {
  llm: '#1a3a2a',
  orphaned: '#3a2f1a',
  stub: '#3a1a1a',
  deterministic: '#252a38',
};

const KIND_LABELS: Record<AgentKind, string> = {
  llm: 'LLM-агент',
  orphaned: 'Осиротевший промпт',
  stub: 'Только контракт',
  deterministic: 'Детерминированный',
};

// --- Prompt section detection (SOP / Agentum) ---

interface PromptSection {
  title: string;
  kind: 'sop' | 'agentum' | 'standard';
  startLine: number;
  endLine: number;
  content: string;
}

const SOP_MARKERS = [
  'ЦЕЛЬ И КОНТЕКСТ', 'ВХОДНЫЕ ДАННЫЕ', 'АЛГОРИТМ', 'СТОП-СЛОВА',
  'ЗАПРЕЩЕНО', 'ФОРМАТ ВЫВОДА', 'КРИТЕРИИ КАЧЕСТВА', 'ПРИМЕРЫ',
  'GOAL AND CONTEXT', 'INPUT DATA', 'ALGORITHM', 'STOP WORDS',
  'FORBIDDEN', 'OUTPUT FORMAT', 'QUALITY CRITERIA', 'EXAMPLES',
];

const AGENTUM_MARKERS = [
  'ROLE', 'PERSONA', 'ЗАДАЧА', 'TASK', 'КОНТЕКСТ', 'CONTEXT',
  'ОГРАНИЧЕНИЯ', 'CONSTRAINTS', 'ИНСТРУКЦИЯ', 'INSTRUCTION',
  'ОТВЕТСТВЕННОСТЬ', 'RESPONSIBILITY', 'КОМПЕТЕНЦИЯ', 'COMPETENCY',
];

function detectPromptSections(text: string): PromptSection[] {
  if (!text) return [];
  const lines = text.split('\n');
  const sections: PromptSection[] = [];
  let current: Partial<PromptSection> | null = null;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    const upper = line.replace(/^#+\s*/, '').replace(/[:\-—]/g, '').trim().toUpperCase();

    let matched = false;
    for (const marker of SOP_MARKERS) {
      if (upper.includes(marker)) {
        if (current) {
          current.endLine = i - 1;
          current.content = lines.slice(current.startLine!, i).join('\n');
          sections.push(current as PromptSection);
        }
        current = { title: line, kind: 'sop', startLine: i };
        matched = true;
        break;
      }
    }
    if (!matched) {
      for (const marker of AGENTUM_MARKERS) {
        if (upper.includes(marker) && (line.startsWith('#') || line.startsWith('**') || upper === line.replace(/^#+\s*/, '').trim())) {
          if (current) {
            current.endLine = i - 1;
            current.content = lines.slice(current.startLine!, i).join('\n');
            sections.push(current as PromptSection);
          }
          current = { title: line, kind: 'agentum', startLine: i };
          matched = true;
          break;
        }
      }
    }
  }

  if (current) {
    current.endLine = lines.length - 1;
    current.content = lines.slice(current.startLine!, lines.length).join('\n');
    sections.push(current as PromptSection);
  }

  return sections;
}

// --- Main Component ---

export function AgentMap() {
  const [data, setData] = useState<AgentMapData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<AgentMapAgent | null>(null);
  const [promptPopup, setPromptPopup] = useState<AgentMapPrompt | null>(null);
  const [activeWorkflow, setActiveWorkflow] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.getAgentMap();
      setData(result);
      if (result.workflows.length > 0 && !activeWorkflow) {
        setActiveWorkflow(result.workflows[0].workflow_id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось загрузить карту агентов');
    } finally {
      setLoading(false);
    }
  }, [activeWorkflow]);

  useEffect(() => { loadData(); }, []);

  const agentsByRole = useMemo(() => {
    if (!data) return {};
    const map: Record<string, AgentMapAgent> = {};
    for (const a of data.agents) map[a.role_id] = a;
    return map;
  }, [data]);

  const currentWorkflow = useMemo(() => {
    if (!data || !activeWorkflow) return null;
    return data.workflows.find(w => w.workflow_id === activeWorkflow) ?? null;
  }, [data, activeWorkflow]);

  const agentsByLayer = useMemo(() => {
    if (!data) return {};
    const layers: Record<string, AgentMapAgent[]> = {};
    for (const a of data.agents) {
      const key = a.layer || 'unknown';
      if (!layers[key]) layers[key] = [];
      layers[key].push(a);
    }
    return layers;
  }, [data]);

  if (loading) {
    return <div className="agent-map-loading">Загрузка карты агентов…</div>;
  }

  if (error) {
    return (
      <div className="agent-map-error">
        <p>{error}</p>
        <button className="btn btn-primary" onClick={loadData}>Повторить</button>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="agent-map">
      {/* Header with stats and refresh */}
      <div className="agent-map-header">
        <div className="agent-map-title">
          <h2>Карта архитектуры агентов</h2>
          <button className="btn btn-small" onClick={loadData} title="Обновить">↻ Обновить</button>
        </div>
        <div className="agent-map-stats">
          <span className="agent-map-stat">
            <span className="stat-dot" style={{ background: KIND_COLORS.llm }} />
            {data.agents.filter(a => a.has_real_llm).length} LLM
          </span>
          <span className="agent-map-stat">
            <span className="stat-dot" style={{ background: KIND_COLORS.orphaned }} />
            {data.agents.filter(a => a.has_orphaned_prompt).length} Orphaned
          </span>
          <span className="agent-map-stat">
            <span className="stat-dot" style={{ background: KIND_COLORS.stub }} />
            {data.agents.filter(a => a.implementation_status === 'contract_only').length} Stubs
          </span>
          <span className="agent-map-stat">
            <span className="stat-dot" style={{ background: KIND_COLORS.deterministic }} />
            {data.agents.filter(a => classifyAgent(a) === 'deterministic').length} Deterministic
          </span>
          <span className="agent-map-stat agent-map-stat--llm-status">
            LLM: {(data.llm as Record<string, string>)?.status === 'configured' ? '● Активен' : '○ Выкл'}
          </span>
        </div>
      </div>

      {/* Workflow pipeline selector */}
      <div className="agent-map-workflow-tabs">
        <span className="workflow-tabs-label">Pipelines:</span>
        {data.workflows.map(w => (
          <button
            key={w.workflow_id}
            className={`workflow-tab ${activeWorkflow === w.workflow_id ? 'workflow-tab--active' : ''}`}
            onClick={() => setActiveWorkflow(w.workflow_id)}
          >
            {w.display_name}
            <span className="workflow-tab-steps">{w.steps.length} steps</span>
          </button>
        ))}
        <button
          className={`workflow-tab ${activeWorkflow === '__all__' ? 'workflow-tab--active' : ''}`}
          onClick={() => setActiveWorkflow('__all__')}
        >
          Все агенты (по слоям)
        </button>
      </div>

      {/* Pipeline visualization or layer view */}
      {activeWorkflow === '__all__' ? (
        <LayerView
          layers={agentsByLayer}
          onSelectAgent={setSelectedAgent}
          selectedAgent={selectedAgent}
        />
      ) : currentWorkflow ? (
        <PipelineView
          workflow={currentWorkflow}
          agents={agentsByRole}
          prompts={data.prompts}
          onSelectAgent={setSelectedAgent}
          selectedAgent={selectedAgent}
        />
      ) : null}

      {/* Agent detail card */}
      {selectedAgent && (
        <AgentDetailCard
          agent={selectedAgent}
          prompts={data.prompts}
          workflows={data.workflows}
          onClose={() => setSelectedAgent(null)}
          onShowPrompt={setPromptPopup}
        />
      )}

      {/* Prompt full-screen popup */}
      {promptPopup && (
        <PromptPopup
          prompt={promptPopup}
          onClose={() => setPromptPopup(null)}
        />
      )}
    </div>
  );
}

// --- Pipeline view: n8n-style horizontal flow ---

function PipelineView({
  workflow,
  agents,
  prompts,
  onSelectAgent,
  selectedAgent,
}: {
  workflow: AgentMapWorkflow;
  agents: Record<string, AgentMapAgent>;
  prompts: Record<string, AgentMapPrompt>;
  onSelectAgent: (a: AgentMapAgent) => void;
  selectedAgent: AgentMapAgent | null;
}) {
  return (
    <div className="pipeline-view">
      <div className="pipeline-header">
        <h3>{workflow.display_name}</h3>
        <span className="pipeline-desc">{workflow.description}</span>
        <span className={`pipeline-status pipeline-status--${workflow.implementation_status}`}>
          {workflow.implementation_status}
        </span>
      </div>
      <div className="pipeline-flow">
        {workflow.steps.map((step, i) => {
          const agent = agents[step.agent_role_id];
          const kind = agent ? classifyAgent(agent) : 'stub';
          const hasPrompt = agent?.prompt_family_ids?.some(id => prompts[id]);
          const isSelected = selectedAgent?.role_id === step.agent_role_id;

          return (
            <div key={i} className="pipeline-step-wrapper">
              {i > 0 && (
                <div className="pipeline-connector">
                  <svg width="40" height="24" viewBox="0 0 40 24">
                    <line x1="0" y1="12" x2="30" y2="12" stroke="#3a3f50" strokeWidth="2" />
                    <polygon points="30,6 40,12 30,18" fill="#3a3f50" />
                  </svg>
                </div>
              )}
              <button
                className={`pipeline-node pipeline-node--${kind} ${isSelected ? 'pipeline-node--selected' : ''}`}
                onClick={() => agent && onSelectAgent(agent)}
                title={step.description || step.agent_role_id}
              >
                <div className="pipeline-node-index">{i + 1}</div>
                <div className="pipeline-node-name">
                  {agent?.display_name || step.agent_role_id}
                </div>
                <div className="pipeline-node-meta">
                  <span className="pipeline-node-kind" style={{ color: KIND_COLORS[kind] }}>
                    {KIND_LABELS[kind]}
                  </span>
                  {hasPrompt && <span className="pipeline-node-prompt-dot" title="Has prompt">P</span>}
                </div>
                <div className="pipeline-node-output">
                  → {step.output_key}
                </div>
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// --- Layer view: grouped by architectural layer ---

function LayerView({
  layers,
  onSelectAgent,
  selectedAgent,
}: {
  layers: Record<string, AgentMapAgent[]>;
  onSelectAgent: (a: AgentMapAgent) => void;
  selectedAgent: AgentMapAgent | null;
}) {
  const layerOrder = [
    'L1_extraction', 'L1_profiling', 'L2_matching', 'L2_discovery',
    'L3_orchestration', 'L4_evidence', 'L5_meta',
  ];

  const sortedLayers = Object.entries(layers).sort(([a], [b]) => {
    const ai = layerOrder.indexOf(a);
    const bi = layerOrder.indexOf(b);
    return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi);
  });

  return (
    <div className="layer-view">
      {sortedLayers.map(([layerName, agents]) => (
        <div key={layerName} className="layer-group">
          <div className="layer-header">
            <span className="layer-name">{layerName}</span>
            <span className="layer-count">{agents.length} agents</span>
          </div>
          <div className="layer-agents">
            {agents.map(agent => {
              const kind = classifyAgent(agent);
              const isSelected = selectedAgent?.role_id === agent.role_id;
              return (
                <button
                  key={agent.role_id}
                  className={`layer-agent layer-agent--${kind} ${isSelected ? 'layer-agent--selected' : ''}`}
                  onClick={() => onSelectAgent(agent)}
                >
                  <span className="layer-agent-dot" style={{ background: KIND_COLORS[kind] }} />
                  <span className="layer-agent-name">{agent.display_name}</span>
                  <span className="layer-agent-kind">{KIND_LABELS[kind]}</span>
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

// --- Agent detail card ---

function AgentDetailCard({
  agent,
  prompts,
  workflows,
  onClose,
  onShowPrompt,
}: {
  agent: AgentMapAgent;
  prompts: Record<string, AgentMapPrompt>;
  workflows: AgentMapWorkflow[];
  onClose: () => void;
  onShowPrompt: (p: AgentMapPrompt) => void;
}) {
  const kind = classifyAgent(agent);

  const participatingWorkflows = workflows.filter(w =>
    w.steps.some(s => s.agent_role_id === agent.role_id)
  );

  const agentPrompts = agent.prompt_family_ids
    .map(id => prompts[id])
    .filter(Boolean);

  const inputFields = Object.entries(agent.input_contract || {});
  const outputFields = Object.entries(agent.output_contract || {});

  return (
    <div className="agent-detail-card">
      <div className="agent-detail-header">
        <div className="agent-detail-title-row">
          <span className="agent-detail-dot" style={{ background: KIND_COLORS[kind] }} />
          <h3>{agent.display_name}</h3>
          <span className="agent-detail-badge" style={{ background: KIND_BG[kind], color: KIND_COLORS[kind] }}>
            {KIND_LABELS[kind]}
          </span>
        </div>
        <button className="agent-detail-close" onClick={onClose}>✕</button>
      </div>

      <div className="agent-detail-body">
        <div className="agent-detail-section">
          <div className="agent-detail-row">
            <span className="agent-detail-label">Role ID</span>
            <code className="agent-detail-value">{agent.role_id}</code>
          </div>
          <div className="agent-detail-row">
            <span className="agent-detail-label">Layer</span>
            <span className="agent-detail-value">{agent.layer}</span>
          </div>
          <div className="agent-detail-row">
            <span className="agent-detail-label">Status</span>
            <span className="agent-detail-value">{agent.implementation_status}</span>
          </div>
          <div className="agent-detail-row">
            <span className="agent-detail-label">Execution</span>
            <span className="agent-detail-value">{agent.execution_mode}</span>
          </div>
          <div className="agent-detail-row">
            <span className="agent-detail-label">MVP Phase</span>
            <span className="agent-detail-value">{agent.mvp_phase}</span>
          </div>
        </div>

        {participatingWorkflows.length > 0 && (
          <div className="agent-detail-section">
            <h4>Pipelines</h4>
            {participatingWorkflows.map(w => {
              const stepIdx = w.steps.findIndex(s => s.agent_role_id === agent.role_id);
              return (
                <div key={w.workflow_id} className="agent-pipeline-ref">
                  <span className="agent-pipeline-name">{w.display_name}</span>
                  <span className="agent-pipeline-pos">Step {stepIdx + 1} of {w.steps.length}</span>
                </div>
              );
            })}
          </div>
        )}

        {(inputFields.length > 0 || outputFields.length > 0) && (
          <div className="agent-detail-section">
            <h4>Contract</h4>
            {inputFields.length > 0 && (
              <div className="agent-contract">
                <span className="contract-dir">IN:</span>
                {inputFields.map(([k, v]) => (
                  <code key={k} className="contract-field">{k}: {v}</code>
                ))}
              </div>
            )}
            {outputFields.length > 0 && (
              <div className="agent-contract">
                <span className="contract-dir">OUT:</span>
                {outputFields.map(([k, v]) => (
                  <code key={k} className="contract-field">{k}: {v}</code>
                ))}
              </div>
            )}
          </div>
        )}

        {agentPrompts.length > 0 && (
          <div className="agent-detail-section">
            <h4>Prompts</h4>
            {agentPrompts.map(p => (
              <div key={p.family_id} className="agent-prompt-ref">
                <div className="agent-prompt-info">
                  <span className="agent-prompt-id">{p.family_id}</span>
                  <span className="agent-prompt-meta">
                    v{p.version} · {p.system_prompt_lines} sys lines · {p.user_prompt_lines} usr lines
                  </span>
                  {p.purpose && <span className="agent-prompt-purpose">{p.purpose}</span>}
                </div>
                <button
                  className="btn btn-small btn-prompt"
                  onClick={() => onShowPrompt(p)}
                >
                  Показать промпт
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// --- Prompt full-screen popup ---

function PromptPopup({
  prompt,
  onClose,
}: {
  prompt: AgentMapPrompt;
  onClose: () => void;
}) {
  const [activeTab, setActiveTab] = useState<'system' | 'user'>('system');

  const text = activeTab === 'system' ? prompt.system_prompt : prompt.user_prompt_template;
  const sections = useMemo(() => detectPromptSections(text), [text]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  return (
    <div className="prompt-popup-overlay" onClick={onClose}>
      <div className="prompt-popup" onClick={e => e.stopPropagation()}>
        <div className="prompt-popup-header">
          <div className="prompt-popup-title">
            <h3>{prompt.family_id}</h3>
            <span className="prompt-popup-meta">
              Agent: {prompt.agent_role_id} · v{prompt.version}
            </span>
          </div>
          <button className="prompt-popup-close" onClick={onClose}>✕</button>
        </div>

        <div className="prompt-popup-tabs">
          <button
            className={`prompt-tab ${activeTab === 'system' ? 'prompt-tab--active' : ''}`}
            onClick={() => setActiveTab('system')}
          >
            System Prompt ({prompt.system_prompt_lines} lines)
          </button>
          <button
            className={`prompt-tab ${activeTab === 'user' ? 'prompt-tab--active' : ''}`}
            onClick={() => setActiveTab('user')}
          >
            User Template ({prompt.user_prompt_lines} lines)
          </button>
        </div>

        {prompt.output_schema_fields.length > 0 && (
          <div className="prompt-popup-schema">
            <span className="prompt-schema-label">Output schema:</span>
            {prompt.output_schema_fields.map(f => (
              <code key={f} className="prompt-schema-field">{f}</code>
            ))}
          </div>
        )}

        {prompt.forbidden_behaviors && prompt.forbidden_behaviors.length > 0 && (
          <div className="prompt-popup-forbidden">
            <span className="prompt-forbidden-label">Forbidden:</span>
            {prompt.forbidden_behaviors.map((b, i) => (
              <span key={i} className="prompt-forbidden-item">{b}</span>
            ))}
          </div>
        )}

        <div className="prompt-popup-body">
          {sections.length > 0 ? (
            <HighlightedPromptText text={text} sections={sections} />
          ) : (
            <pre className="prompt-raw">{text || '(empty)'}</pre>
          )}
        </div>
      </div>
    </div>
  );
}

// --- Highlighted prompt text with section markers ---

function HighlightedPromptText({
  text,
  sections,
}: {
  text: string;
  sections: PromptSection[];
}) {
  const lines = text.split('\n');

  const sectionByLine: Record<number, PromptSection> = {};
  for (const s of sections) {
    for (let i = s.startLine; i <= s.endLine; i++) {
      sectionByLine[i] = s;
    }
  }

  return (
    <div className="prompt-highlighted">
      {lines.map((line, i) => {
        const section = sectionByLine[i];
        const isHeader = section && section.startLine === i;
        let className = 'prompt-line';
        if (section) {
          className += ` prompt-line--${section.kind}`;
          if (isHeader) className += ' prompt-line--section-header';
        }
        return (
          <div key={i} className={className}>
            <span className="prompt-line-num">{i + 1}</span>
            {isHeader && (
              <span className={`prompt-section-badge prompt-section-badge--${section.kind}`}>
                {section.kind === 'sop' ? 'SOP' : 'Agentum'}
              </span>
            )}
            <span className="prompt-line-text">{line || ' '}</span>
          </div>
        );
      })}
    </div>
  );
}
