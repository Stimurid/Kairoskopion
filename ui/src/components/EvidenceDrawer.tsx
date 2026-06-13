import type { EvidenceDetail } from '../types/domain';
import { EvidenceBadge } from './EvidenceBadge';

interface Props {
  evidence: EvidenceDetail | null;
  onClose: () => void;
}

export function EvidenceDrawer({ evidence, onClose }: Props) {
  if (!evidence) {
    return (
      <aside className="evidence-drawer evidence-drawer--empty" aria-label="Evidence panel">
        <div className="drawer-header">
          <h3>Evidence</h3>
        </div>
        <p className="drawer-empty-text">
          Click any claim or field to see its evidence source, status, and confidence.
        </p>
      </aside>
    );
  }

  return (
    <aside className="evidence-drawer" aria-label="Evidence panel">
      <div className="drawer-header">
        <h3>Evidence</h3>
        <button
          className="drawer-close"
          onClick={onClose}
          aria-label="Close evidence panel"
        >
          ×
        </button>
      </div>

      <div className="drawer-content">
        <div className="drawer-field">
          <span className="drawer-label">Field</span>
          <span className="drawer-value">
            {evidence.entity_type}.{evidence.field_path}
          </span>
        </div>

        <div className="drawer-field">
          <span className="drawer-label">Status</span>
          <EvidenceBadge status={evidence.evidence_status} />
        </div>

        <div className="drawer-field">
          <span className="drawer-label">Confidence</span>
          <span className={`confidence-${evidence.confidence}`}>
            {evidence.confidence}
          </span>
        </div>

        {evidence.source && (
          <div className="drawer-field">
            <span className="drawer-label">Source</span>
            <span className="drawer-value">{evidence.source}</span>
          </div>
        )}

        {evidence.note && (
          <div className="drawer-field">
            <span className="drawer-label">Note</span>
            <span className="drawer-value drawer-note">{evidence.note}</span>
          </div>
        )}
      </div>
    </aside>
  );
}
