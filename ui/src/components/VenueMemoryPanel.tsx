import { useState, useEffect } from 'react';
import { api } from '../api/client';

interface VenueMemoryRecord {
  venue_memory_id: string;
  canonical_name: string;
  issn: string | null;
  facts: { note?: string }[];
  tacit_signals: { text: string; added_at: string }[];
  prior_outcomes: { result: string; notes?: string; recorded_at?: string }[];
  staleness_status: string;
  created_at: string;
  updated_at: string;
}

export function VenueMemoryPanel() {
  const [records, setRecords] = useState<VenueMemoryRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listVenueMemory()
      .then((data) => setRecords(data as unknown as VenueMemoryRecord[]))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="venue-memory-panel"><p>Загрузка...</p></div>;
  if (records.length === 0) {
    return (
      <div className="venue-memory-panel">
        <h3>Память площадок</h3>
        <p className="empty-state">Пока нет запомненных площадок. Они появятся после первого анализа.</p>
      </div>
    );
  }

  return (
    <div className="venue-memory-panel">
      <h3>Память площадок ({records.length})</h3>
      <div className="venue-memory-list">
        {records.map((rec) => (
          <div key={rec.venue_memory_id} className="venue-memory-card">
            <div className="vmem-header">
              <strong>{rec.canonical_name}</strong>
              {rec.issn && <span className="vmem-issn">{rec.issn}</span>}
              <span className={`vmem-staleness ${rec.staleness_status}`}>
                {rec.staleness_status}
              </span>
            </div>
            {rec.facts.length > 0 && (
              <div className="vmem-facts">
                {rec.facts.slice(0, 3).map((f, i) => (
                  <span key={i} className="vmem-fact">{f.note ?? JSON.stringify(f)}</span>
                ))}
              </div>
            )}
            {rec.tacit_signals.length > 0 && (
              <div className="vmem-signals">
                {rec.tacit_signals.slice(0, 2).map((s, i) => (
                  <span key={i} className="vmem-signal">{s.text}</span>
                ))}
              </div>
            )}
            {rec.prior_outcomes.length > 0 && (
              <div className="vmem-outcomes">
                {rec.prior_outcomes.map((o, i) => (
                  <span key={i} className={`vmem-outcome ${o.result}`}>{o.result}</span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
