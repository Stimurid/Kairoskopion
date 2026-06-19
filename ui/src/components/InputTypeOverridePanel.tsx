import { useState } from 'react';

interface ClassificationVerdict {
  input_type: string;
  confidence: 'high' | 'medium' | 'low';
  needs_user_choice: boolean;
  language_detected: 'ru' | 'en' | 'mixed' | 'unknown';
  reasoning: string;
}

interface Props {
  caseId: string;
  classification: ClassificationVerdict;
  effectiveType?: string;
  onOverride: (chosenType: string) => Promise<void>;
  isLoading?: boolean;
}

const ACTIONS: { value: string; label: string; sub?: string }[] = [
  { value: 'article', label: 'Это статья / manuscript', sub: 'запустить ArticleModeler' },
  { value: 'abstract', label: 'Это аннотация (abstract)', sub: 'короткий формат статьи' },
  { value: 'field_notes', label: 'Это полевые заметки / тезисы', sub: 'оставить как есть, без анализа' },
  { value: 'bibliography', label: 'Это библиография', sub: 'оставить как ссылочный список' },
  { value: 'journal_or_venue', label: 'Это журнал / площадка', sub: 'запустить разбор venue' },
  { value: 'review_letter', label: 'Это рецензионное письмо', sub: 'без анализа в этом проходе' },
  { value: 'mixed', label: 'Смешанный материал', sub: 'оставить, я разберу позже' },
];

const TYPE_HUMAN: Record<string, string> = {
  manuscript: 'manuscript',
  article: 'article',
  abstract: 'abstract',
  bibliography: 'bibliography',
  journal_or_venue: 'journal / venue',
  venue: 'venue',
  review_letter: 'review letter',
  field_notes: 'field notes',
  mixed: 'mixed',
  unknown: 'unknown',
};

const CONFIDENCE_COLOR: Record<string, string> = {
  high: 'override-conf--high',
  medium: 'override-conf--medium',
  low: 'override-conf--low',
};


export function InputTypeOverridePanel({
  classification, effectiveType, onOverride, isLoading,
}: Props) {
  const [chosen, setChosen] = useState<string | null>(null);

  const handleClick = async (value: string) => {
    setChosen(value);
    try {
      await onOverride(value);
    } finally {
      setChosen(null);
    }
  };

  const detected = TYPE_HUMAN[classification.input_type] || classification.input_type;
  const isOverridden =
    effectiveType && effectiveType !== classification.input_type;

  return (
    <div className="input-type-override-panel" role="region" aria-label="Уточните тип ввода">
      <div className="override-header">
        <h3>Уточните тип ввода</h3>
        <span className="override-meta">
          Классификатор предположил:{' '}
          <strong className="override-detected-type">{detected}</strong>
          <span className={`override-conf ${CONFIDENCE_COLOR[classification.confidence] || ''}`}>
            confidence: {classification.confidence}
          </span>
        </span>
      </div>
      {classification.reasoning && (
        <p className="override-reasoning">{classification.reasoning}</p>
      )}
      {isOverridden && (
        <p className="override-effective">
          Пайплайн использует: <strong>{effectiveType}</strong> (ваш выбор)
        </p>
      )}
      <p className="override-help">
        Если классификатор ошибся или вы хотите перенаправить материал — выберите действие:
      </p>
      <div className="override-actions" role="group">
        {ACTIONS.map((a) => (
          <button
            key={a.value}
            type="button"
            className={`override-action-chip ${
              effectiveType === a.value ? 'override-action-chip--active' : ''
            }`}
            onClick={() => handleClick(a.value)}
            disabled={isLoading || chosen !== null}
            aria-pressed={effectiveType === a.value}
          >
            <span className="override-action-label">{a.label}</span>
            {a.sub && <span className="override-action-sub">{a.sub}</span>}
          </button>
        ))}
      </div>
    </div>
  );
}
