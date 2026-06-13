import { useState } from 'react';
import type { RewritePlan } from '../types/domain';
import { RewriteTaskCard } from './RewriteTaskCard';

const CORE_RISK_ORDER: Record<string, number> = {
  core_destroying_risk: 0,
  core_transforming: 1,
  core_touching: 2,
  core_preserving: 3,
  unknown_core_impact: 4,
};

interface Props {
  rewritePlan: RewritePlan;
  protectedCore: string[];
  onDecision: (changeId: string, action: string) => void;
  onApplyAll?: () => void;
  isLoading?: boolean;
}

type FilterStatus = 'all' | 'pending' | 'accepted' | 'rejected' | 'blocked';

export function AdaptationStudio({
  rewritePlan,
  protectedCore,
  onDecision,
  onApplyAll,
  isLoading,
}: Props) {
  const [filter, setFilter] = useState<FilterStatus>('all');

  const changes = rewritePlan.changes;

  const filtered = filter === 'all'
    ? changes
    : changes.filter(c => {
        if (filter === 'blocked') return !!c._blocked_reason;
        return c.status === filter;
      });

  const sorted = [...filtered].sort(
    (a, b) => (CORE_RISK_ORDER[a.field_core_risk] ?? 9) - (CORE_RISK_ORDER[b.field_core_risk] ?? 9)
  );

  const pendingCount = changes.filter(c => c.status === 'pending' && !c._blocked_reason).length;
  const acceptedCount = changes.filter(c => c.status === 'accepted').length;
  const rejectedCount = changes.filter(c => c.status === 'rejected').length;
  const blockedCount = changes.filter(c => !!c._blocked_reason).length;

  return (
    <div className="adaptation-studio">
      <div className="adapt-header">
        <div className="adapt-header-left">
          <h2>Adaptation Studio</h2>
          <span className="adapt-effort">Effort: {rewritePlan.estimated_effort}</span>
        </div>
        {rewritePlan.requires_user_acceptance && (
          <span className="adapt-gate-badge">User acceptance required</span>
        )}
      </div>

      {rewritePlan.summary && (
        <p className="adapt-summary">{rewritePlan.summary}</p>
      )}

      {protectedCore.length > 0 && (
        <div className="protected-core-gate">
          <h3>Protected Core</h3>
          <div className="core-elements">
            {protectedCore.map((el, i) => {
              const touched = changes.some(c =>
                c._matched_core_elements?.includes(el)
              );
              return (
                <span
                  key={i}
                  className={`core-element ${touched ? 'core-element--touched' : 'core-element--safe'}`}
                >
                  {touched && <span className="core-warning-icon" aria-hidden="true">!</span>}
                  {el}
                </span>
              );
            })}
          </div>
        </div>
      )}

      <div className="adapt-toolbar">
        <div className="adapt-filters">
          {(['all', 'pending', 'accepted', 'rejected', 'blocked'] as FilterStatus[]).map(f => (
            <button
              key={f}
              className={`type-chip ${filter === f ? 'type-chip--active' : ''}`}
              onClick={() => setFilter(f)}
            >
              {f}
              {f === 'pending' && pendingCount > 0 && ` (${pendingCount})`}
              {f === 'accepted' && acceptedCount > 0 && ` (${acceptedCount})`}
              {f === 'rejected' && rejectedCount > 0 && ` (${rejectedCount})`}
              {f === 'blocked' && blockedCount > 0 && ` (${blockedCount})`}
            </button>
          ))}
        </div>

        <div className="adapt-counts">
          <span>{changes.length} changes total</span>
        </div>
      </div>

      <div className="adapt-task-list">
        {sorted.length === 0 ? (
          <div className="adapt-empty">
            <p>No changes match the current filter.</p>
          </div>
        ) : (
          sorted.map(c => (
            <RewriteTaskCard
              key={c.change_id}
              change={c}
              onDecision={onDecision}
              disabled={isLoading}
            />
          ))
        )}
      </div>

      {pendingCount === 0 && acceptedCount > 0 && onApplyAll && (
        <div className="adapt-apply-bar">
          <span>{acceptedCount} changes accepted, {rejectedCount} rejected</span>
          <button
            className="btn btn-primary"
            onClick={onApplyAll}
            disabled={isLoading}
          >
            {isLoading ? 'Applying...' : 'Apply Accepted Changes'}
          </button>
        </div>
      )}
    </div>
  );
}
