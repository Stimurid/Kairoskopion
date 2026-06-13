import type { QualityGateResult, QualityGateStatus } from '../types/domain';

const STATUS_CONFIG: Record<string, { icon: string; className: string }> = {
  passed: { icon: '✓', className: 'gate-passed' },
  passed_with_warnings: { icon: '✓', className: 'gate-warned' },
  failed_blocking: { icon: '✗', className: 'gate-failed' },
  failed_but_preliminary_output_allowed: { icon: '~', className: 'gate-soft-fail' },
  needs_user_input: { icon: '?', className: 'gate-needs-input' },
  needs_source_refresh: { icon: '↻', className: 'gate-stale' },
  not_applicable: { icon: '—', className: 'gate-na' },
};

interface Props {
  gates: Record<string, QualityGateResult>;
}

export function QualityGateBar({ gates }: Props) {
  const entries = Object.values(gates);

  if (entries.length === 0) {
    return null;
  }

  const failedCount = entries.filter(g =>
    g.status === 'failed_blocking'
  ).length;
  const warnedCount = entries.filter(g =>
    g.status === 'passed_with_warnings' || g.status === 'failed_but_preliminary_output_allowed'
  ).length;

  return (
    <div className="quality-gate-bar">
      <div className="gate-bar-header">
        <h3>Quality Gates</h3>
        {failedCount > 0 && (
          <span className="gate-count gate-count--failed">{failedCount} failed</span>
        )}
        {warnedCount > 0 && (
          <span className="gate-count gate-count--warned">{warnedCount} warnings</span>
        )}
      </div>
      <div className="gate-chips">
        {entries.map(gate => {
          const cfg = STATUS_CONFIG[gate.status] ?? STATUS_CONFIG.not_applicable;
          return (
            <div
              key={gate.gate_id}
              className={`gate-chip ${cfg.className}`}
              title={gate.notes || gate.gate_name}
            >
              <span className="gate-icon" aria-hidden="true">{cfg.icon}</span>
              <span className="gate-name">{gate.gate_name}</span>
              {gate.blocking_issues.length > 0 && (
                <span className="gate-issue-count">{gate.blocking_issues.length}</span>
              )}
            </div>
          );
        })}
      </div>

      {entries.some(g => g.blocking_issues.length > 0) && (
        <div className="gate-issues">
          {entries
            .filter(g => g.blocking_issues.length > 0)
            .map(g => (
              <div key={g.gate_id} className="gate-issue-group">
                <span className="gate-issue-source">{g.gate_name}:</span>
                <ul>
                  {g.blocking_issues.map((issue, i) => (
                    <li key={i} className="gate-issue">{issue}</li>
                  ))}
                </ul>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
