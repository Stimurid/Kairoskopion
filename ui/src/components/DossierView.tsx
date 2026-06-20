import { useState, useEffect } from 'react';
import type { Dossier } from '../types/domain';
import { api } from '../api/client';
import { DecisionLog } from './DecisionLog';

interface Props {
  caseId: string;
}

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(true);
  return (
    <div className="dossier-section">
      <button className="dossier-section-header" onClick={() => setOpen(!open)}>
        <span className="dossier-section-title">{title}</span>
        <span className="dossier-section-toggle">{open ? '▴' : '▾'}</span>
      </button>
      {open && <div className="dossier-section-body">{children}</div>}
    </div>
  );
}

function KVRow({ label, value }: { label: string; value: string | number | boolean | null | undefined }) {
  if (value == null || value === '') return null;
  return (
    <div className="dossier-kv">
      <span className="dossier-kv-label">{label}</span>
      <span className="dossier-kv-value">{String(value)}</span>
    </div>
  );
}

export function DossierView({ caseId }: Props) {
  const [dossier, setDossier] = useState<Dossier | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'decisions'>('overview');

  useEffect(() => {
    setIsLoading(true);
    api.getDossier(caseId)
      .then(setDossier)
      .catch(e => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setIsLoading(false));
  }, [caseId]);

  if (isLoading) {
    return <div className="placeholder-view"><p>Building dossier...</p></div>;
  }

  if (error) {
    return <div className="placeholder-view"><p className="error-text">{error}</p></div>;
  }

  if (!dossier) {
    return <div className="placeholder-view"><h2>Dossier</h2><p>No dossier data available.</p></div>;
  }

  return (
    <div className="dossier-view">
      <div className="dossier-header">
        <div className="dossier-header-left">
          <h2>Dossier: {dossier.title}</h2>
          <span className="dossier-stage-badge">{dossier.stage}</span>
        </div>
        <span className="dossier-generated">Generated: {dossier.generated_at}</span>
      </div>

      <div className="dossier-tabs">
        <button
          className={`type-chip ${activeTab === 'overview' ? 'type-chip--active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          Overview
        </button>
        <button
          className={`type-chip ${activeTab === 'decisions' ? 'type-chip--active' : ''}`}
          onClick={() => setActiveTab('decisions')}
        >
          Decision Log ({dossier.decision_log.length})
        </button>
      </div>

      {activeTab === 'overview' ? (
        <div className="dossier-overview">
          {dossier.article_model && (
            <SectionCard title="Article Model">
              <KVRow label="Title" value={dossier.article_model.title} />
              <KVRow label="Lifecycle" value={dossier.article_model.lifecycle_status} />
              <KVRow label="Confidence" value={dossier.article_model.confidence} />
              {dossier.article_model.protected_core.length > 0 && (
                <div className="dossier-kv">
                  <span className="dossier-kv-label">Protected Core</span>
                  <div className="dossier-chip-list">
                    {dossier.article_model.protected_core.map((c, i) => (
                      <span key={i} className="core-element core-element--safe">{c}</span>
                    ))}
                  </div>
                </div>
              )}
            </SectionCard>
          )}

          {dossier.scenario && (
            <SectionCard title="Submission Scenario">
              {dossier.scenario.scenario_preliminary && (
                <div className="scenario-preliminary-banner" role="note">
                  <strong>⚠ Сценарий публикации — предварительный</strong>
                  <p>
                    Оператор пока не заполнил сценарий подачи.
                    Fit-вердикт построен на дефолтных предпосылках;
                    после заполнения сценария результат может измениться.
                  </p>
                </div>
              )}
              <KVRow label="Goal" value={dossier.scenario.goal} />
              <KVRow label="Rewrite Depth" value={dossier.scenario.rewrite_depth_allowed} />
              <KVRow label="Language" value={dossier.scenario.language} />
              <KVRow label="Risk Tolerance" value={dossier.scenario.risk_tolerance} />
            </SectionCard>
          )}

          {dossier.pathways && dossier.pathways.length > 0 && (
            <SectionCard title={`Pathways (${dossier.pathways.length})`}>
              {dossier.pathways.map((p, i) => (
                <div key={i} className="dossier-pathway-row">
                  <span className="dossier-pathway-rank">#{p.rank}</span>
                  <span className="dossier-pathway-name">{p.discipline_name}</span>
                  <span className={`pathway-badge fit-${p.fit_strength}`}>{p.fit_strength}</span>
                </div>
              ))}
            </SectionCard>
          )}

          {dossier.selected_venue && (
            <SectionCard title="Selected Venue">
              <KVRow label="Name" value={dossier.selected_venue.canonical_name} />
              <KVRow label="Type" value={dossier.selected_venue.venue_type} />
              <KVRow label="Confidence" value={dossier.selected_venue.confidence} />
              <KVRow label="APC" value={dossier.selected_venue.apc_policy} />
            </SectionCard>
          )}

          {dossier.fit_assessment && (
            <SectionCard
              title={`Матрица соответствия — Fit matrix (${dossier.fit_assessment.axes?.length ?? 0} осей)`}
            >
              <KVRow label="Overall" value={dossier.fit_assessment.overall_label} />
              <KVRow label="Level" value={dossier.fit_assessment.assessment_level} />
              <KVRow label="Confidence" value={dossier.fit_assessment.confidence} />
              <KVRow label="Recommendation" value={dossier.fit_assessment.recommendation} />

              {dossier.fit_assessment.axes && dossier.fit_assessment.axes.length > 0 ? (
                <div className="fit-axes-table" role="table" aria-label="Fit matrix axes">
                  <div className="fit-axes-head" role="row">
                    <span className="fit-axes-col-axis">Axis</span>
                    <span className="fit-axes-col-value">Value</span>
                    <span className="fit-axes-col-conf">Confidence</span>
                    <span className="fit-axes-col-notes">Reason / notes</span>
                  </div>
                  {dossier.fit_assessment.axes.map((ax, i) => {
                    const valueClass =
                      `fit-axis-value fit-axis-value--${(ax.value || 'unknown')}`;
                    return (
                      <div key={i} className="fit-axes-row" role="row">
                        <span className="fit-axes-col-axis">
                          <code>{ax.axis}</code>
                        </span>
                        <span className="fit-axes-col-value">
                          <span className={valueClass}>{ax.value || 'unknown'}</span>
                        </span>
                        <span className="fit-axes-col-conf">
                          {ax.confidence ? (
                            <span className={`fit-axis-conf fit-axis-conf--${ax.confidence}`}>
                              {ax.confidence}
                            </span>
                          ) : (
                            <em className="fit-axis-muted">—</em>
                          )}
                        </span>
                        <span className="fit-axes-col-notes">
                          {ax.notes ? (
                            ax.notes
                          ) : ax.value === 'unknown' ? (
                            <em className="fit-axis-muted">
                              Неизвестно: недостаточно данных
                            </em>
                          ) : (
                            <em className="fit-axis-muted">
                              Комментарий пока не построен — reason unavailable
                            </em>
                          )}
                          {ax.unknowns && ax.unknowns.length > 0 && (
                            <ul className="fit-axis-unknowns">
                              {ax.unknowns.map((u, j) => (
                                <li key={j}>{u}</li>
                              ))}
                            </ul>
                          )}
                          {ax.evidence_refs && ax.evidence_refs.length > 0 && (
                            <div className="fit-axis-evidence">
                              evidence: {ax.evidence_refs.length}
                            </div>
                          )}
                        </span>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="fit-axes-empty">
                  Fit-матрица пока не построена. Выберите площадку и запустите fit.
                </p>
              )}

              {dossier.fit_assessment.unknowns && dossier.fit_assessment.unknowns.length > 0 && (
                <div className="fit-overall-unknowns">
                  <strong>Что система явно НЕ знает по этому fit-проходу:</strong>
                  <ul>
                    {dossier.fit_assessment.unknowns.map((u, i) => (
                      <li key={i}>{u}</li>
                    ))}
                  </ul>
                </div>
              )}
            </SectionCard>
          )}

          {/* Risk report — built by Case._run_fit_chain after select_venue.
              Backend payload at api/cases.py:1459-1460. */}
          {dossier.risk_report ? (
            <SectionCard
              title={
                `Риски подачи — Risk report` +
                (dossier.risk_report.risk_items?.length
                  ? ` (${dossier.risk_report.risk_items.length})`
                  : '')
              }
            >
              {dossier.risk_report.overall_risk_label && (
                <KVRow label="Overall risk" value={dossier.risk_report.overall_risk_label} />
              )}
              {dossier.risk_report.blocking_risks
                && dossier.risk_report.blocking_risks.length > 0 && (
                <div className="risk-blocking-list" role="alert">
                  <strong>Blocking risks ({dossier.risk_report.blocking_risks.length}):</strong>
                  <ul>
                    {dossier.risk_report.blocking_risks.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </div>
              )}
              {dossier.risk_report.warnings
                && dossier.risk_report.warnings.length > 0 && (
                <div className="risk-warnings-list" role="note">
                  <strong>Warnings ({dossier.risk_report.warnings.length}):</strong>
                  <ul>
                    {dossier.risk_report.warnings.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}
              {dossier.risk_report.risk_items
                && dossier.risk_report.risk_items.length > 0 ? (
                <div className="risk-items">
                  {dossier.risk_report.risk_items.map((r, i) => (
                    <div
                      key={i}
                      className={`risk-item risk-item--${r.severity || 'informational'}`}
                    >
                      <div className="risk-item-head">
                        <code className="risk-item-type">{r.risk_type}</code>
                        <span className={`severity-badge severity-${r.severity || 'informational'}`}>
                          {r.severity || 'unknown'}
                        </span>
                        {r.likelihood && (
                          <span className="risk-item-likelihood">
                            likelihood: {r.likelihood}
                          </span>
                        )}
                        {r.requires_user_action && (
                          <span className="risk-item-user-action">
                            requires user action
                          </span>
                        )}
                      </div>
                      <p className="risk-item-desc">{r.description}</p>
                      {r.mitigation ? (
                        <p className="risk-item-mitigation">
                          <strong>Mitigation:</strong> {r.mitigation}
                        </p>
                      ) : (
                        <p className="risk-item-mitigation risk-item-mitigation--muted">
                          <em>Mitigation not provided.</em>
                        </p>
                      )}
                      {r.evidence_refs && r.evidence_refs.length > 0 && (
                        <div className="risk-item-evidence">
                          evidence: {r.evidence_refs.length}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="risk-items-empty">
                  Список рисков пуст — система не выявила отдельных пунктов риска
                  для этой пары статья×площадка.
                </p>
              )}
              {dossier.risk_report.unknowns
                && dossier.risk_report.unknowns.length > 0 && (
                <div className="risk-unknowns">
                  <strong>Risk-зоны без оценки (unknowns):</strong>
                  <ul>
                    {dossier.risk_report.unknowns.map((u, i) => (
                      <li key={i}>{u}</li>
                    ))}
                  </ul>
                </div>
              )}
            </SectionCard>
          ) : (
            <SectionCard title="Риски подачи — Risk report">
              <p className="risk-report-missing">
                Risk report not built for this case yet.
                Подача в анализ рисков запускается после выбора площадки
                и запуска fit-проверки.
              </p>
            </SectionCard>
          )}

          {dossier.mismatch_map && dossier.mismatch_map.mismatches.length > 0 && (
            <SectionCard title={`Mismatches (${dossier.mismatch_map.mismatches.length})`}>
              <p className="dossier-text-sm">{dossier.mismatch_map.summary}</p>
              {dossier.mismatch_map.mismatches.map((m, i) => (
                <div key={i} className="dossier-mismatch-row">
                  <span className={`severity-badge severity-${m.severity}`}>{m.severity}</span>
                  <span>{m.axis}: {m.description}</span>
                </div>
              ))}
            </SectionCard>
          )}

          {dossier.rewrite_plan && (
            <SectionCard title="Rewrite Plan">
              <KVRow label="Effort" value={dossier.rewrite_plan.estimated_effort} />
              <KVRow label="Changes" value={dossier.rewrite_plan.changes.length} />
              <KVRow label="Summary" value={dossier.rewrite_plan.summary} />
            </SectionCard>
          )}

          {Object.keys(dossier.quality_gates).length > 0 && (
            <SectionCard title="Quality Gates">
              {Object.entries(dossier.quality_gates).map(([gateId, gate]) => (
                <div key={gateId} className="dossier-gate-row">
                  <span className={`gate-chip gate-${gate.status}`}>
                    <span className="gate-name">{gate.gate_name}</span>
                  </span>
                </div>
              ))}
            </SectionCard>
          )}
        </div>
      ) : (
        <DecisionLog caseId={caseId} />
      )}
    </div>
  );
}
