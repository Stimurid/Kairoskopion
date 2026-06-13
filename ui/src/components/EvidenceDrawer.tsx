import { useEffect } from 'react';
import type { EvidenceDetail } from '../types/domain';
import { EvidenceBadge } from './EvidenceBadge';

const CONFIDENCE_LABELS: Record<string, { label: string; className: string }> = {
  high: { label: 'High confidence', className: 'confidence-high' },
  medium: { label: 'Medium confidence', className: 'confidence-medium' },
  low: { label: 'Low confidence', className: 'confidence-low' },
  preliminary: { label: 'Preliminary', className: 'confidence-low' },
};

const STATUS_EXPLANATIONS: Record<string, string> = {
  fact_from_source: 'Directly verified from the original source document.',
  fact_from_api_metadata: 'Verified from authoritative API metadata (e.g., Crossref, DOAJ).',
  vendor_claim: 'Publisher self-reported. Not independently verified.',
  corpus_observation: 'Derived from statistical analysis of published articles in the venue.',
  inference: 'System inference from available data. May need validation.',
  tacit_signal: 'User-provided tacit knowledge or experience.',
  user_note: 'User-provided note, not system-derived.',
  prior_outcome: 'Based on prior submission or review outcome.',
  unknown: 'No data available. This is not absence of the thing, but absence of knowledge.',
  inaccessible: 'A source was found but could not be accessed (paywall, broken link).',
  stale: 'Data was collected but may be outdated. Refresh recommended.',
  conflicting_evidence: 'Multiple sources disagree on this field.',
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
      <aside className="evidence-drawer evidence-drawer--empty" aria-label="Evidence panel">
        <div className="drawer-header">
          <h3>Evidence</h3>
        </div>
        <p className="drawer-empty-text">
          Click any claim or field to see its evidence source, status, and confidence.
        </p>
        <div className="drawer-legend">
          <h4>Badge legend</h4>
          <div className="legend-items">
            <div className="legend-item"><EvidenceBadge status="fact_from_source" /> Verified from source</div>
            <div className="legend-item"><EvidenceBadge status="vendor_claim" /> Publisher claim</div>
            <div className="legend-item"><EvidenceBadge status="corpus_observation" /> Corpus-derived</div>
            <div className="legend-item"><EvidenceBadge status="inference" /> System inference</div>
            <div className="legend-item"><EvidenceBadge status="user_note" /> User-provided</div>
            <div className="legend-item"><EvidenceBadge status="unknown" /> No data</div>
            <div className="legend-item"><EvidenceBadge status="stale" /> Needs refresh</div>
            <div className="legend-item"><EvidenceBadge status="conflicting_evidence" /> Sources disagree</div>
          </div>
        </div>
      </aside>
    );
  }

  const confCfg = CONFIDENCE_LABELS[evidence.confidence] ?? CONFIDENCE_LABELS.low;
  const explanation = STATUS_EXPLANATIONS[evidence.evidence_status] ?? '';

  return (
    <aside className="evidence-drawer" aria-label="Evidence panel">
      <div className="drawer-header">
        <h3>Evidence</h3>
        <button
          className="drawer-close"
          onClick={onClose}
          aria-label="Close evidence panel"
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
            <span className="drawer-label">Status</span>
            <EvidenceBadge status={evidence.evidence_status} />
          </div>
          {explanation && (
            <p className="drawer-explanation">{explanation}</p>
          )}
        </div>

        <div className="drawer-field">
          <span className="drawer-label">Confidence</span>
          <span className={`drawer-confidence ${confCfg.className}`}>
            {confCfg.label}
          </span>
        </div>

        {evidence.source && (
          <div className="drawer-source-section">
            <span className="drawer-label">Source</span>
            <div className="drawer-source-preview">
              {evidence.source}
            </div>
          </div>
        )}

        {evidence.note && (
          <div className="drawer-field">
            <span className="drawer-label">Note</span>
            <span className="drawer-value drawer-note">{evidence.note}</span>
          </div>
        )}

        {evidence.evidence_status === 'conflicting_evidence' && (
          <div className="drawer-conflict-section">
            <h4>Conflict</h4>
            <p className="drawer-conflict-text">
              Multiple sources report different values for this field.
              Manual review is recommended before proceeding.
            </p>
          </div>
        )}
      </div>
    </aside>
  );
}
