import type { EvidenceStatus } from '../types/domain';

const BADGE_CONFIG: Record<string, { label: string; className: string; title: string }> = {
  fact_from_source:       { label: 'FACT',     className: 'badge-fact',       title: 'Подтверждено из источника' },
  fact_from_api_metadata: { label: 'FACT',     className: 'badge-fact',       title: 'Подтверждено из метаданных API' },
  vendor_claim:           { label: 'CLAIM',    className: 'badge-claim',      title: 'Заявлено издателем, не проверено' },
  corpus_observation:     { label: 'CORPUS',   className: 'badge-corpus',     title: 'Из анализа опубликованных статей' },
  inference:              { label: 'INFERRED', className: 'badge-inferred',   title: 'Системный вывод из данных' },
  tacit_signal:           { label: 'USER',     className: 'badge-user',       title: 'Неявное знание пользователя' },
  user_note:              { label: 'USER',     className: 'badge-user',       title: 'Заметка пользователя' },
  prior_outcome:          { label: 'PRIOR',    className: 'badge-user',       title: 'Из предыдущего опыта подачи' },
  unknown:                { label: 'UNKNOWN',  className: 'badge-unknown',    title: 'Нет данных — не отсутствие, а незнание' },
  inaccessible:           { label: 'LOCKED',   className: 'badge-unknown',    title: 'Источник найден, но недоступен' },
  stale:                  { label: 'STALE',    className: 'badge-stale',      title: 'Может быть устаревшим' },
  conflicting_evidence:   { label: 'CONFLICT', className: 'badge-conflict',   title: 'Источники расходятся' },
};

interface Props {
  status: EvidenceStatus;
  onClick?: () => void;
}

export function EvidenceBadge({ status, onClick }: Props) {
  const cfg = BADGE_CONFIG[status] ?? BADGE_CONFIG.unknown;
  return (
    <span
      className={`evidence-badge ${cfg.className}`}
      title={cfg.title}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick}
      onKeyDown={onClick ? (e) => { if (e.key === 'Enter' || e.key === ' ') onClick(); } : undefined}
    >
      {cfg.label}
    </span>
  );
}
