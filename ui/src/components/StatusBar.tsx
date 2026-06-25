import type { CaseStage } from '../types/domain';

const STAGES: { key: string; label: string }[] = [
  { key: 'intake',          label: 'Ввод' },
  { key: 'article_model',   label: 'Статья' },
  { key: 'scenario',        label: 'Сценарий' },
  { key: 'pathways',        label: 'Дисциплины' },
  { key: 'venue_pool',      label: 'Пул журналов' },
  { key: 'venue_selected',  label: 'Выбранный журнал' },
  { key: 'fit_assessed',    label: 'Fit и расхождения' },
  { key: 'adapting',        label: 'Адаптация' },
  { key: 'submission_pack', label: 'Пакет' },
  { key: 'dossier',         label: 'Досье' },
];

interface Props {
  currentStage: CaseStage;
  objectsPresent: Record<string, boolean>;
  onStageClick: (stage: string) => void;
}

export function StatusBar({ currentStage, objectsPresent, onStageClick }: Props) {
  const currentIdx = STAGES.findIndex(s => s.key === currentStage);

  return (
    <nav className="status-bar" aria-label="Этапы пайплайна">
      {STAGES.map((s, i) => {
        const present = objectsPresent[s.key] ?? false;
        const isCurrent = currentStage === s.key;
        const isReachable = present || isCurrent || i <= currentIdx;
        let stateClass = 'stage-empty';
        if (isCurrent) stateClass = 'stage-current';
        else if (present) stateClass = 'stage-done';

        return (
          <span key={s.key}>
            {i > 0 && <span className="stage-arrow" aria-hidden="true"> → </span>}
            <button
              className={`stage-chip ${stateClass} ${!isReachable ? 'stage-disabled' : ''}`}
              onClick={() => isReachable && onStageClick(s.key)}
              aria-current={isCurrent ? 'step' : undefined}
              aria-disabled={!isReachable}
              title={present ? `${s.label}: данные доступны` : isReachable ? s.label : `${s.label}: сначала завершите предыдущие этапы`}
            >
              <span className="stage-indicator" aria-hidden="true">
                {present ? '●' : '○'}
              </span>
              {' '}{s.label}
            </button>
          </span>
        );
      })}
    </nav>
  );
}
