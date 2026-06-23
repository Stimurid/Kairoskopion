import { useEffect, useState } from 'react';
import type { HumanDossier, HumanSubsection } from '../types/domain';
import { api } from '../api/client';

interface Props {
  caseId: string;
}

function Subsection({ sub }: { sub: HumanSubsection }) {
  return (
    <div className="human-subsection">
      {sub.title_ru && (
        <div className="human-subsection-head">
          <strong>{sub.title_ru}</strong>
          {sub.badge && (
            <span className={`human-badge human-badge--${sub.badge}`}>
              {sub.badge}
            </span>
          )}
          {sub.status_ru && (
            <em className="human-subsection-status"> · {sub.status_ru}</em>
          )}
        </div>
      )}
      {sub.paragraphs.map((p, i) => (
        <p key={`p${i}`} className="human-paragraph">{p}</p>
      ))}
      {sub.bullets.length > 0 && (
        <ul className="human-bullets">
          {sub.bullets.map((b, i) => <li key={`b${i}`}>{b}</li>)}
        </ul>
      )}
    </div>
  );
}

export function HumanDossierView({ caseId }: Props) {
  const [data, setData] = useState<HumanDossier | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api.getHumanDossier(caseId)
      .then(setData)
      .catch(e => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [caseId]);

  if (loading) {
    return (
      <div className="placeholder-view">
        <p>Собираем авторский разбор…</p>
      </div>
    );
  }
  if (error) {
    return (
      <div className="placeholder-view">
        <p className="error-text">{error}</p>
      </div>
    );
  }
  if (!data) {
    return (
      <div className="placeholder-view">
        <p>Авторский разбор не построен.</p>
      </div>
    );
  }

  return (
    <div className="human-dossier-view">
      <div className="human-dossier-header">
        <h2>Авторский разбор досье</h2>
        <p className="human-dossier-subtitle">
          Статья: «{data.title_ru}» — площадка: {data.venue_name_ru}
          {data.stage_ru ? ` — стадия: ${data.stage_ru}` : ''}
        </p>
        {data.generated_at && (
          <p className="human-dossier-generated">
            Собрано: {data.generated_at}
          </p>
        )}
        <p className="human-dossier-disclaimer">
          Этот разбор — человеческое изложение того, что система знает про
          эту пару статья × площадка. Он не заменяет рецензента и не
          говорит за журнал. Если по какой-то секции системе не хватило
          данных, она говорит об этом прямо, а не дописывает за себя.
        </p>
      </div>

      {data.sections.map(section => (
        <section
          key={section.id}
          className={`human-section human-section--${section.id}`}
        >
          <h3 className="human-section-title">{section.title_ru}</h3>
          {section.paragraphs.map((p, i) => (
            <p key={`p${i}`} className="human-paragraph">{p}</p>
          ))}
          {section.bullets.length > 0 && (
            <ul className="human-bullets">
              {section.bullets.map((b, i) => <li key={`b${i}`}>{b}</li>)}
            </ul>
          )}
          {section.subsections.map((sub, i) => (
            <Subsection key={`sub${i}`} sub={sub} />
          ))}
        </section>
      ))}
    </div>
  );
}
