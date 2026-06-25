import { useEffect } from 'react';
import type { EvidenceDetail } from '../types/domain';
import { EvidenceBadge } from './EvidenceBadge';

const CONFIDENCE_LABELS: Record<string, { label: string; className: string }> = {
  high: { label: 'Высокая', className: 'confidence-high' },
  medium: { label: 'Средняя', className: 'confidence-medium' },
  low: { label: 'Низкая', className: 'confidence-low' },
  preliminary: { label: 'Предварительная', className: 'confidence-low' },
};

const STATUS_EXPLANATIONS: Record<string, string> = {
  fact_from_source: 'Подтверждено непосредственно из исходного документа.',
  fact_from_api_metadata: 'Подтверждено из авторитетных метаданных API (Crossref, DOAJ и т.д.).',
  vendor_claim: 'Заявлено издателем. Не проверено независимо.',
  corpus_observation: 'Получено статистическим анализом опубликованных статей журнала.',
  inference: 'Системный вывод из доступных данных. Может требовать проверки.',
  tacit_signal: 'Неявное знание пользователя или опыт.',
  user_note: 'Заметка пользователя, не системный вывод.',
  prior_outcome: 'Основано на предыдущих подачах или результатах рецензирования.',
  unknown: 'Нет данных. Это не отсутствие объекта, а отсутствие знания о нём.',
  inaccessible: 'Источник найден, но недоступен (пейволл, битая ссылка).',
  stale: 'Данные могут быть устаревшими. Рекомендуется обновление.',
  conflicting_evidence: 'Источники расходятся в данных по этому полю.',
};

interface Props {
  evidence: EvidenceDetail | null;
  onClose: () => void;
}

export function EvidenceDrawer({ evidence, onClose }: Props) {
  useEffect(() => {
    if (!evidence) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [evidence, onClose]);

  if (!evidence) {
    return (
      <aside className="evidence-drawer evidence-drawer--empty" aria-label="Панель свидетельств">
        <div className="drawer-header">
          <h3>Свидетельства</h3>
        </div>
        <p className="drawer-empty-text">
          Нажмите на любое утверждение или поле, чтобы увидеть его источник, статус и уверенность.
        </p>
        <div className="drawer-legend">
          <h4>Обозначения бейджей</h4>
          <div className="legend-items">
            <div className="legend-item"><EvidenceBadge status="fact_from_source" /> Подтверждено из источника</div>
            <div className="legend-item"><EvidenceBadge status="vendor_claim" /> Заявление издателя</div>
            <div className="legend-item"><EvidenceBadge status="corpus_observation" /> Из корпуса</div>
            <div className="legend-item"><EvidenceBadge status="inference" /> Системный вывод</div>
            <div className="legend-item"><EvidenceBadge status="user_note" /> От пользователя</div>
            <div className="legend-item"><EvidenceBadge status="unknown" /> Нет данных</div>
            <div className="legend-item"><EvidenceBadge status="stale" /> Требует обновления</div>
            <div className="legend-item"><EvidenceBadge status="conflicting_evidence" /> Источники расходятся</div>
          </div>
        </div>
      </aside>
    );
  }

  const confCfg = CONFIDENCE_LABELS[evidence.confidence] ?? CONFIDENCE_LABELS.low;
  const explanation = STATUS_EXPLANATIONS[evidence.evidence_status] ?? '';

  return (
    <aside className="evidence-drawer" aria-label="Панель свидетельств">
      <div className="drawer-header">
        <h3>Свидетельства</h3>
        <button
          className="drawer-close"
          onClick={onClose}
          aria-label="Закрыть панель"
        >
          &times;
        </button>
      </div>

      <div className="drawer-content">
        <div className="drawer-field-path">
          <span className="drawer-entity">{evidence.entity_type}</span>
          <span className="drawer-sep">.</span>
          <span className="drawer-field-name">{evidence.field_path}</span>
        </div>

        <div className="drawer-status-section">
          <div className="drawer-field">
            <span className="drawer-label">Статус</span>
            <EvidenceBadge status={evidence.evidence_status} />
          </div>
          {explanation && (
            <p className="drawer-explanation">{explanation}</p>
          )}
        </div>

        <div className="drawer-field">
          <span className="drawer-label">Уверенность</span>
          <span className={`drawer-confidence ${confCfg.className}`}>
            {confCfg.label}
          </span>
        </div>

        {evidence.source && (
          <div className="drawer-source-section">
            <span className="drawer-label">Источник</span>
            <div className="drawer-source-preview">
              {evidence.source}
            </div>
          </div>
        )}

        {evidence.note && (
          <div className="drawer-field">
            <span className="drawer-label">Заметка</span>
            <span className="drawer-value drawer-note">{evidence.note}</span>
          </div>
        )}

        {evidence.evidence_status === 'conflicting_evidence' && (
          <div className="drawer-conflict-section">
            <h4>Конфликт</h4>
            <p className="drawer-conflict-text">
              Несколько источников сообщают разные значения для этого поля.
              Рекомендуется ручная проверка перед продолжением.
            </p>
          </div>
        )}
      </div>
    </aside>
  );
}
