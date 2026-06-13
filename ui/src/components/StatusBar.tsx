import type { CaseStage } from '../types/domain';

const STAGES: { key: string; label: string }[] = [
  { key: 'intake',          label: 'Intake' },
  { key: 'article_model',   label: 'Article' },
  { key: 'scenario',        label: 'Scenario' },
  { key: 'pathways',        label: 'Pathways' },
  { key: 'venue_pool',      label: 'Venue Pool' },
  { key: 'venue_selected',  label: 'Selected Venue' },
  { key: 'fit_assessed',    label: 'Fit & Mismatch' },
  { key: 'adapting',        label: 'Adaptation' },
  { key: 'submission_pack', label: 'Pack' },
  { key: 'dossier',         label: 'Dossier' },
];

interface Props {
  currentStage: CaseStage;
  objectsPresent: Record<string, boolean>;
  onStageClick: (stage: string) => void;
}

export function StatusBar({ currentStage, objectsPresent, onStageClick }: Props) {
  return (
    <nav className="status-bar" aria-label="Case pipeline stages">
      {STAGES.map((s, i) => {
        const present = objectsPresent[s.key] ?? false;
        const isCurrent = currentStage === s.key;
        let stateClass = 'stage-empty';
        if (isCurrent) stateClass = 'stage-current';
        else if (present) stateClass = 'stage-done';

        return (
          <span key={s.key}>
            {i > 0 && <span className="stage-arrow" aria-hidden="true"> → </span>}
            <button
              className={`stage-chip ${stateClass}`}
              onClick={() => onStageClick(s.key)}
              aria-current={isCurrent ? 'step' : undefined}
              title={present ? `${s.label}: data available` : `${s.label}: not yet`}
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
