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
            <SectionCard title="Fit Assessment">
              <KVRow label="Overall" value={dossier.fit_assessment.overall_label} />
              <KVRow label="Level" value={dossier.fit_assessment.assessment_level} />
              <KVRow label="Recommendation" value={dossier.fit_assessment.recommendation} />
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
