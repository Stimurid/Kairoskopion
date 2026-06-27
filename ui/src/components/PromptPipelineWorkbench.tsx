import { useState, useEffect, useCallback } from 'react';
import { workbench } from '../api/client';
import type {
  PromptFamilyInfo,
  PipelineStage,
  PipelineRunSummary,
  PipelineNodeInfo,
  PromptRunRecordInfo,
  PromptOverrideInfo,
} from '../api/client';

interface Props {
  caseId: string;
  onClose: () => void;
}

type Tab = 'stages' | 'runs' | 'prompts' | 'overrides';

export function PromptPipelineWorkbench({ caseId, onClose }: Props) {
  const [tab, setTab] = useState<Tab>('stages');
  const [stages, setStages] = useState<PipelineStage[]>([]);
  const [prompts, setPrompts] = useState<PromptFamilyInfo[]>([]);
  const [runs, setRuns] = useState<PipelineRunSummary[]>([]);
  const [overrides, setOverrides] = useState<PromptOverrideInfo[]>([]);
  const [selectedRun, setSelectedRun] = useState<string | null>(null);
  const [nodes, setNodes] = useState<PipelineNodeInfo[]>([]);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [promptRecords, setPromptRecords] = useState<PromptRunRecordInfo[]>([]);
  const [selectedPrompt, setSelectedPrompt] = useState<PromptFamilyInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, p, r, o] = await Promise.all([
        workbench.listStages(),
        workbench.listPrompts(),
        workbench.listRuns(caseId),
        workbench.listOverrides(caseId),
      ]);
      setStages(s);
      setPrompts(p);
      setRuns(r);
      setOverrides(o);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => { load(); }, [load]);

  const loadNodes = useCallback(async (runId: string) => {
    setSelectedRun(runId);
    setSelectedNode(null);
    setPromptRecords([]);
    try {
      const n = await workbench.listNodes(caseId, runId);
      setNodes(n);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [caseId]);

  const loadPromptRecord = useCallback(async (runId: string, nodeId: string) => {
    setSelectedNode(nodeId);
    try {
      const r = await workbench.getNodePrompt(caseId, runId, nodeId);
      setPromptRecords(r);
    } catch {
      setPromptRecords([]);
    }
  }, [caseId]);

  const handleRerunAll = async () => {
    setLoading(true);
    try {
      await workbench.rerunAll(caseId);
      await load();
      setTab('runs');
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  const handleRerunStage = async (stageId: string) => {
    setLoading(true);
    try {
      const lastRun = runs.length > 0 ? runs[runs.length - 1].run_id : undefined;
      await workbench.rerunStage(caseId, stageId, lastRun);
      await load();
      setTab('runs');
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  const handleRerunFrom = async (stageId: string) => {
    setLoading(true);
    try {
      const lastRun = runs.length > 0 ? runs[runs.length - 1].run_id : undefined;
      await workbench.rerunFromStage(caseId, stageId, lastRun);
      await load();
      setTab('runs');
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  const statusColor = (s: string) => {
    switch (s) {
      case 'completed': return 'var(--color-success)';
      case 'failed': return 'var(--color-danger)';
      case 'running': return 'var(--color-warning)';
      case 'pending': return 'var(--text-muted)';
      case 'skipped': return 'var(--text-muted)';
      default: return 'var(--text-secondary)';
    }
  };

  return (
    <div style={{
      background: 'var(--bg-surface)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: 16,
      marginTop: 12,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h3 style={{ margin: 0, color: 'var(--text-primary)', fontSize: 16 }}>
          Pipeline Workbench
        </h3>
        <button onClick={onClose} style={{
          background: 'none', border: 'none', color: 'var(--text-muted)',
          cursor: 'pointer', fontSize: 18,
        }}>×</button>
      </div>

      {error && (
        <div style={{ color: 'var(--color-danger)', marginBottom: 8, fontSize: 13 }}>
          {error}
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 12, borderBottom: '1px solid var(--border)', paddingBottom: 8 }}>
        {(['stages', 'runs', 'prompts', 'overrides'] as Tab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              background: tab === t ? 'var(--bg-hover)' : 'transparent',
              border: tab === t ? '1px solid var(--border-focus)' : '1px solid transparent',
              color: tab === t ? 'var(--text-primary)' : 'var(--text-secondary)',
              borderRadius: 4, padding: '4px 12px', cursor: 'pointer', fontSize: 13,
            }}
          >
            {t === 'stages' ? 'Pipeline Stages' :
             t === 'runs' ? `Runs (${runs.length})` :
             t === 'prompts' ? `Prompts (${prompts.length})` :
             `Overrides (${overrides.length})`}
          </button>
        ))}
        <div style={{ flex: 1 }} />
        <button
          onClick={handleRerunAll}
          disabled={loading}
          style={{
            background: 'var(--color-primary)', color: '#fff', border: 'none',
            borderRadius: 4, padding: '4px 12px', cursor: 'pointer', fontSize: 13,
            opacity: loading ? 0.5 : 1,
          }}
        >
          Rerun All
        </button>
      </div>

      {/* Stages tab */}
      {tab === 'stages' && (
        <div style={{ maxHeight: 400, overflowY: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ color: 'var(--text-muted)', textAlign: 'left' }}>
                <th style={{ padding: '4px 8px' }}>#</th>
                <th style={{ padding: '4px 8px' }}>Stage</th>
                <th style={{ padding: '4px 8px' }}>Producer</th>
                <th style={{ padding: '4px 8px' }}>Prompt</th>
                <th style={{ padding: '4px 8px' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {stages.map((s, i) => (
                <tr key={s.stage_id} style={{ borderTop: '1px solid var(--border)' }}>
                  <td style={{ padding: '4px 8px', color: 'var(--text-muted)' }}>{i + 1}</td>
                  <td style={{ padding: '4px 8px', color: 'var(--text-primary)' }}>{s.label}</td>
                  <td style={{ padding: '4px 8px' }}>
                    <span style={{
                      background: s.producer === 'llm_agent' ? 'var(--badge-claim-bg, #3a2a1a)' : 'var(--bg-raised)',
                      color: s.producer === 'llm_agent' ? 'var(--color-warning)' : 'var(--text-secondary)',
                      padding: '2px 6px', borderRadius: 3, fontSize: 11,
                    }}>
                      {s.producer}
                    </span>
                  </td>
                  <td style={{ padding: '4px 8px', color: 'var(--text-secondary)', fontSize: 12 }}>
                    {s.prompt_family ?? '—'}
                  </td>
                  <td style={{ padding: '4px 8px' }}>
                    <button
                      onClick={() => handleRerunStage(s.stage_id)}
                      disabled={loading}
                      style={{
                        background: 'transparent', border: '1px solid var(--border)',
                        color: 'var(--text-secondary)', borderRadius: 3,
                        padding: '2px 6px', cursor: 'pointer', fontSize: 11, marginRight: 4,
                      }}
                    >Stage</button>
                    <button
                      onClick={() => handleRerunFrom(s.stage_id)}
                      disabled={loading}
                      style={{
                        background: 'transparent', border: '1px solid var(--border)',
                        color: 'var(--text-secondary)', borderRadius: 3,
                        padding: '2px 6px', cursor: 'pointer', fontSize: 11,
                      }}
                    >From here</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Runs tab */}
      {tab === 'runs' && (
        <div style={{ display: 'flex', gap: 12, maxHeight: 500 }}>
          <div style={{ flex: '0 0 280px', overflowY: 'auto' }}>
            {runs.length === 0 && <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No runs yet</div>}
            {runs.map(r => (
              <div
                key={r.run_id}
                onClick={() => loadNodes(r.run_id)}
                style={{
                  padding: '6px 8px', cursor: 'pointer', borderRadius: 4,
                  background: selectedRun === r.run_id ? 'var(--bg-hover)' : 'transparent',
                  borderLeft: selectedRun === r.run_id ? '2px solid var(--border-focus)' : '2px solid transparent',
                  marginBottom: 2,
                }}
              >
                <div style={{ fontSize: 12, color: 'var(--text-primary)' }}>
                  <span style={{ color: statusColor(r.status) }}>{r.status}</span>
                  {' '}{r.trigger}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  {r.run_id.slice(0, 20)}... · {r.node_ids.length} nodes
                </div>
              </div>
            ))}
          </div>
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {selectedRun && nodes.length > 0 && (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                <thead>
                  <tr style={{ color: 'var(--text-muted)', textAlign: 'left' }}>
                    <th style={{ padding: '3px 6px' }}>#</th>
                    <th style={{ padding: '3px 6px' }}>Stage</th>
                    <th style={{ padding: '3px 6px' }}>Status</th>
                    <th style={{ padding: '3px 6px' }}>Producer</th>
                    <th style={{ padding: '3px 6px' }}>Prompt</th>
                  </tr>
                </thead>
                <tbody>
                  {nodes.map(n => (
                    <tr
                      key={n.node_id}
                      onClick={() => n.prompt_family_id && loadPromptRecord(selectedRun!, n.node_id)}
                      style={{
                        borderTop: '1px solid var(--border)',
                        cursor: n.prompt_family_id ? 'pointer' : 'default',
                        background: selectedNode === n.node_id ? 'var(--bg-hover)' : 'transparent',
                      }}
                    >
                      <td style={{ padding: '3px 6px', color: 'var(--text-muted)' }}>{n.order_index + 1}</td>
                      <td style={{ padding: '3px 6px', color: 'var(--text-primary)' }}>{n.stage_label}</td>
                      <td style={{ padding: '3px 6px', color: statusColor(n.status) }}>{n.status}</td>
                      <td style={{ padding: '3px 6px', color: 'var(--text-secondary)' }}>{n.producer_type}</td>
                      <td style={{ padding: '3px 6px', color: 'var(--text-muted)', fontSize: 11 }}>
                        {n.prompt_family_id ?? '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {selectedNode && promptRecords.length > 0 && (
              <div style={{ marginTop: 12, padding: 8, background: 'var(--bg-raised)', borderRadius: 4 }}>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Prompt Record</div>
                {promptRecords.map(pr => (
                  <div key={pr.prompt_run_id}>
                    <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>
                      Family: {pr.prompt_family_id} · Hash: {pr.prompt_version_hash}
                    </div>
                    <details style={{ marginBottom: 6 }}>
                      <summary style={{ cursor: 'pointer', color: 'var(--text-secondary)', fontSize: 12 }}>
                        System Prompt
                      </summary>
                      <pre style={{
                        background: 'var(--bg-input)', padding: 8, borderRadius: 4,
                        fontSize: 11, color: 'var(--text-primary)', whiteSpace: 'pre-wrap',
                        maxHeight: 200, overflowY: 'auto',
                      }}>
                        {pr.rendered_system_prompt || '(empty)'}
                      </pre>
                    </details>
                    <details>
                      <summary style={{ cursor: 'pointer', color: 'var(--text-secondary)', fontSize: 12 }}>
                        User Prompt
                      </summary>
                      <pre style={{
                        background: 'var(--bg-input)', padding: 8, borderRadius: 4,
                        fontSize: 11, color: 'var(--text-primary)', whiteSpace: 'pre-wrap',
                        maxHeight: 200, overflowY: 'auto',
                      }}>
                        {pr.rendered_user_prompt || '(empty)'}
                      </pre>
                    </details>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Prompts tab */}
      {tab === 'prompts' && (
        <div style={{ display: 'flex', gap: 12, maxHeight: 500 }}>
          <div style={{ flex: '0 0 240px', overflowY: 'auto' }}>
            {prompts.map(p => (
              <div
                key={p.prompt_family_id}
                onClick={() => setSelectedPrompt(p)}
                style={{
                  padding: '4px 8px', cursor: 'pointer', borderRadius: 4,
                  background: selectedPrompt?.prompt_family_id === p.prompt_family_id ? 'var(--bg-hover)' : 'transparent',
                  marginBottom: 2,
                }}
              >
                <div style={{ fontSize: 12, color: 'var(--text-primary)' }}>{p.prompt_family_id}</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                  {p.agent_ref ?? 'service'} · {p.version_hash}
                </div>
              </div>
            ))}
          </div>
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {selectedPrompt && (
              <div>
                <h4 style={{ margin: '0 0 8px', color: 'var(--text-primary)', fontSize: 14 }}>
                  {selectedPrompt.prompt_family_id}
                </h4>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>
                  {selectedPrompt.description}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8 }}>
                  Agent: {selectedPrompt.agent_ref ?? '—'} ·
                  Schema: {selectedPrompt.has_schema ? selectedPrompt.schema_ref : 'none'} ·
                  Hash: {selectedPrompt.version_hash}
                </div>
                {selectedPrompt.system_prompt && (
                  <details open style={{ marginBottom: 8 }}>
                    <summary style={{ cursor: 'pointer', color: 'var(--text-secondary)', fontSize: 12 }}>
                      System Prompt
                    </summary>
                    <pre style={{
                      background: 'var(--bg-input)', padding: 8, borderRadius: 4,
                      fontSize: 11, color: 'var(--text-primary)', whiteSpace: 'pre-wrap',
                      maxHeight: 300, overflowY: 'auto',
                    }}>
                      {selectedPrompt.system_prompt}
                    </pre>
                  </details>
                )}
                {selectedPrompt.user_template && (
                  <details style={{ marginBottom: 8 }}>
                    <summary style={{ cursor: 'pointer', color: 'var(--text-secondary)', fontSize: 12 }}>
                      User Template
                    </summary>
                    <pre style={{
                      background: 'var(--bg-input)', padding: 8, borderRadius: 4,
                      fontSize: 11, color: 'var(--text-primary)', whiteSpace: 'pre-wrap',
                      maxHeight: 300, overflowY: 'auto',
                    }}>
                      {selectedPrompt.user_template}
                    </pre>
                  </details>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Overrides tab */}
      {tab === 'overrides' && (
        <div style={{ maxHeight: 400, overflowY: 'auto' }}>
          {overrides.length === 0 && (
            <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>
              No prompt overrides for this case. Create one from the Prompts tab.
            </div>
          )}
          {overrides.map(o => (
            <div key={o.override_id} style={{
              padding: 8, marginBottom: 6, background: 'var(--bg-raised)',
              borderRadius: 4, border: '1px solid var(--border)',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 13, color: 'var(--text-primary)' }}>
                  {o.base_prompt_family_id}
                </span>
                <span style={{
                  fontSize: 11, padding: '1px 6px', borderRadius: 3,
                  background: o.status === 'active' ? 'var(--badge-fact-bg)' : 'var(--bg-hover)',
                  color: o.status === 'active' ? 'var(--color-success)' : 'var(--text-muted)',
                }}>
                  {o.status}
                </span>
              </div>
              {o.notes && <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4 }}>{o.notes}</div>}
              {o.edited_system_prompt && (
                <details style={{ marginTop: 4 }}>
                  <summary style={{ cursor: 'pointer', color: 'var(--text-muted)', fontSize: 11 }}>
                    Edited system prompt
                  </summary>
                  <pre style={{
                    background: 'var(--bg-input)', padding: 6, borderRadius: 4,
                    fontSize: 10, color: 'var(--text-primary)', whiteSpace: 'pre-wrap',
                    maxHeight: 150, overflowY: 'auto',
                  }}>
                    {o.edited_system_prompt}
                  </pre>
                </details>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
