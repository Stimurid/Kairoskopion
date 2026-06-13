import type { VenueCandidate } from '../types/domain';

const CONFIDENCE_CONFIG: Record<string, { label: string; className: string }> = {
  high: { label: 'High', className: 'conf-high' },
  medium: { label: 'Medium', className: 'conf-medium' },
  low: { label: 'Low', className: 'conf-low' },
};

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  discovered: { label: 'Discovered', className: 'status-discovered' },
  screened: { label: 'Screened', className: 'status-screened' },
  profiled: { label: 'Profiled', className: 'status-profiled' },
  selected: { label: 'Selected', className: 'status-selected' },
  rejected: { label: 'Rejected', className: 'status-rejected' },
};

interface Props {
  candidate: VenueCandidate;
  isSelected?: boolean;
  onSelect?: (candidateId: string) => void;
}

export function VenueCandidateCard({ candidate, isSelected, onSelect }: Props) {
  const conf = CONFIDENCE_CONFIG[candidate.confidence] ?? CONFIDENCE_CONFIG.low;
  const status = STATUS_CONFIG[candidate.status] ?? STATUS_CONFIG.discovered;

  return (
    <button
      className={`venue-candidate-card ${isSelected ? 'venue-candidate-card--selected' : ''}`}
      onClick={() => onSelect?.(candidate.venue_candidate_id)}
      type="button"
    >
      <div className="vc-header">
        <h3 className="vc-name">{candidate.canonical_name || 'Unknown venue'}</h3>
        <span className={`vc-status ${status.className}`}>{status.label}</span>
      </div>

      {candidate.issn && (
        <div className="vc-issn">ISSN: {candidate.issn}</div>
      )}

      <div className="vc-badges">
        <span className={`vc-badge ${conf.className}`}>{conf.label} confidence</span>
      </div>

      {candidate.discovery_reasons.length > 0 && (
        <div className="vc-reasons">
          <span className="vc-section-label">Discovery reasons:</span>
          <ul>
            {candidate.discovery_reasons.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </div>
      )}

      {candidate.authority_assessments.length > 0 && (
        <div className="vc-authority">
          <span className="vc-section-label">Authority:</span>
          <div className="vc-authority-list">
            {candidate.authority_assessments.map((a, i) => {
              const scope = (a as Record<string, unknown>).scope as string | undefined;
              const level = (a as Record<string, unknown>).level as string | undefined;
              return (
                <span key={i} className="vc-authority-chip">
                  {scope ?? 'unknown'}: {level ?? '?'}
                </span>
              );
            })}
          </div>
        </div>
      )}
    </button>
  );
}
