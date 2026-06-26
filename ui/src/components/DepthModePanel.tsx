import { useState, useEffect } from 'react';
import { api } from '../api/client';

interface Props {
  caseId: string;
}

const MODES = [
  { value: 'quick', label: 'Быстрый', desc: 'Только локальные данные' },
  { value: 'standard', label: 'Стандартный', desc: 'Базовые адаптеры + 1 LLM' },
  { value: 'deep', label: 'Глубокий', desc: 'Полный обход адаптеров + мульти-LLM' },
  { value: 'exhaustive', label: 'Исчерпывающий', desc: 'Все источники + корпусный анализ' },
];

export function DepthModePanel({ caseId }: Props) {
  const [mode, setMode] = useState('standard');
  const [estimate, setEstimate] = useState<Record<string, unknown> | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.getCostEstimate(caseId).then(setEstimate).catch(() => {});
  }, [caseId]);

  useEffect(() => {
    if (estimate && typeof estimate.depth_mode === 'string') {
      setMode(estimate.depth_mode);
    }
  }, [estimate]);

  const handleSelect = async (m: string) => {
    setSaving(true);
    try {
      await api.setDepthMode(caseId, m);
      setMode(m);
      const est = await api.getCostEstimate(caseId);
      setEstimate(est);
    } catch { /* ignore */ }
    setSaving(false);
  };

  const profile = (estimate as { profile?: Record<string, unknown> })?.profile;

  return (
    <div className="depth-mode-panel">
      <h3>Глубина анализа</h3>
      <div className="depth-mode-options">
        {MODES.map((m) => (
          <button
            key={m.value}
            className={`depth-btn ${mode === m.value ? 'active' : ''}`}
            onClick={() => handleSelect(m.value)}
            disabled={saving}
          >
            <strong>{m.label}</strong>
            <span className="depth-desc">{m.desc}</span>
          </button>
        ))}
      </div>
      {profile && (
        <div className="cost-estimate">
          <span>Адаптеры: {String(profile.adapter_calls ?? 0)}</span>
          <span>LLM: {String(profile.llm_calls ?? 0)}</span>
          <span>~{String(profile.estimated_seconds ?? 0)}с</span>
        </div>
      )}
    </div>
  );
}
