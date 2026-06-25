import { useEffect, useState } from 'react';
import { api } from '../api/client';

interface DisciplineMatch {
  discipline_id: string;
  strength: string;
  why: string;
}

interface DisciplineMatchesData {
  region_hint: string;
  matched: DisciplineMatch[];
  new_candidate: { display_name: string; reason: string } | null;
  confidence: 'high' | 'medium' | 'low';
  reasoning: string;
}

interface Props {
  caseId: string;
}

const STRENGTH_LABELS: Record<string, { label: string; className: string }> = {
  primary: { label: 'primary', className: 'discipline-strength--primary' },
  secondary: { label: 'secondary', className: 'discipline-strength--secondary' },
  tangential: { label: 'tangential', className: 'discipline-strength--tangential' },
  unknown: { label: 'unknown', className: 'discipline-strength--unknown' },
};

const REGION_LABELS: Record<string, string> = {
  auto: 'Auto',
  ru: 'RU',
  international: 'International',
};

export function DisciplineMatches({ caseId }: Props) {
  const [data, setData] = useState<DisciplineMatchesData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .getDisciplineMatches(caseId)
      .then((d) => {
        if (!cancelled) {
          setData(d);
          setError(null);
        }
      })
      .catch((e) => {
        if (!cancelled) {
          const msg = e instanceof Error ? e.message : String(e);
          if (msg.includes('404')) {
            setError('pending');
          } else {
            setError(msg);
          }
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [caseId]);

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
  return (
    <div className="discipline-matches">
      <div className="discipline-matches-header">
        <h3>Дисциплинарное позиционирование</h3>
        <div className="discipline-matches-meta">
          <span className="discipline-region-badge">
            Регион: {REGION_LABELS[data.region_hint] || data.region_hint}
          </span>
          <span className={`discipline-confidence discipline-confidence--${data.confidence}`}>
            confidence: {data.confidence}
          </span>
        </div>
      </div>
      {data.reasoning && (
        <p className="discipline-matches-reasoning">{data.reasoning}</p>
      )}
      {matched.length === 0 ? (
        <p className="discipline-matches-empty">
          Регистр-матчер не выделил ни одной дисциплины. Это честная позиция —
          выберите регион вручную или подождите следующего прохода с LLM.
        </p>
      ) : (
        <ul className="discipline-matches-list">
          {matched.map((m) => {
            const s = STRENGTH_LABELS[m.strength] || STRENGTH_LABELS.unknown;
            return (
              <li key={m.discipline_id} className="discipline-match-row">
                <div className="discipline-match-head">
                  <code className="discipline-id">{m.discipline_id}</code>
                  <span className={`discipline-strength ${s.className}`}>{s.label}</span>
                </div>
                {m.why && <p className="discipline-match-why">{m.why}</p>}
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
    </div>
  );
}
