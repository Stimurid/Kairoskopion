import type { DisciplinaryPathway } from '../types/domain';

const FIT_CONFIG: Record<string, { label: string; className: string }> = {
  strong: { label: 'Strong', className: 'fit-strong' },
  moderate: { label: 'Moderate', className: 'fit-moderate' },
  weak: { label: 'Weak', className: 'fit-weak' },
};

const CORE_RISK_CONFIG: Record<string, { label: string; className: string }> = {
  core_preserving: { label: 'Core safe', className: 'core-preserving' },
  core_touching: { label: 'Core touched', className: 'core-touching' },
  core_transforming: { label: 'Core at risk', className: 'core-transforming' },
  core_destroying_risk: { label: 'Core threat', className: 'core-destroying' },
  unknown_core_impact: { label: 'Unknown', className: 'core-unknown' },
};

interface Props {
  pathways: DisciplinaryPathway[];
  onSelectPathway?: (pathway: DisciplinaryPathway) => void;
  selectedPathwayId?: string;
}

export function PathwayMap({ pathways, onSelectPathway, selectedPathwayId }: Props) {
  const sorted = [...pathways].sort((a, b) => a.rank - b.rank);

  return (
    <div className="pathway-map">
      <div className="pathway-map-header">
        <h2>Disciplinary Pathways</h2>
        <span className="pathway-count">{pathways.length} pathways mapped</span>
      </div>

      <div className="pathway-grid">
        {sorted.map((p) => {
          const fit = FIT_CONFIG[p.fit_strength] ?? { label: p.fit_strength, className: 'fit-unknown' };
          const core = CORE_RISK_CONFIG[p.field_core_risk] ?? CORE_RISK_CONFIG.unknown_core_impact;
          const isSelected = selectedPathwayId === p.disciplinary_pathway_id;

          return (
            <button
              key={p.disciplinary_pathway_id}
              className={`pathway-card ${isSelected ? 'pathway-card--selected' : ''}`}
              onClick={() => onSelectPathway?.(p)}
              type="button"
            >
              <div className="pathway-card-header">
                <span className="pathway-rank">#{p.rank}</span>
                <h3 className="pathway-name">{p.discipline_name}</h3>
              </div>

              <div className="pathway-badges">
                <span className={`pathway-badge ${fit.className}`}>{fit.label} fit</span>
                <span className={`pathway-badge ${core.className}`}>{core.label}</span>
                {p.confidence && (
                  <span className="pathway-badge pathway-badge--confidence">
                    confidence: {p.confidence}
                  </span>
                )}
              </div>

              {p.reasoning && (
                <p className="pathway-reasoning">{p.reasoning}</p>
              )}

              {p.required_adaptations.length > 0 && (
                <div className="pathway-adaptations">
                  <span className="pathway-section-label">Adaptations needed:</span>
                  <ul>
                    {p.required_adaptations.map((a, i) => (
                      <li key={i}>{a}</li>
                    ))}
                  </ul>
                </div>
              )}

              {p.strategic_value_notes && (
                <p className="pathway-strategic">{p.strategic_value_notes}</p>
              )}

              {p.example_venue_names.length > 0 && (
                <div className="pathway-venues">
                  <span className="pathway-section-label">Example venues:</span>
                  <div className="pathway-venue-chips">
                    {p.example_venue_names.map((v, i) => (
                      <span key={i} className="venue-chip">{v}</span>
                    ))}
                  </div>
                </div>
              )}

              {p.venue_type_hints.length > 0 && (
                <div className="pathway-type-hints">
                  {p.venue_type_hints.map((h, i) => (
                    <span key={i} className="type-hint-chip">{h}</span>
                  ))}
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
