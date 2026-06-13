import type { VenueModel, PublicationRegimeModel, EvidenceStatus } from '../types/domain';
import { EvidenceBadge } from './EvidenceBadge';

interface FieldRowProps {
  label: string;
  value: string | string[] | undefined;
  evidenceStatus?: EvidenceStatus;
  onEvidenceClick?: () => void;
}

function VenueFieldRow({ label, value, evidenceStatus, onEvidenceClick }: FieldRowProps) {
  const displayValue = Array.isArray(value)
    ? (value.length > 0 ? value.join(', ') : '—')
    : (value || '—');
  const isEmpty = !value || (Array.isArray(value) && value.length === 0);

  return (
    <div className={`field-row ${isEmpty ? 'field-row--empty' : ''}`}>
      <span className="field-label">{label}</span>
      <span className="field-value">{displayValue}</span>
      {evidenceStatus && (
        <EvidenceBadge status={evidenceStatus} onClick={onEvidenceClick} />
      )}
    </div>
  );
}

interface Props {
  venue: VenueModel;
  regime?: PublicationRegimeModel;
  onEvidenceClick: (entityType: string, fieldPath: string) => void;
}

export function VenueProfile({ venue, regime, onEvidenceClick }: Props) {
  const inferStatus = (field: string): EvidenceStatus => {
    if (venue.unknowns?.some(u => u.toLowerCase().includes(field.toLowerCase()))) {
      return 'unknown';
    }
    return 'vendor_claim';
  };

  return (
    <div className="venue-profile">
      <div className="venue-profile-header">
        <h2 className="venue-name">{venue.canonical_name || 'Unknown Venue'}</h2>
        <span className={`lifecycle-badge lifecycle-${venue.lifecycle_status}`}>
          {venue.lifecycle_status}
        </span>
      </div>

      <section className="venue-section">
        <h3>Identity</h3>
        <div className="venue-fields">
          <VenueFieldRow
            label="Type"
            value={venue.venue_type}
            evidenceStatus={inferStatus('type')}
            onEvidenceClick={() => onEvidenceClick('VenueModel', 'venue_type')}
          />
          <VenueFieldRow
            label="Scope"
            value={venue.scope_summary}
            evidenceStatus={inferStatus('scope')}
            onEvidenceClick={() => onEvidenceClick('VenueModel', 'scope_summary')}
          />
          <VenueFieldRow
            label="Article types"
            value={venue.article_types_supported}
            evidenceStatus={inferStatus('article_types')}
            onEvidenceClick={() => onEvidenceClick('VenueModel', 'article_types_supported')}
          />
        </div>
      </section>

      <section className="venue-section">
        <h3>Access & Policy</h3>
        <div className="venue-fields">
          <VenueFieldRow
            label="Open Access"
            value={venue.open_access_status}
            evidenceStatus={inferStatus('open_access')}
            onEvidenceClick={() => onEvidenceClick('VenueModel', 'open_access_status')}
          />
          <VenueFieldRow
            label="APC"
            value={venue.apc_policy}
            evidenceStatus={inferStatus('apc')}
            onEvidenceClick={() => onEvidenceClick('VenueModel', 'apc_policy')}
          />
          <VenueFieldRow
            label="AI Policy"
            value={venue.ai_policy}
            evidenceStatus={inferStatus('ai_policy')}
            onEvidenceClick={() => onEvidenceClick('VenueModel', 'ai_policy')}
          />
        </div>
      </section>

      {venue.indexing_claims && venue.indexing_claims.length > 0 && (
        <section className="venue-section">
          <h3>Indexing</h3>
          <div className="indexing-claims">
            {venue.indexing_claims.map((claim, i) => (
              <div key={i} className="indexing-claim">
                <span className="claim-db">{String((claim as Record<string, unknown>).database_name ?? 'Indexing')}</span>
                <EvidenceBadge
                  status={String((claim as Record<string, unknown>).evidence_status ?? 'vendor_claim') as EvidenceStatus}
                  onClick={() => onEvidenceClick('VenueModel', `indexing_claims[${i}]`)}
                />
              </div>
            ))}
          </div>
        </section>
      )}

      {regime && (
        <section className="venue-section">
          <h3>Publication Process</h3>
          <div className="venue-fields">
            <VenueFieldRow label="Review type" value={regime.review_type} />
            <VenueFieldRow label="Typical rounds" value={String(regime.typical_review_rounds || '—')} />
            <VenueFieldRow label="Turnaround" value={regime.typical_turnaround_weeks} />
            <VenueFieldRow label="Submission system" value={regime.submission_system} />
            <VenueFieldRow label="Formatting" value={regime.formatting_strictness} />
          </div>
        </section>
      )}

      {venue.unknowns && venue.unknowns.length > 0 && (
        <section className="venue-section venue-unknowns">
          <h3>Unknowns</h3>
          <ul className="unknowns-list">
            {venue.unknowns.map((u, i) => (
              <li key={i}>
                <EvidenceBadge status="unknown" /> {u}
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="venue-footer">
        <span className="confidence-label">
          Confidence: <strong>{venue.confidence || 'preliminary'}</strong>
        </span>
      </div>
    </div>
  );
}
