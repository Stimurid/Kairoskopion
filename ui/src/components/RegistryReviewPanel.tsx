import { useEffect, useState, useCallback } from 'react';
import { api, type RegistryRecord } from '../api/client';

type Tab = 'queue' | 'browse';

const TYPE_LABELS: Record<string, string> = {
  venue: 'Журналы',
  discipline: 'Дисциплины',
  venue_section: 'Секции',
  evidence_ref: 'Источники',
  acquisition_task: 'Задачи',
};

const STATUS_STYLES: Record<string, { label: string; cls: string }> = {
  canonical: { label: 'canonical', cls: 'registry-status--canonical' },
  provisional_with_warning: { label: 'provisional', cls: 'registry-status--provisional' },
  rejected_unusable: { label: 'rejected', cls: 'registry-status--rejected' },
  unknown: { label: 'unknown', cls: 'registry-status--unknown' },
};

function StatusBadge({ status }: { status: string | undefined }) {
  const s = STATUS_STYLES[status ?? 'unknown'] ?? STATUS_STYLES.unknown;
  return <span className={`registry-status-badge ${s.cls}`}>{s.label}</span>;
}

function recordLabel(rec: RegistryRecord): string {
  return (
    (rec.canonical_name as string) ??
    (rec.display_names as Record<string, string>)?.ru ??
    (rec.display_names as Record<string, string>)?.en ??
    (rec.section_name as string) ??
    (rec.venue_id as string) ??
    (rec.discipline_id as string) ??
    '—'
  );
}

function recordId(rec: RegistryRecord): string {
  return (
    (rec.venue_id as string) ??
    (rec.discipline_id as string) ??
    (rec.section_id as string) ??
    (rec.task_id as string) ??
    JSON.stringify(rec).slice(0, 40)
  );
}

export function RegistryReviewPanel() {
  const [tab, setTab] = useState<Tab>('queue');
  const [types, setTypes] = useState<string[]>([]);
  const [selectedType, setSelectedType] = useState<string>('');
  const [queue, setQueue] = useState<RegistryRecord[]>([]);
  const [records, setRecords] = useState<RegistryRecord[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    api.listRegistryTypes().then(setTypes).catch(() => {});
  }, []);

  const loadQueue = useCallback(() => {
    setLoading(true);
    setError(null);
    api
      .getReviewQueue(200)
      .then((data) => { setQueue(data); setError(null); })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, []);

  const loadRecords = useCallback(() => {
    if (!selectedType) return;
    setLoading(true);
    setError(null);
    api
      .listRegistryRecords(selectedType, search, 100)
      .then((data) => { setRecords(data); setError(null); })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [selectedType, search]);

  useEffect(() => {
    if (tab === 'queue') loadQueue();
  }, [tab, loadQueue]);

  useEffect(() => {
    if (tab === 'browse' && selectedType) loadRecords();
  }, [tab, selectedType, loadRecords]);

  const handleAccept = async (recType: string, recId: string) => {
    setActionInProgress(recId);
    try {
      await api.acceptRegistryRecord(recType, recId);
      if (tab === 'queue') loadQueue();
      else loadRecords();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setActionInProgress(null);
    }
  };

  const handleReject = async (recType: string, recId: string) => {
    setActionInProgress(recId);
    try {
      await api.rejectRegistryRecord(recType, recId);
      if (tab === 'queue') loadQueue();
      else loadRecords();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setActionInProgress(null);
    }
  };

  const renderRecord = (rec: RegistryRecord, showType: boolean) => {
    const id = recordId(rec);
    const recType = (rec._record_type as string) ?? selectedType;
    const isExpanded = expanded === id;
    const isPending = (rec._usage_status === 'provisional_with_warning' || rec._usage_status === 'unknown');

    return (
      <div key={id} className="registry-record-card">
        <div className="registry-record-header" onClick={() => setExpanded(isExpanded ? null : id)}>
          <div className="registry-record-label">
            {showType && (
              <span className="registry-record-type-tag">
                {TYPE_LABELS[recType] ?? recType}
              </span>
            )}
            <strong>{recordLabel(rec)}</strong>
          </div>
          <div className="registry-record-actions">
            <StatusBadge status={rec._usage_status as string} />
            {isPending && (
              <>
                <button
                  className="registry-btn registry-btn--accept"
                  disabled={actionInProgress === id}
                  onClick={(e) => { e.stopPropagation(); handleAccept(recType, id); }}
                >
                  ✓
                </button>
                <button
                  className="registry-btn registry-btn--reject"
                  disabled={actionInProgress === id}
                  onClick={(e) => { e.stopPropagation(); handleReject(recType, id); }}
                >
                  ✗
                </button>
              </>
            )}
          </div>
        </div>
        {isExpanded && (
          <pre className="registry-record-detail">
            {JSON.stringify(rec, null, 2)}
          </pre>
        )}
      </div>
    );
  };

  return (
    <div className="registry-review-panel">
      <div className="registry-review-header">
        <h3>Реестр</h3>
        <div className="registry-tabs">
          <button
            className={`registry-tab ${tab === 'queue' ? 'registry-tab--active' : ''}`}
            onClick={() => setTab('queue')}
          >
            Очередь ({queue.length})
          </button>
          <button
            className={`registry-tab ${tab === 'browse' ? 'registry-tab--active' : ''}`}
            onClick={() => setTab('browse')}
          >
            Обзор
          </button>
        </div>
      </div>

      {error && <div className="registry-error">{error}</div>}

      {tab === 'queue' && (
        <div className="registry-queue">
          {loading ? (
            <div className="registry-loading">Загрузка очереди…</div>
          ) : queue.length === 0 ? (
            <div className="registry-empty">
              Нет записей, ожидающих рецензии. Все записи приняты или отклонены.
            </div>
          ) : (
            queue.map((rec) => renderRecord(rec, true))
          )}
        </div>
      )}

      {tab === 'browse' && (
        <div className="registry-browse">
          <div className="registry-browse-controls">
            <select
              className="registry-type-select"
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
            >
              <option value="">— тип записи —</option>
              {types.map((t) => (
                <option key={t} value={t}>
                  {TYPE_LABELS[t] ?? t}
                </option>
              ))}
            </select>
            <input
              className="registry-search-input"
              type="text"
              placeholder="Поиск…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') loadRecords(); }}
            />
            <button className="registry-btn registry-btn--search" onClick={loadRecords}>
              Найти
            </button>
          </div>
          {loading ? (
            <div className="registry-loading">Загрузка…</div>
          ) : !selectedType ? (
            <div className="registry-empty">Выберите тип записи для просмотра.</div>
          ) : records.length === 0 ? (
            <div className="registry-empty">Нет записей.</div>
          ) : (
            records.map((rec) => renderRecord(rec, false))
          )}
        </div>
      )}
    </div>
  );
}
