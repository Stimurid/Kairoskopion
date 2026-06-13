import type { RewriteChange, FieldCoreImpact } from '../types/domain';

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  pending: { label: 'Pending', className: 'rw-pending' },
  accepted: { label: 'Accepted', className: 'rw-accepted' },
  rejected: { label: 'Rejected', className: 'rw-rejected' },
  deferred: { label: 'Deferred', className: 'rw-deferred' },
  blocked: { label: 'Blocked', className: 'rw-blocked' },
};

const CORE_RISK_CONFIG: Record<string, { label: string; className: string }> = {
  core_preserving: { label: 'Core safe', className: 'core-preserving' },
  core_touching: { label: 'Core touched', className: 'core-touching' },
  core_transforming: { label: 'Core at risk', className: 'core-transforming' },
  core_destroying_risk: { label: 'Core threat', className: 'core-destroying' },
  unknown_core_impact: { label: 'Unknown', className: 'core-unknown' },
};

interface Props {
  change: RewriteChange;
  onDecision: (changeId: string, action: string) => void;
  disabled?: boolean;
}

export function RewriteTaskCard({ change, onDecision, disabled }: Props) {
  const status = STATUS_CONFIG[change.status] ?? STATUS_CONFIG.pending;
  const core = CORE_RISK_CONFIG[change.field_core_risk] ?? CORE_RISK_CONFIG.unknown_core_impact;
  const isActionable = change.status === 'pending' && !change._blocked_reason;

  return (
    <div className={`rewrite-task-card ${status.className}`}>
      <div className="rw-header">
        <span className="rw-target">{change.target_block}</span>
        <span className={`rw-status-badge ${status.className}`}>{status.label}</span>
      </div>

      <p className="rw-desired">{change.desired_state}</p>
      <p className="rw-reason">{change.reason}</p>

      <div className="rw-badges">
        <span className={`pathway-badge ${core.className}`}>{core.label}</span>
      </div>

      {change._blocked_reason && (
        <div className="rw-blocked-reason">
          Blocked: {change._blocked_reason}
        </div>
      )}

      {change._matched_core_elements && change._matched_core_elements.length > 0 && (
        <div className="rw-core-matches">
          <span className="rw-core-label">Touches core:</span>
          {change._matched_core_elements.map((el, i) => (
            <span key={i} className="rw-core-chip">{el}</span>
          ))}
        </div>
      )}

      {isActionable && (
        <div className="rw-actions">
          <button
            className="btn btn-sm rw-btn-accept"
            onClick={() => onDecision(change.change_id, 'accept')}
            disabled={disabled}
          >
            Accept
          </button>
          <button
            className="btn btn-sm rw-btn-reject"
            onClick={() => onDecision(change.change_id, 'reject')}
            disabled={disabled}
          >
            Reject
          </button>
          <button
            className="btn btn-sm rw-btn-defer"
            onClick={() => onDecision(change.change_id, 'defer')}
            disabled={disabled}
          >
            Defer
          </button>
        </div>
      )}
    </div>
  );
}
