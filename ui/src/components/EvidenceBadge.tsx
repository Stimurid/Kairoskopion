import type { EvidenceStatus } from '../types/domain';

const BADGE_CONFIG: Record<string, { label: string; className: string; title: string }> = {
  fact_from_source:       { label: 'FACT',     className: 'badge-fact',       title: 'Verified from source' },
  fact_from_api_metadata: { label: 'FACT',     className: 'badge-fact',       title: 'Verified from API metadata' },
  vendor_claim:           { label: 'CLAIM',    className: 'badge-claim',      title: 'Publisher self-reported, not independently verified' },
  corpus_observation:     { label: 'CORPUS',   className: 'badge-corpus',     title: 'Derived from analysis of published articles' },
  inference:              { label: 'INFERRED', className: 'badge-inferred',   title: 'System inference from available data' },
  tacit_signal:           { label: 'USER',     className: 'badge-user',       title: 'User-provided tacit knowledge' },
  user_note:              { label: 'USER',     className: 'badge-user',       title: 'User-provided note' },
  prior_outcome:          { label: 'PRIOR',    className: 'badge-user',       title: 'Based on prior submission outcome' },
  unknown:                { label: 'UNKNOWN',  className: 'badge-unknown',    title: 'No data available — not absence, ignorance' },
  inaccessible:           { label: 'LOCKED',   className: 'badge-unknown',    title: 'Source found but cannot be accessed' },
  stale:                  { label: 'STALE',    className: 'badge-stale',      title: 'Past freshness window, may have changed' },
  conflicting_evidence:   { label: 'CONFLICT', className: 'badge-conflict',   title: 'Multiple sources disagree' },
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
