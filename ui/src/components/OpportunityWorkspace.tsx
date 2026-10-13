import { useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';
import '../styles/opportunity.css';

/** Data fed by a future verified importer; this view never invents W12 records. */
export type RouteKind =
  | 'FORMAL_ABSTRACT_CFP'
  | 'OPTIONAL_EDITORIAL_PRECHECK'
  | 'PRESUBMISSION_INQUIRY'
  | 'FULL_MANUSCRIPT_ONLY'
  | 'POLICY_UNVERIFIED';

export interface OpportunityRow {
  id: string;
  seedId: string;
  opportunityId: string;
  claim: string;
  scholarlyDialogue: string;
  venueId: string;
  journalName: string;
  routeKind: RouteKind;
  fit: 'FIT' | 'CONDITIONAL' | 'REJECT' | 'UNKNOWN';
  transformationCost: string;
  requiredEvidence: string[];
  readDepth: 'FULL_TEXT' | 'SECTIONS' | 'ABSTRACT' | 'INDEX_ONLY' | 'UNKNOWN';
  fullTextExampleCount: number;
  deadline?: string;
  deadlineStage?: string;
  officialRouteRef?: string;
  authorDecision: 'HOLD' | 'ACCEPT' | 'REJECT';
  evidenceRefs: string[];
  lineage: string[];
  gateStatus?: string;
  blockers?: string[];
}

export interface OpportunityTraceEvent {
  eventId: string;
  kind: string;
  subjectId: string;
  sourceRef: string;
  at: string;
  result: string;
  intellectualConsequence: string;
  reopenLevel?: string | null;
  nextAction: string;
  reason: string;
}

export interface OpportunityPortfolio {
  importStatus: 'IMPORTED_VERIFIED' | 'SOURCE_BYTES_VERIFIED_MAPPING_PENDING' | 'BLOCKED_SOURCE_BYTES_UNAVAILABLE';
  importReceipt?: string;
  seedCount: number;
  independentOpportunityCount: number;
  variantCount: number;
  distinctVenueCount: number;
  rows: OpportunityRow[];
  events?: OpportunityTraceEvent[];
}

const routeLabels: Record<RouteKind, string> = {
  FORMAL_ABSTRACT_CFP: 'Формальный конкурс аннотаций / предложений',
  OPTIONAL_EDITORIAL_PRECHECK: 'Необязательная редакционная предпроверка',
  PRESUBMISSION_INQUIRY: 'Предварительный запрос редактору',
  FULL_MANUSCRIPT_ONLY: 'Только полная рукопись',
  POLICY_UNVERIFIED: 'Редакционная политика не подтверждена',
};

const fitLabels: Record<OpportunityRow['fit'], string> = {
  FIT: 'Подходит',
  CONDITIONAL: 'Условно',
  REJECT: 'Отклонить',
  UNKNOWN: 'Недостаточно данных',
};

type Tab = 'portfolio' | 'matrix' | 'venues' | 'lineage' | 'trace';

function ImportNotice({ portfolio }: { portfolio: OpportunityPortfolio | null }) {
  if (portfolio?.importStatus === 'IMPORTED_VERIFIED') {
    return <p className="opp-import-state">Импорт подтверждён. <span>{portfolio.importReceipt}</span></p>;
  }
  return (
    <div className="opp-import-warning" role="status">
      <strong>Корпус W12 ещё не импортирован.</strong>
      <p>Индаго передала исследовательский handoff: 6 исходных замыслов, 27 смысловых версий,
        81 журнал-кандидат и 53 редакционных маршрута. Это заявленные размеры источника,
        а не количество допущенных или отправленных статей.</p>
      <p>До получения проверяемых байтов XLSX/ZIP, SHA-256 и квитанции импорта данные
        не переходят в состояние «подтверждено». Никаких отправок из этого экрана нет.</p>
    </div>
  );
}

export function OpportunityWorkspace({ portfolio = null }: { portfolio?: OpportunityPortfolio | null }) {
  const [tab, setTab] = useState<Tab>('portfolio');
  const [query, setQuery] = useState('');
  const [routeFilter, setRouteFilter] = useState<RouteKind | 'ALL'>('ALL');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [remotePortfolio, setRemotePortfolio] = useState<OpportunityPortfolio | null>(null);
  const [fetchError, setFetchError] = useState(false);

  useEffect(() => {
    if (portfolio) return;
    let active = true;
    api.getOpportunityPortfolio()
      .then((value) => { if (active) { setRemotePortfolio(value); setFetchError(false); } })
      .catch(() => { if (active) setFetchError(true); });
    return () => { active = false; };
  }, [portfolio]);

  const activePortfolio = portfolio ?? remotePortfolio;
  const rows = useMemo(() => activePortfolio?.rows ?? [], [activePortfolio]);
  const events = activePortfolio?.events ?? [];

  const filtered = useMemo(() => {
    const q = query.trim().toLocaleLowerCase('ru-RU');
    return rows.filter((row) =>
      (routeFilter === 'ALL' || row.routeKind === routeFilter) &&
      (!q || [row.seedId, row.journalName, row.claim, row.scholarlyDialogue, row.opportunityId]
        .some((part) => part.toLocaleLowerCase('ru-RU').includes(q))),
    );
  }, [rows, query, routeFilter]);
  const selected = rows.find((row) => row.id === selectedId) ?? filtered[0] ?? null;
  const venues = [...new Map(rows.map((row) => [row.venueId, row.journalName])).entries()];

  return (
    <main className="opportunity-workspace" aria-label="Пространство публикационных возможностей">
      <header className="opp-header">
        <div>
          <p className="opp-eyebrow">INDAGO × HEAD-TRIMURTI</p>
          <h2>Пространство публикационных возможностей</h2>
          <p>От исследовательского замысла и научного спора — к обоснованной редакционной траектории.
            Не путать с пакетным исполнением над готовыми статьями.</p>
        </div>
      </header>

      <ImportNotice portfolio={activePortfolio} />
      {fetchError && <p className="opp-fetch-warning" role="alert">
        Не удалось получить живые данные реестра с сервера. Показанные нулевые значения
        не означают, что исследовательские возможности отсутствуют.
      </p>}

      <nav className="opp-tabs" aria-label="Разделы пространства возможностей">
        {([
          ['portfolio', 'Портфель'],
          ['matrix', 'Матрица возможностей'],
          ['venues', 'Паспорта журналов'],
          ['lineage', 'Происхождение и версии'],
          ['trace', 'Охота и отрицательные результаты'],
        ] as const).map(([key, name]) => (
          <button key={key} type="button" onClick={() => setTab(key)}
            className={tab === key ? 'opp-tab opp-tab--active' : 'opp-tab'}>
            {name}
          </button>
        ))}
      </nav>

      {tab === 'portfolio' && (
        <section className="opp-section">
          <h3>Объекты в реестре (не обязательно импорт W12)</h3>
          <div className="opp-summary">
            <div><strong>{activePortfolio?.seedCount ?? 0}</strong><span>Замыслов в хранилище</span></div>
            <div><strong>{activePortfolio?.independentOpportunityCount ?? 0}</strong><span>Самостоятельных возможностей</span></div>
            <div><strong>{activePortfolio?.variantCount ?? 0}</strong><span>Версий аргумента</span></div>
            <div><strong>{activePortfolio?.distinctVenueCount ?? 0}</strong><span>Различных журналов</span></div>
            <div><strong>{rows.length}</strong><span>Маршрутов, включая заблокированные</span></div>
          </div>
          <p className="opp-small">Не создаём 53 самостоятельные статьи из 53 редакционных действий.
            Статусы автора и машинной проверки существуют раздельно.</p>
        </section>
      )}

      {tab === 'matrix' && (
        <section className="opp-section">
          <h3>Замысел × дискуссия × журнал</h3>
          <div className="opp-filters">
            <label>Поиск<input value={query} onChange={(e) => setQuery(e.target.value)}
              placeholder="Замысел, тезис, журнал или дискуссия" /></label>
            <label>Тип редакционного действия
              <select value={routeFilter} onChange={(e) => setRouteFilter(e.target.value as RouteKind | 'ALL')}>
                <option value="ALL">Все действия</option>
                {Object.entries(routeLabels).map(([kind, label]) => <option key={kind} value={kind}>{label}</option>)}
              </select>
            </label>
          </div>
          <div className="opp-table-scroll">
            <table className="opp-table">
              <thead><tr><th>Замысел / возможность</th><th>Журнал</th><th>Маршрут</th>
                <th>Соответствие</th><th>Цена изменений</th><th>Автор</th></tr></thead>
              <tbody>
                {filtered.map((row) => (
                  <tr key={row.id}>
                    <td><button className="opp-row-link" onClick={() => { setSelectedId(row.id); setTab('lineage'); }}>
                      {row.seedId} · {row.opportunityId}</button><small>{row.claim}</small></td>
                    <td>{row.journalName}</td><td>{routeLabels[row.routeKind]}</td>
                    <td>{fitLabels[row.fit]}</td><td>{row.transformationCost}</td><td>{row.authorDecision}</td>
                  </tr>
                ))}
                {filtered.length === 0 && <tr><td colSpan={6} className="opp-empty-cell">
                  Нет проверенных записей с такими условиями. Отсутствие данных — не отрицательное научное заключение.
                </td></tr>}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {tab === 'venues' && (
        <section className="opp-section">
          <h3>Редакционные миры и доказательства</h3>
          {venues.length === 0 ? <p className="opp-empty">Нет импортированных паспортов журналов.
            Полное чтение опубликованных статей нельзя заменить списком названий или аннотаций.</p> : (
            <div className="opp-venue-grid">
              {venues.map(([venueId, name]) => {
                const examples = rows.filter((r) => r.venueId === venueId);
                const deep = examples.some((r) => r.fullTextExampleCount >= 3 && r.readDepth === 'FULL_TEXT');
                return <article key={venueId} className="opp-venue-card">
                  <h4>{name}</h4><p>{deep ? 'Есть свидетельства глубокого чтения' : 'PARTIAL_EVIDENCE — глубокая модель не принята'}</p>
                  <p>Маршруты: {examples.length}</p>
                  <ul>{examples.map((r) => <li key={r.id}>{routeLabels[r.routeKind]}
                    {r.deadline ? ' · срок: ' + r.deadline : ' · срок не подтверждён'}</li>)}</ul>
                </article>;
              })}
            </div>
          )}
        </section>
      )}

      {tab === 'lineage' && (
        <section className="opp-section">
          <h3>Генеалогия научного объекта</h3>
          {selected ? (
            <article className="opp-lineage">
              <h4>{selected.seedId} → {selected.opportunityId} → {selected.journalName}</h4>
              <p><strong>Тезис:</strong> {selected.claim}</p>
              <p><strong>Научная дискуссия:</strong> {selected.scholarlyDialogue}</p>
              <p><strong>Источники и основания:</strong> {selected.evidenceRefs.join('; ') || 'Не предъявлены'}</p>
              <p><strong>Недостающие доказательства:</strong> {selected.requiredEvidence.join('; ') || 'Не оценены'}</p>
              <p><strong>Происхождение:</strong> {selected.lineage.join(' → ') || 'Не зарегистрировано'}</p>
              <p><strong>Редакционное действие:</strong> {routeLabels[selected.routeKind]}</p>
              <p><strong>Технические ограничения:</strong> {selected.blockers?.join('; ') || 'Не предъявлены'}</p>
              <p><strong>Авторское решение:</strong> {selected.authorDecision}. Внешняя отправка — вне полномочий интерфейса.</p>
            </article>
          ) : <p className="opp-empty">Пока нечего сравнивать. После проверяемого импорта здесь будут
            версии, отвергнутые гипотезы, источниковые якоря и изменения L0–L5.</p>}
        </section>
      )}
      {tab === 'trace' && (
        <section className="opp-section">
          <h3>Дневник исследовательских решений</h3>
          <p className="opp-small">Неудачная гипотеза, редакционный отказ и недоступный источник
            — сохраняемые исследовательские события, а не повод стирать ветку.</p>
          {events.length ? (
            <div className="opp-trace-list">
              {events.map((item) => (
                <article className="opp-venue-card" key={item.eventId}>
                  <h4>{item.kind} · {item.subjectId}</h4>
                  <p><strong>Наблюдение:</strong> {item.result || 'Не описано'} · {item.reason || 'Основание не внесено'}</p>
                  <p><strong>Научное следствие:</strong> {item.intellectualConsequence || 'Ещё не установлено'}</p>
                  <p><strong>Возврат к уровню:</strong> {item.reopenLevel || 'Не назначен'}</p>
                  <p><strong>Следующее действие:</strong> {item.nextAction || 'Не сформулировано'}</p>
                  <p className="opp-small">Источник: {item.sourceRef} · {item.at || 'Дата отсутствует'}</p>
                </article>
              ))}
            </div>
          ) : <p className="opp-empty">В этом хранилище пока нет зафиксированных ходов.
            Отсутствие записей не является отрицательным результатом охоты.</p>}
        </section>
      )}

    </main>
  );
}
