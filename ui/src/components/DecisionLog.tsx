import { useState, useEffect } from 'react';
import type { DecisionLogEntry } from '../types/domain';
import { api } from '../api/client';

interface Props {
  caseId: string;
}

const ACTION_ICONS: Record<string, string> = {
  intake_text: '▶',
  confirm_article_model: '✓',
  set_scenario: '⚙',
  investigate_venue: '\u{1F50D}',
  select_venue: '⚑',
  discover_venues: '\u{1F30D}',
  decision_accept: '✔',
  decision_reject: '✘',
  decision_defer: '⏸',
};

function formatAction(action: string): string {
  return action
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

function formatTimestamp(ts: string): string {
  try {
    const d = new Date(ts);
    return d.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return ts;
  }
}

export function DecisionLog({ caseId }: Props) {
  const [entries, setEntries] = useState<DecisionLogEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  useEffect(() => {
    setIsLoading(true);
    api.getDecisionLog(caseId)
      .then(setEntries)
      .catch(() => setEntries([]))
      .finally(() => setIsLoading(false));
  }, [caseId]);

  const toggleExpand = (idx: number) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  if (isLoading) {
    return (
      <div className="placeholder-view">
        <p>Loading decision log...</p>
      </div>
    );
  }

  if (entries.length === 0) {
    return (
      <div className="decision-log-empty">
        <h2>Decision Log</h2>
        <p>No decisions recorded yet. Decisions are logged as you work through the case.</p>
      </div>
    );
  }

  return (
    <div className="decision-log">
      <div className="dlog-header">
        <h2>Decision Log</h2>
        <span className="dlog-count">{entries.length} decisions</span>
      </div>

      <div className="dlog-timeline">
        {entries.map((entry, i) => {
          const icon = ACTION_ICONS[entry.action] ?? '•';
          const isOpen = expanded.has(i);
          const detailKeys = Object.keys(entry.details);

          return (
            <div key={i} className="dlog-entry">
              <div className="dlog-icon">{icon}</div>
              <div className="dlog-body">
                <button
                  className="dlog-action-btn"
                  onClick={() => toggleExpand(i)}
                  aria-expanded={isOpen}
                >
                  <span className="dlog-action">{formatAction(entry.action)}</span>
                  <span className="dlog-time">{formatTimestamp(entry.timestamp)}</span>
                  {detailKeys.length > 0 && (
                    <span className="dlog-expand-icon">{isOpen ? '▴' : '▾'}</span>
                  )}
                </button>

                {isOpen && detailKeys.length > 0 && (
                  <div className="dlog-details">
                    {detailKeys.map(k => (
                      <div key={k} className="dlog-detail-row">
                        <span className="dlog-detail-key">{k}:</span>
                        <span className="dlog-detail-val">
                          {typeof entry.details[k] === 'object'
                            ? JSON.stringify(entry.details[k])
                            : String(entry.details[k] ?? '')}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
