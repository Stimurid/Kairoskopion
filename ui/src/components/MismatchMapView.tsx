import type { FitAssessment, MismatchItem, MismatchMap } from '../types/domain';
import { LLMAttemptBadge } from './LLMAttemptBadge';
import { LLMAttemptWarning } from './LLMAttemptWarning';

const SEVERITY_ORDER: Record<string, number> = {
  blocking: 0,
  major: 1,
  minor: 2,
  informational: 3,
};

const SEVERITY_LABELS: Record<string, { label: string; className: string }> = {
  blocking: { label: 'BLOCKING', className: 'severity-blocking' },
  major: { label: 'MAJOR', className: 'severity-major' },
  minor: { label: 'MINOR', className: 'severity-minor' },
  informational: { label: 'INFO', className: 'severity-info' },
};

const CORE_RISK_LABELS: Record<string, { label: string; className: string }> = {
  core_preserving: { label: 'Core safe', className: 'core-preserving' },
  core_touching: { label: 'Core touched', className: 'core-touching' },
  core_transforming: { label: 'Core at risk', className: 'core-transforming' },
  core_destroying_risk: { label: 'Core threat', className: 'core-destroying' },
  unknown_core_impact: { label: 'Unknown impact', className: 'core-unknown' },
};

function MismatchRow({ item }: { item: MismatchItem }) {
  const sev = SEVERITY_LABELS[item.severity] ?? SEVERITY_LABELS.informational;
  const core = CORE_RISK_LABELS[item.field_core_risk] ?? CORE_RISK_LABELS.unknown_core_impact;

  return (
    <div className={`mismatch-row mismatch-${item.severity}`}>
      <div className="mismatch-header">
        <span className="mismatch-axis">{item.axis}</span>
        <span className={`severity-badge ${sev.className}`}>{sev.label}</span>
        <span className={`core-risk-badge ${core.className}`}>{core.label}</span>
      </div>
      <p className="mismatch-description">{item.description}</p>
      <div className="mismatch-sides">
        <div className="mismatch-side">
          <span className="side-label">Article</span>
          <span className="side-value">
            {item.article_side || (
              <em className="side-value--unknown">сторона статьи не определена</em>
            )}
          </span>
        </div>
        <span className="mismatch-arrow" aria-hidden="true">&harr;</span>
        <div className="mismatch-side">
          <span className="side-label">Venue</span>
          <span className="side-value">
            {item.venue_side || (
              // UI4 closure: backend now intentionally emits empty
              // venue_side when no LLM narrative is available; label
              // it honestly instead of "—".
              <em className="side-value--unknown">
                требуется LLM-комментарий по площадке
              </em>
            )}
          </span>
        </div>
      </div>
      {item.possible_actions.length > 0 && (
        <div className="mismatch-actions">
          <span className="actions-label">Possible actions:</span>
          <ul>
            {item.possible_actions.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

interface Props {
  mismatchMap: MismatchMap;
  fitAssessment?: FitAssessment | null;
}

export function MismatchMapView({ mismatchMap, fitAssessment }: Props) {
  const sorted = [...mismatchMap.mismatches].sort(
    (a, b) => (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9)
  );

  const blockingCount = sorted.filter(m => m.severity === 'blocking').length;
  const majorCount = sorted.filter(m => m.severity === 'major').length;

  return (
    <div className="mismatch-map-view">
      <div className="mismatch-map-header">
        <h2>Mismatch Map</h2>
        <div className="mismatch-summary-badges">
          {blockingCount > 0 && (
            <span className="severity-badge severity-blocking">{blockingCount} blocking</span>
          )}
          {majorCount > 0 && (
            <span className="severity-badge severity-major">{majorCount} major</span>
          )}
          <span className="mismatch-total">{sorted.length} total</span>
          <LLMAttemptBadge attempt={fitAssessment?.extraction_attempt} label="Fit LLM" />
        </div>
      </div>

      <LLMAttemptWarning
        layers={[
          {
            key: 'fit_assessment',
            label: 'Оценка соответствия',
            attempt: fitAssessment?.extraction_attempt,
          },
        ]}
      />

      {mismatchMap.summary && (
        <p className="mismatch-map-summary">{mismatchMap.summary}</p>
      )}

      {sorted.length === 0 ? (
        <div className="mismatch-empty">
          <p>No mismatches detected between article and venue.</p>
        </div>
      ) : (
        <div className="mismatch-list">
          {sorted.map(item => (
            <MismatchRow key={item.mismatch_id} item={item} />
          ))}
        </div>
      )}

      {mismatchMap.unknowns && mismatchMap.unknowns.length > 0 && (
        <div className="mismatch-unknowns">
          <h3>Unknowns</h3>
          <ul>
            {mismatchMap.unknowns.map((u, i) => (
              <li key={i}>{u}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
