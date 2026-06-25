import { useEffect, useState } from 'react';
import type {
  HumanDossier,
  HumanSubsection,
  HumanSourceHeader,
  HumanTechnicalFooter,
} from '../types/domain';
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

function SourceHeader({ h }: { h: HumanSourceHeader }) {
  return (
    <div className="human-source-header">
      <div className="human-source-row">
        <span className="human-source-label">Источник:</span>
        <span className="human-source-value">{h.source_filename_ru}</span>
      </div>
      <div className="human-source-row">
        <span className="human-source-label">Тип:</span>
        <span className="human-source-value">{h.source_type_ru}</span>
      </div>
      <div className="human-source-row">
        <span className="human-source-label">Объём:</span>
        <span className="human-source-value">{h.size_ru}</span>
      </div>
      <div className="human-source-row">
        <span className="human-source-label">Заголовок в документе:</span>
        <span className="human-source-value">{h.document_title_ru}</span>
      </div>
      <div className="human-source-row">
        <span className="human-source-label">Case:</span>
        <span className="human-source-value">
          <code>{h.case_id_ru}</code>
        </span>
      </div>
      <div className="human-source-row">
        <span className="human-source-label">Собрано:</span>
        <span className="human-source-value">{h.generated_at_ru}</span>
      </div>
      {h.notes.map((n, i) => (
        <p key={i} className="human-source-note">{n}</p>
      ))}
    </div>
  );
}

function renderKVBlock(
  title: string,
  data: Record<string, string | number | boolean | null | undefined>,
) {
  const rows = Object.entries(data).filter(([, v]) => v !== null && v !== undefined && v !== '');
  if (rows.length === 0) return null;
  return (
    <div className="tech-footer-block">
      <h4>{title}</h4>
      <table className="tech-footer-table">
        <tbody>
          {rows.map(([k, v]) => (
            <tr key={k}>
              <td><code>{k}</code></td>
              <td>{String(v)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TechnicalFooter({ f }: { f: HumanTechnicalFooter }) {
  return (
    <details className="human-technical-footer">
      <summary>Технические сведения (для разработчика — свёрнуто)</summary>
      <div className="tech-footer-disclaimer">
        Этот блок не предназначен для авторского чтения. Он содержит
        provenance / диагностику / quality gates. Сырой ответ LLM здесь не
        хранится и не показывается.
      </div>
      {renderKVBlock('Входные метаданные', f.input_metadata)}
      {renderKVBlock('Метаданные пайплайна', f.pipeline_metadata)}
      {renderKVBlock('Использование токенов', f.token_metadata)}
      {renderKVBlock('Контрольные точки качества', f.safety_gates)}
      {f.agent_metadata.length > 0 && (
        <div className="tech-footer-block">
          <h4>Метаданные агентов</h4>
          <table className="tech-footer-table">
            <thead>
              <tr>
                <th>lane</th>
                <th>role</th>
                <th>provider</th>
                <th>parse</th>
                <th>repair</th>
                <th>semantic</th>
                <th>fallback</th>
                <th>rubric</th>
                <th>raw exposed</th>
              </tr>
            </thead>
            <tbody>
              {f.agent_metadata.map((a, i) => (
                <tr key={i}>
                  <td><code>{a.lane}</code></td>
                  <td><code>{a.role}</code></td>
                  <td>{a.provider_status ?? '—'}</td>
                  <td>{a.parse_status ?? '—'}</td>
                  <td>{a.repair_status ?? '—'}</td>
                  <td>{a.semantic_status ?? '—'}</td>
                  <td>{a.fallback_reason ?? '—'}</td>
                  <td>{a.rubric_active == null ? '—' : String(a.rubric_active)}</td>
                  <td>{String(a.raw_output_exposed ?? false)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {f.known_limitations.length > 0 && (
        <div className="tech-footer-block">
          <h4>Известные ограничения</h4>
          <ul>
            {f.known_limitations.map((l, i) => <li key={i}>{l}</li>)}
          </ul>
        </div>
      )}
    </details>
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
        <p className="human-dossier-disclaimer">
          Этот разбор — человеческое изложение того, что система знает про
          эту пару статья × площадка. Он не заменяет рецензента и не
          говорит за журнал. Если по какой-то секции системе не хватило
          данных, она говорит об этом прямо, а не дописывает за себя.
        </p>
      </div>

      <SourceHeader h={data.source_header} />

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

      <TechnicalFooter f={data.technical_footer} />
    </div>
  );
}
