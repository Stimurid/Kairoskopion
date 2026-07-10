import { useEffect, useState, useCallback } from 'react';
import { api } from '../api/client';

interface DisciplineMatch {
  discipline_id: string;
  display_name?: string;
  strength: string;
  why: string;
  supporting_evidence?: string[];
  contradicting_evidence?: string[];
  relation_type?: string;
}

interface DisciplineMatchesData {
  region_hint: string;
  matched: DisciplineMatch[];
  new_candidate: { display_name: string; reason: string } | null;
  confidence: 'high' | 'medium' | 'low';
  reasoning: string;
  source?: string;
}

interface Props {
  caseId: string;
}

const STRENGTH_LABELS: Record<string, { label: string; className: string }> = {
  primary: { label: 'Основное поле', className: 'discipline-strength--primary' },
  strong: { label: 'Сильное соответствие', className: 'discipline-strength--primary' },
  secondary: { label: 'Смежная область', className: 'discipline-strength--secondary' },
  partial: { label: 'Частичное соответствие', className: 'discipline-strength--secondary' },
  tangential: { label: 'Слабое боковое соответствие', className: 'discipline-strength--tangential' },
  weak: { label: 'Слабое соответствие', className: 'discipline-strength--tangential' },
  unknown: { label: 'Не определено', className: 'discipline-strength--unknown' },
};

const CONFIDENCE_LABELS: Record<string, string> = {
  high: 'высокая',
  medium: 'средняя',
  low: 'низкая',
};

const REGION_LABELS: Record<string, string> = {
  auto: 'Авто',
  ru: 'Россия',
  international: 'Международный',
};

export function DisciplineMatches({ caseId }: Props) {
  const [data, setData] = useState<DisciplineMatchesData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [rerunComment, setRerunComment] = useState('');
  const [rerunning, setRerunning] = useState(false);

  const fetchData = useCallback(() => {
    setLoading(true);
    api
      .getDisciplineMatches(caseId)
      .then((d) => {
        setData(d);
        setError(null);
      })
      .catch((e) => {
        const msg = e instanceof Error ? e.message : String(e);
        if (msg.includes('404')) {
          setError('pending');
        } else {
          setError(msg);
        }
      })
      .finally(() => setLoading(false));
  }, [caseId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleRerun = useCallback(async () => {
    setRerunning(true);
    try {
      await api.rerunDisciplineAnalysis(caseId, rerunComment);
      setRerunComment('');
      fetchData();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRerunning(false);
    }
  }, [caseId, rerunComment, fetchData]);

  const toggleExpand = useCallback((id: string) => {
    setExpanded(prev => ({ ...prev, [id]: !prev[id] }));
  }, []);

  if (loading) {
    return <div className="discipline-matches discipline-matches--loading">Загрузка дисциплин…</div>;
  }
  if (error === 'pending') {
    return (
      <div className="discipline-matches discipline-matches--pending">
        Дисциплинарный матчер ещё не запускался — сначала отправьте текст через ввод.
      </div>
    );
  }
  if (error || !data) {
    return <div className="discipline-matches discipline-matches--error">{error || 'Нет данных'}</div>;
  }

  const matched = data.matched || [];
  const isKeywordOnly = data.source === 'keyword_fallback' || data.source === 'deterministic';
  return (
    <div className="discipline-matches">
      <div className="discipline-matches-header">
        <h3>Дисциплинарное позиционирование</h3>
        <div className="discipline-matches-meta">
          <span className="discipline-region-badge">
            Регион: {REGION_LABELS[data.region_hint] || data.region_hint}
          </span>
          <span className={`discipline-confidence discipline-confidence--${data.confidence}`}>
            Уверенность: {CONFIDENCE_LABELS[data.confidence] || data.confidence}
          </span>
          {isKeywordOnly && (
            <span className="discipline-source-badge discipline-source-badge--keyword">
              Только ключевые слова — требуется LLM-анализ
            </span>
          )}
        </div>
      </div>
      {data.reasoning && (
        <p className="discipline-matches-reasoning">{data.reasoning}</p>
      )}
      {matched.length === 0 ? (
        <p className="discipline-matches-empty">
          Регистр-матчер не выделил ни одной дисциплины. Это честная позиция —
          запустите повторный анализ с помощью LLM ниже.
        </p>
      ) : (
        <ul className="discipline-matches-list">
          {matched.map((m, idx) => {
            const s = STRENGTH_LABELS[m.strength] || STRENGTH_LABELS.unknown;
            const isOpen = expanded[m.discipline_id];
            return (
              <li key={m.discipline_id} className="discipline-match-row">
                <div className="discipline-match-head" onClick={() => toggleExpand(m.discipline_id)} style={{ cursor: 'pointer' }}>
                  <span className="discipline-rank">#{idx + 1}</span>
                  <div className="discipline-match-names">
                    {m.display_name && (
                      <span className="discipline-display-name">{m.display_name}</span>
                    )}
                    <code className="discipline-id">{m.discipline_id}</code>
                  </div>
                  <span className={`discipline-strength ${s.className}`}>{s.label}</span>
                  <span className="discipline-expand-icon">{isOpen ? '▾' : '▸'}</span>
                </div>
                {m.why && <p className="discipline-match-why">{m.why}</p>}
                {isOpen && (
                  <div className="discipline-match-detail">
                    {m.supporting_evidence && m.supporting_evidence.length > 0 && (
                      <div className="discipline-evidence discipline-evidence--supporting">
                        <strong>Признаки, поддерживающие выбор:</strong>
                        <ul>{m.supporting_evidence.map((e, i) => <li key={i}>{e}</li>)}</ul>
                      </div>
                    )}
                    {m.contradicting_evidence && m.contradicting_evidence.length > 0 && (
                      <div className="discipline-evidence discipline-evidence--contradicting">
                        <strong>Признаки, противоречащие выбору:</strong>
                        <ul>{m.contradicting_evidence.map((e, i) => <li key={i}>{e}</li>)}</ul>
                      </div>
                    )}
                    {m.relation_type && (
                      <p className="discipline-relation-type">
                        <strong>Тип связи:</strong> {m.relation_type}
                      </p>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
      {data.new_candidate && (
        <div className="discipline-new-candidate">
          <strong>LLM предложил нового кандидата:</strong> {data.new_candidate.display_name}
          <p className="discipline-match-why">{data.new_candidate.reason}</p>
        </div>
      )}

      <div className="discipline-rerun-section">
        <h4>Повторный анализ с помощью LLM</h4>
        <textarea
          className="discipline-rerun-comment"
          placeholder="Комментарий: гипотеза, аргумент, желаемая дисциплинарная рамка, указание на автора/традицию…"
          value={rerunComment}
          onChange={e => setRerunComment(e.target.value)}
          rows={3}
        />
        <button
          className="btn btn-primary"
          onClick={handleRerun}
          disabled={rerunning}
        >
          {rerunning ? 'Анализ…' : 'Повторить анализ с помощью LLM'}
        </button>
      </div>
    </div>
  );
}
