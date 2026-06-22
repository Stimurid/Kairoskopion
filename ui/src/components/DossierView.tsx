import { useState, useEffect } from 'react';
import type {
  Dossier,
  CitationPlanV2D,
  ComplianceChecklistV2D,
  ComplianceItemV2D,
  SubmissionPackV2D,
  BibliographyProfileV2E,
} from '../types/domain';
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
              {dossier.article_model.title ? (
                <KVRow label="Title" value={dossier.article_model.title} />
              ) : (
                <div className="dossier-kv">
                  <span className="dossier-kv-label">Title</span>
                  <em className="fit-axis-muted">
                    Не извлечено модели — H1/title заголовок статьи не распознан
                  </em>
                </div>
              )}
              {dossier.article_model.genre ? (
                <KVRow label="Genre" value={dossier.article_model.genre} />
              ) : (
                <div className="dossier-kv">
                  <span className="dossier-kv-label">Genre</span>
                  <em className="fit-axis-muted">
                    Жанр не определён — article modeler не вынес решения
                  </em>
                </div>
              )}
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
              {dossier.article_model.unknowns
                && dossier.article_model.unknowns.length > 0 && (
                <div className="article-model-unknowns">
                  <strong>Unknowns ({dossier.article_model.unknowns.length}):</strong>
                  <ul>
                    {dossier.article_model.unknowns.slice(0, 8).map((u, i) => (
                      <li key={i}>{u}</li>
                    ))}
                  </ul>
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

          {dossier.pathways && dossier.pathways.length > 0 ? (
            <SectionCard title={`Pathways (${dossier.pathways.length})`}>
              {dossier.pathways.map((p, i) => (
                <div key={i} className="dossier-pathway-row">
                  <span className="dossier-pathway-rank">#{p.rank}</span>
                  <span className="dossier-pathway-name">{p.discipline_name}</span>
                  <span className={`pathway-badge fit-${p.fit_strength}`}>{p.fit_strength}</span>
                </div>
              ))}
            </SectionCard>
          ) : (
            <SectionCard title="Pathways (0)">
              <p className="placeholder-note">
                Дисциплинарные пути ещё не выведены — pathway mapper не вернул
                кандидатов для этой статьи. Это не ошибка fit-проверки.
              </p>
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

              {/* V2-B1/B2: structured narrator coverage diagnostic */}
              {dossier.mismatch_map.narrator_coverage && (
                <div className={`narrator-coverage narrator-coverage--${dossier.mismatch_map.narrator_coverage.narrator_status}`}>
                  <div className="narrator-coverage-head">
                    <strong>LLM mismatch narrator</strong>
                    <span className={`narrator-status-badge narrator-status--${dossier.mismatch_map.narrator_coverage.narrator_status}`}>
                      {dossier.mismatch_map.narrator_coverage.narrator_status}
                    </span>
                    <span className="narrator-coverage-count">
                      filled: {dossier.mismatch_map.narrator_coverage.filled_count}
                      /{dossier.mismatch_map.narrator_coverage.total_count}
                    </span>
                  </div>
                  {dossier.mismatch_map.narrator_coverage.empty_reason && (
                    <p className="narrator-coverage-reason">
                      {dossier.mismatch_map.narrator_coverage.empty_reason}
                    </p>
                  )}
                  {dossier.mismatch_map.narrator_coverage.parse_failure_category && (
                    <div className="narrator-coverage-parse">
                      <code>parse_failure_category:</code> {dossier.mismatch_map.narrator_coverage.parse_failure_category}
                      {dossier.mismatch_map.narrator_coverage.schema_failure_path && (
                        <span> · path: <code>{dossier.mismatch_map.narrator_coverage.schema_failure_path}</code></span>
                      )}
                      {dossier.mismatch_map.narrator_coverage.repair_failure_stage && (
                        <span> · last repair: <code>{dossier.mismatch_map.narrator_coverage.repair_failure_stage}</code></span>
                      )}
                    </div>
                  )}
                  {dossier.mismatch_map.narrator_coverage.missing_axes
                    && dossier.mismatch_map.narrator_coverage.missing_axes.length > 0 && (
                    <div className="narrator-coverage-missing">
                      missing axes: {dossier.mismatch_map.narrator_coverage.missing_axes.join(', ')}
                    </div>
                  )}
                  {dossier.mismatch_map.narrator_coverage.unmatched_axes
                    && dossier.mismatch_map.narrator_coverage.unmatched_axes.length > 0 && (
                    <div className="narrator-coverage-unmatched">
                      unmatched axes: {dossier.mismatch_map.narrator_coverage.unmatched_axes.join(', ')}
                    </div>
                  )}
                  <p className="narrator-coverage-note">
                    Fit, risk и rewrite строятся независимо от narrator —
                    они уже посчитаны, даже если LLM-комментарий по площадке не дошёл.
                  </p>
                </div>
              )}

              <div className="dossier-mismatch-list">
                {dossier.mismatch_map.mismatches.map((m, i) => (
                  <div key={i} className={`dossier-mismatch-card narrative-${m.narrative_status || 'unknown'}`}>
                    <div className="dossier-mismatch-head">
                      <span className={`severity-badge severity-${m.severity}`}>{m.severity}</span>
                      <code className="dossier-mismatch-axis">{m.axis}</code>
                      {m.narrative_status && (
                        <span className={`narrative-badge narrative-badge--${m.narrative_status}`}>
                          {m.narrative_status}
                        </span>
                      )}
                    </div>
                    {m.article_side && (
                      <p className="dossier-mismatch-side">
                        <strong>Article:</strong> {m.article_side}
                      </p>
                    )}
                    {m.venue_side ? (
                      <p className="dossier-mismatch-side">
                        <strong>Venue:</strong> {m.venue_side}
                      </p>
                    ) : (
                      <p className="dossier-mismatch-side dossier-mismatch-side--muted">
                        <em>
                          {m.narrative_status === 'unknown_due_to_venue_evidence'
                            ? 'Venue: текст площадки не задаёт явных ожиданий по этой оси.'
                            : m.narrative_status === 'parse_failed'
                            ? 'Venue: LLM-комментарий не прошёл проверку схемы (см. блок narrator coverage выше).'
                            : m.narrative_status === 'provider_error'
                            ? 'Venue: LLM-провайдер недоступен.'
                            : 'Venue: требуется LLM-комментарий по площадке.'}
                        </em>
                      </p>
                    )}
                    {m.description && m.description !== m.article_side && (
                      <p className="dossier-mismatch-desc">{m.description}</p>
                    )}
                    {m.possible_actions && m.possible_actions.length > 0 && (
                      <ul className="dossier-mismatch-actions">
                        {m.possible_actions.map((a, j) => (
                          <li key={j}>{a}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
            </SectionCard>
          )}

          {dossier.rewrite_plan && (
            <SectionCard title="Rewrite Plan">
              <KVRow label="Effort" value={dossier.rewrite_plan.estimated_effort} />
              <KVRow label="Changes" value={dossier.rewrite_plan.changes.length} />
              <KVRow label="Summary" value={dossier.rewrite_plan.summary} />
            </SectionCard>
          )}

          {/* V2-E: BibliographyProfile (structural). Renders before
              CitationPlan because CitationPlan/Compliance/Pack depend
              on it. */}
          {dossier.bibliography_profile ? (
            <SectionCard
              title={`Bibliography profile — статус: ${dossier.bibliography_profile.status}`}
            >
              <BibliographyProfileSection bp={dossier.bibliography_profile} />
            </SectionCard>
          ) : (
            <SectionCard title="Bibliography profile">
              <p className="placeholder-note">
                <strong>Bibliography profile not built yet.</strong>{' '}
                Будет построен автоматически из текста статьи после
                fit-цепи.
              </p>
            </SectionCard>
          )}

          {/* V2-D: real CitationPlan when built, V2-C placeholder otherwise */}
          {dossier.citation_plan ? (
            <SectionCard title={`Citation plan — статус: ${dossier.citation_plan.status}`}>
              <CitationPlanSection plan={dossier.citation_plan} />
            </SectionCard>
          ) : (
            <SectionCard title="Citation plan">
              <p className="placeholder-note">
                <strong>Citation plan not built yet</strong> для этого case.
                Будет построен автоматически после fit chain.
              </p>
            </SectionCard>
          )}

          {dossier.compliance_checklist ? (
            <SectionCard
              title={`Compliance checklist — статус: ${dossier.compliance_checklist.status}`}
            >
              <ComplianceChecklistSection checklist={dossier.compliance_checklist} />
            </SectionCard>
          ) : (
            <SectionCard title="Compliance checklist">
              <p className="placeholder-note">
                <strong>Compliance checklist not built yet</strong> для этого case.
              </p>
            </SectionCard>
          )}

          {dossier.submission_pack ? (
            <SectionCard
              title={`Submission pack readiness — ${dossier.submission_pack.ready_status}`}
            >
              <SubmissionPackSection pack={dossier.submission_pack} />
            </SectionCard>
          ) : (
            <SectionCard title="Submission pack">
              <p className="placeholder-note">
                <strong>Submission pack not built yet</strong> для этого case.
              </p>
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

          {/* V2-C: explicit next-action block computed from dossier shape.
              No new state on case — pure derivation. */}
          <SectionCard title="Next action">
            <NextActionBlock dossier={dossier} />
          </SectionCard>
        </div>
      ) : (
        <DecisionLog caseId={caseId} />
      )}
    </div>
  );
}


function NextActionBlock({ dossier }: { dossier: Dossier }) {
  const steps: { label: string; status: 'done' | 'pending'; note?: string }[] = [];
  steps.push({
    label: 'Article model built',
    status: dossier.article_model ? 'done' : 'pending',
  });
  steps.push({
    label: 'Venue selected',
    status: dossier.selected_venue ? 'done' : 'pending',
  });
  steps.push({
    label: 'Scenario provided',
    status: (dossier.scenario && !dossier.scenario.scenario_preliminary)
      ? 'done' : 'pending',
    note: dossier.scenario?.scenario_preliminary
      ? 'preliminary — заполните сценарий подачи для уточнения fit'
      : undefined,
  });
  steps.push({
    label: 'Fit matrix built',
    status: (dossier.fit_assessment && dossier.fit_assessment.axes
      && dossier.fit_assessment.axes.length > 0) ? 'done' : 'pending',
  });
  steps.push({
    label: 'Mismatch narrator filled',
    status: (dossier.mismatch_map?.narrator_coverage?.narrator_status === 'filled'
      || dossier.mismatch_map?.narrator_coverage?.narrator_status === 'partial')
      ? 'done' : 'pending',
    note: dossier.mismatch_map?.narrator_coverage?.narrator_status === 'parse_failed'
      ? `LLM-комментарий не прошёл проверку (${dossier.mismatch_map.narrator_coverage.parse_failure_category || 'parse_failed'}) — fit/risk/rewrite уже посчитаны`
      : dossier.mismatch_map?.narrator_coverage?.narrator_status === 'empty_valid_unknown'
      ? 'LLM честно отказался: текст площадки не задаёт явных ожиданий — добавьте подробный текст площадки'
      : undefined,
  });
  steps.push({
    label: 'Risk report built',
    status: dossier.risk_report ? 'done' : 'pending',
  });
  steps.push({
    label: 'Rewrite plan built',
    status: (dossier.rewrite_plan && dossier.rewrite_plan.changes.length > 0)
      ? 'done' : 'pending',
  });
  // V2-E bibliography step (priority — gates citation/compliance/pack)
  const bp = dossier.bibliography_profile;
  steps.push({
    label: 'Bibliography profile',
    status: (bp && ['parsed_structural', 'partial'].includes(bp.status))
      ? 'done' : 'pending',
    note: !bp
      ? 'not built yet'
      : bp.status === 'unknown'
      ? 'raw text unavailable — provide manuscript'
      : bp.status === 'not_found'
      ? 'add References / Bibliography / Список литературы section'
      : bp.status === 'present_unparsed'
      ? 'heading found but no refs parsed — check formatting'
      : bp.status === 'malformed'
      ? `${bp.malformed_count}/${bp.reference_count} refs malformed`
      : bp.verification_status !== 'verified'
      ? `parsed (${bp.reference_count} refs, ${bp.doi_count} DOI); external verification pending`
      : undefined,
  });
  // V2-D real lanes
  steps.push({
    label: 'Citation plan',
    status: (dossier.citation_plan
      && ['partially_ready', 'search_tasks_ready', 'draft'].includes(dossier.citation_plan.status))
      ? 'done' : 'pending',
    note: dossier.citation_plan?.status === 'needs_bibliography'
      ? 'нужна распарсенная библиография'
      : dossier.citation_plan?.status === 'needs_venue_corpus'
      ? 'нужен корпус площадки'
      : dossier.citation_plan?.status === 'blocked_missing_evidence'
      ? 'нет ни библиографии, ни текста площадки'
      : undefined,
  });
  steps.push({
    label: 'Compliance checklist',
    status: dossier.compliance_checklist?.status === 'ready' ? 'done' : 'pending',
    note: dossier.compliance_checklist
      ? `статус ${dossier.compliance_checklist.status} (${dossier.compliance_checklist.missing_items.length} missing, ${dossier.compliance_checklist.unknowns.length} unknown)`
      : undefined,
  });
  steps.push({
    label: 'Submission pack readiness',
    status: dossier.submission_pack?.ready_status === 'ready_for_manual_submission'
      ? 'done' : 'pending',
    note: dossier.submission_pack
      ? `ready_status: ${dossier.submission_pack.ready_status}`
      : undefined,
  });

  // V2-D: prefer SubmissionPack.next_actions when present.
  const packNext = dossier.submission_pack?.next_actions || [];
  const firstPending = steps.find(s => s.status === 'pending');

  let primary: string;
  if (packNext.length > 0 && firstPending) {
    primary = packNext[0];
  } else if (!firstPending) {
    primary = 'Все основные секции построены. Откройте Risk и Rewrite plan и решите, какие изменения принять.';
  } else if (firstPending.label === 'Scenario provided') {
    primary = 'Заполните SubmissionScenario (цель, дедлайн, риск-толерантность, APC max) — это уточнит fit-вердикт.';
  } else if (firstPending.label === 'Mismatch narrator filled' && firstPending.note) {
    primary = firstPending.note;
  } else {
    primary = `Следующий шаг: ${firstPending.label.toLowerCase()}.`;
  }

  return (
    <div className="next-action-block">
      <p className="next-action-primary"><strong>{primary}</strong></p>
      <ul className="next-action-checklist">
        {steps.map((s, i) => (
          <li key={i} className={`next-action-step next-action-step--${s.status}`}>
            <span className="next-action-marker">{s.status === 'done' ? '✓' : '○'}</span>
            <span className="next-action-label">{s.label}</span>
            {s.note && <em className="next-action-note"> — {s.note}</em>}
          </li>
        ))}
      </ul>
      {packNext.length > 1 && (
        <details className="next-action-pack-details">
          <summary>Все next actions из SubmissionPack ({packNext.length})</summary>
          <ol className="next-action-pack-list">
            {packNext.map((a, i) => <li key={i}>{a}</li>)}
          </ol>
        </details>
      )}
    </div>
  );
}


function CitationPlanSection({ plan }: { plan: CitationPlanV2D }) {
  return (
    <div className="lane-section">
      <div className="lane-head">
        <span className={`lane-status-badge lane-status--${plan.status}`}>
          {plan.status}
        </span>
        {plan.semantic_status && (
          <span className={`semantic-status-badge semantic-status--${plan.semantic_status}`}>
            semantic: {plan.semantic_status}
          </span>
        )}
        {plan.confidence && (
          <span className={`lane-conf lane-conf--${plan.confidence}`}>
            confidence: {plan.confidence}
          </span>
        )}
        {plan.created_from && plan.created_from.length > 0 && (
          <span className="lane-created-from">
            built from: {plan.created_from.join(', ')}
          </span>
        )}
      </div>
      {plan.semantic_status === 'needs_llm' && (
        <div className="round2-needs-llm-banner" role="note">
          <strong>Семантические поля пусты — нужен LLM citation-organ.</strong>{' '}
          Категории gap, missing bridges, search tasks и padding-warnings
          намеренно не генерируются детерминированным кодом (Round II doctrine):
          они появятся только когда будет подключён LLM-агент citation_planner.
          Структурные поля (status, bibliography_status, verification tasks) —
          уже доступны.
        </div>
      )}
      <KVRow label="Bibliography status" value={plan.current_bibliography_status} />
      <KVRow label="Venue citation expectation" value={plan.venue_citation_expectation_status} />

      {plan.citation_gap_categories.length > 0 && (
        <div className="lane-list-block">
          <strong>Citation gap categories ({plan.citation_gap_categories.length}):</strong>
          <ul>
            {plan.citation_gap_categories.map((g, i) => <li key={i}>{g}</li>)}
          </ul>
        </div>
      )}
      {plan.missing_bridge_categories.length > 0 && (
        <div className="lane-list-block">
          <strong>Missing bridge categories ({plan.missing_bridge_categories.length}):</strong>
          <ul>
            {plan.missing_bridge_categories.map((g, i) => <li key={i}>{g}</li>)}
          </ul>
        </div>
      )}
      {plan.recommended_reference_search_tasks.length > 0 && (
        <div className="lane-list-block">
          <strong>Search tasks ({plan.recommended_reference_search_tasks.length}):</strong>
          <ul>
            {plan.recommended_reference_search_tasks.map((t, i) => <li key={i}>{t}</li>)}
          </ul>
        </div>
      )}
      {plan.verification_tasks.length > 0 && (
        <div className="lane-list-block">
          <strong>Verification tasks ({plan.verification_tasks.length}):</strong>
          <ul>
            {plan.verification_tasks.map((t, i) => <li key={i}>{t}</li>)}
          </ul>
        </div>
      )}
      {plan.dangerous_padding_warnings.length > 0 && (
        <div className="lane-warning-block" role="alert">
          <strong>⚠ Padding warning:</strong>
          <ul>
            {plan.dangerous_padding_warnings.map((w, i) => <li key={i}>{w}</li>)}
          </ul>
        </div>
      )}
      {plan.unknowns.length > 0 && (
        <div className="lane-unknowns">
          <strong>Unknowns ({plan.unknowns.length}):</strong>
          <ul>
            {plan.unknowns.map((u, i) => <li key={i}>{u}</li>)}
          </ul>
        </div>
      )}
      <p className="lane-disclaimer">
        <em>
          CitationPlan не предлагает конкретные ссылки — это карта работ.
          Конкретные источники должен подобрать автор; см. dangerous_padding_warnings.
        </em>
      </p>
    </div>
  );
}


function ComplianceChecklistSection({ checklist }: { checklist: ComplianceChecklistV2D }) {
  // Group items by category
  const byCategory: Record<string, ComplianceItemV2D[]> = {};
  for (const it of checklist.checklist_items) {
    (byCategory[it.category] ||= []).push(it);
  }
  return (
    <div className="lane-section">
      <div className="lane-head">
        <span className={`lane-status-badge lane-status--${checklist.status}`}>
          {checklist.status}
        </span>
        {checklist.confidence && (
          <span className={`lane-conf lane-conf--${checklist.confidence}`}>
            confidence: {checklist.confidence}
          </span>
        )}
        <span className="lane-counter">
          {checklist.checklist_items.length} items ·
          {' '}{checklist.missing_items.length} missing ·
          {' '}{checklist.unknowns.length} unknown
        </span>
      </div>
      {checklist.blocking_items.length > 0 && (
        <div className="lane-warning-block" role="alert">
          <strong>Blocking items:</strong>
          <ul>{checklist.blocking_items.map((b, i) => <li key={i}>{b}</li>)}</ul>
        </div>
      )}
      <div className="compliance-items">
        {Object.entries(byCategory).map(([cat, items]) => (
          <div key={cat} className="compliance-category">
            <div className="compliance-category-head">
              <code>{cat}</code>
            </div>
            {items.map(it => (
              <div key={it.item_id} className={`compliance-item compliance-item--${it.status}`}>
                <div className="compliance-item-head">
                  <span className={`compliance-status-badge compliance-status--${it.status}`}>
                    {it.status}
                  </span>
                  <span className="compliance-item-req">{it.requirement}</span>
                  {it.source_status && (
                    <span className="compliance-source">src: {it.source_status}</span>
                  )}
                </div>
                {it.notes && <p className="compliance-item-notes">{it.notes}</p>}
              </div>
            ))}
          </div>
        ))}
      </div>
      {checklist.warnings.length > 0 && (
        <div className="lane-list-block">
          <strong>Warnings:</strong>
          <ul>{checklist.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
        </div>
      )}
      {checklist.unknowns.length > 0 && (
        <div className="lane-unknowns">
          <strong>Unknowns ({checklist.unknowns.length}):</strong>
          <ul>{checklist.unknowns.map((u, i) => <li key={i}>{u}</li>)}</ul>
        </div>
      )}
    </div>
  );
}


function SubmissionPackSection({ pack }: { pack: SubmissionPackV2D }) {
  return (
    <div className="lane-section">
      <div className="lane-head">
        <span className={`lane-status-badge lane-status--${pack.status}`}>
          {pack.status}
        </span>
        <span className={`pack-ready-badge pack-ready--${pack.ready_status}`}>
          ready: {pack.ready_status}
        </span>
        {pack.depends_on.length > 0 && (
          <span className="lane-created-from">
            depends on: {pack.depends_on.join(', ')}
          </span>
        )}
      </div>
      <p className="lane-disclaimer">
        <em>
          ⚠ This is a readiness skeleton, not final submission automation.
          No portal-specific fields, no auto-generated cover letter.
        </em>
      </p>
      {pack.blocking_issues.length > 0 && (
        <div className="lane-warning-block" role="alert">
          <strong>Blocking issues ({pack.blocking_issues.length}):</strong>
          <ul>{pack.blocking_issues.map((b, i) => <li key={i}>{b}</li>)}</ul>
        </div>
      )}
      {pack.missing_items.length > 0 && (
        <div className="lane-list-block">
          <strong>Missing items ({pack.missing_items.length}):</strong>
          <ul>{pack.missing_items.map((m, i) => <li key={i}>{m}</li>)}</ul>
        </div>
      )}
      {pack.warnings.length > 0 && (
        <div className="lane-list-block">
          <strong>Warnings ({pack.warnings.length}):</strong>
          <ul>{pack.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
        </div>
      )}
      {pack.next_actions.length > 0 && (
        <div className="lane-list-block">
          <strong>Next actions ({pack.next_actions.length}):</strong>
          <ol>{pack.next_actions.map((a, i) => <li key={i}>{a}</li>)}</ol>
        </div>
      )}
      {pack.statements.length > 0 && (
        <div className="lane-list-block">
          <strong>Statements (operator-prepared):</strong>
          <ul>{pack.statements.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
      )}
      {pack.unknowns.length > 0 && (
        <div className="lane-unknowns">
          <strong>Unknowns ({pack.unknowns.length}):</strong>
          <ul>{pack.unknowns.map((u, i) => <li key={i}>{u}</li>)}</ul>
        </div>
      )}
    </div>
  );
}


function BibliographyProfileSection({ bp }: { bp: BibliographyProfileV2E }) {
  const preview = bp.references.slice(0, 10);
  return (
    <div className="lane-section">
      <div className="lane-head">
        <span className={`lane-status-badge lane-status--${bp.status}`}>
          {bp.status}
        </span>
        <span className={`pack-ready-badge pack-ready--${bp.verification_status}`}>
          verify: {bp.verification_status}
        </span>
        {bp.confidence && (
          <span className={`lane-conf lane-conf--${bp.confidence}`}>
            confidence: {bp.confidence}
          </span>
        )}
        <span className="lane-counter">
          {bp.reference_count} refs · {bp.doi_count} DOI · {bp.url_count} URL
        </span>
      </div>
      <KVRow label="Section detected" value={String(bp.bibliography_section_detected)} />
      <KVRow label="Raw text available" value={String(bp.bibliography_text_available)} />
      <KVRow label="Source" value={bp.source} />
      {(bp.year_min || bp.year_max) && (
        <KVRow label="Year range" value={`${bp.year_min ?? '?'} – ${bp.year_max ?? '?'}`} />
      )}
      {bp.parsed_reference_count !== bp.reference_count && (
        <KVRow
          label="Parsed / total"
          value={`${bp.parsed_reference_count} / ${bp.reference_count} (unparsed: ${bp.unparsed_reference_count})`}
        />
      )}
      {bp.malformed_count > 0 && (
        <KVRow label="Malformed" value={bp.malformed_count} />
      )}
      {bp.duplicate_suspect_count > 0 && (
        <KVRow label="Duplicate suspects" value={bp.duplicate_suspect_count} />
      )}
      {bp.warnings.length > 0 && (
        <div className="lane-warning-block" role="alert">
          <strong>Warnings ({bp.warnings.length}):</strong>
          <ul>{bp.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
        </div>
      )}
      {bp.verification_tasks.length > 0 && (
        <div className="lane-list-block">
          <strong>Verification tasks ({bp.verification_tasks.length}):</strong>
          <ul>{bp.verification_tasks.map((t, i) => <li key={i}>{t}</li>)}</ul>
        </div>
      )}
      {bp.unknowns.length > 0 && (
        <div className="lane-unknowns">
          <strong>Unknowns ({bp.unknowns.length}):</strong>
          <ul>{bp.unknowns.map((u, i) => <li key={i}>{u}</li>)}</ul>
        </div>
      )}
      {preview.length > 0 && (
        <div className="lane-list-block">
          <strong>
            References preview ({preview.length} of {bp.reference_count})
          </strong>
          <ol className="bib-reference-list">
            {preview.map((r) => (
              <li key={r.reference_id} className={`bib-reference bib-reference--${r.parse_status}`}>
                <div className="bib-ref-head">
                  <span className={`bib-id-badge bib-id--${r.identifier_status}`}>
                    {r.identifier_status}
                  </span>
                  <span className={`bib-parse-badge bib-parse--${r.parse_status}`}>
                    {r.parse_status}
                  </span>
                  {r.year && <span className="bib-year">{r.year}</span>}
                  {r.doi && (
                    <code className="bib-doi">doi:{r.doi}</code>
                  )}
                </div>
                <p className="bib-raw">{r.raw_text}</p>
              </li>
            ))}
          </ol>
        </div>
      )}
      <p className="lane-disclaimer">
        <em>
          Structural bibliography profile. References are not externally
          verified unless marked so. No titles / authors / DOIs are
          invented; only what was extractable by regex from the supplied
          text.
        </em>
      </p>
    </div>
  );
}
