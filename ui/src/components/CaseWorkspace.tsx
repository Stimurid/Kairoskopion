import { useState, useCallback } from 'react';
import type {
  CaseDetail,
  ArticleModel,
  EvidenceDetail,
  DisciplinaryPathway,
  VenueModel,
  PublicationRegimeModel,
  MismatchMap,
  QualityGateResult,
} from '../types/domain';
import { api } from '../api/client';
import { StatusBar } from './StatusBar';
import { EvidenceDrawer } from './EvidenceDrawer';
import { IntakeSurface } from './IntakeSurface';
import { ArticleCard } from './ArticleCard';
import { VenueProfile } from './VenueProfile';
import { ScenarioBuilder } from './ScenarioBuilder';
import { MismatchMapView } from './MismatchMapView';
import { QualityGateBar } from './QualityGateBar';

interface Props {
  caseData: CaseDetail;
  onCaseUpdate: () => void;
}

export function CaseWorkspace({ caseData, onCaseUpdate }: Props) {
  const [activeView, setActiveView] = useState<string>(caseData.stage);
  const [evidence, setEvidence] = useState<EvidenceDetail | null>(null);
  const [articleModel, setArticleModel] = useState<ArticleModel | null>(null);
  const [pathways, setPathways] = useState<DisciplinaryPathway[]>([]);
  const [venueModel, setVenueModel] = useState<VenueModel | null>(null);
  const [pubRegime, setPubRegime] = useState<PublicationRegimeModel | undefined>(undefined);
  const [mismatchMap, setMismatchMap] = useState<MismatchMap | null>(null);
  const [qualityGates, setQualityGates] = useState<Record<string, QualityGateResult>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const caseId = caseData.case_id;

  const handleStageClick = (stage: string) => {
    setActiveView(stage);
  };

  const handleError = (err: unknown) => {
    setError(err instanceof Error ? err.message : String(err));
  };

  // --- Intake ---

  const handleIntakeSubmit = useCallback(async (text: string, inputType: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await api.intakeText(caseId, text, inputType);
      if (result.article_model_built) {
        const am = await api.getArticleModel(caseId);
        setArticleModel(am);
        setActiveView('article_model');
      } else if (result.venue_investigated) {
        const venueResult = await api.getInvestigatedVenue(caseId);
        setVenueModel(venueResult.venue);
        setPubRegime(venueResult.publication_regime);
        setActiveView('venue_investigation');
      }
      onCaseUpdate();
      return result;
    } catch (e) {
      handleError(e);
    } finally {
      setIsLoading(false);
    }
  }, [caseId, onCaseUpdate]);

  // --- Article confirm ---

  const handleConfirmArticle = useCallback(async (
    protectedCore: string[],
    corrections: Record<string, string>,
  ) => {
    setIsLoading(true);
    setError(null);
    try {
      await api.confirmArticleModel(caseId, protectedCore, corrections);
      const am = await api.getArticleModel(caseId);
      setArticleModel(am);
      onCaseUpdate();
    } catch (e) {
      handleError(e);
    } finally {
      setIsLoading(false);
    }
  }, [caseId, onCaseUpdate]);

  // --- Evidence ---

  const handleEvidenceClick = useCallback(async (entityType: string, fieldPath: string) => {
    try {
      const ev = await api.getEvidence(caseId, entityType, fieldPath);
      setEvidence(ev);
    } catch (e) {
      handleError(e);
    }
  }, [caseId]);

  // --- Pathways ---

  const loadPathways = useCallback(async () => {
    setIsLoading(true);
    try {
      const p = await api.getPathways(caseId);
      setPathways(p);
      setActiveView('pathways');
      onCaseUpdate();
    } catch (e) {
      handleError(e);
    } finally {
      setIsLoading(false);
    }
  }, [caseId, onCaseUpdate]);

  // --- Scenario ---

  const handleSetScenario = useCallback(async (data: Record<string, unknown>) => {
    setIsLoading(true);
    setError(null);
    try {
      await api.setScenario(caseId, data);
      setActiveView('pathways');
      onCaseUpdate();
    } catch (e) {
      handleError(e);
    } finally {
      setIsLoading(false);
    }
  }, [caseId, onCaseUpdate]);

  // --- Mismatch map ---

  const loadMismatchMap = useCallback(async () => {
    try {
      const result = await api.getMismatchMap(caseId);
      if ('mismatches' in result && Array.isArray(result.mismatches) && result.mismatches.length > 0) {
        setMismatchMap(result as MismatchMap);
      }
    } catch { /* not available yet */ }
  }, [caseId]);

  // --- Quality gates ---

  const loadQualityGates = useCallback(async () => {
    try {
      const gates = await api.getQualityGates(caseId);
      setQualityGates(gates);
    } catch { /* not available */ }
  }, [caseId]);

  // --- Render view ---

  const renderView = () => {
    switch (activeView) {
      case 'empty':
      case 'intake':
        return (
          <IntakeSurface onSubmit={handleIntakeSubmit} isLoading={isLoading} />
        );

      case 'article_model':
        if (!articleModel) {
          return (
            <div className="loading-view">
              <button className="btn btn-primary" onClick={async () => {
                try {
                  const am = await api.getArticleModel(caseId);
                  setArticleModel(am);
                } catch { setActiveView('intake'); }
              }}>
                Load Article Model
              </button>
            </div>
          );
        }
        return (
          <ArticleCard
            article={articleModel}
            onConfirm={handleConfirmArticle}
            onEvidenceClick={handleEvidenceClick}
          />
        );

      case 'venue_investigation':
        if (!venueModel) {
          return (
            <div className="loading-view">
              <button className="btn btn-primary" onClick={async () => {
                try {
                  const result = await api.getInvestigatedVenue(caseId);
                  setVenueModel(result.venue);
                  setPubRegime(result.publication_regime);
                } catch { setActiveView('intake'); }
              }}>
                Load Venue Profile
              </button>
            </div>
          );
        }
        return (
          <VenueProfile
            venue={venueModel}
            regime={pubRegime}
            onEvidenceClick={handleEvidenceClick}
          />
        );

      case 'scenario':
        return (
          <ScenarioBuilder
            onSubmit={handleSetScenario}
            isLoading={isLoading}
            hasArticleModel={!!articleModel || !!caseData.article_model_id}
          />
        );

      case 'fit_assessed':
        if (!mismatchMap) {
          return (
            <div className="loading-view">
              <button className="btn btn-primary" onClick={loadMismatchMap}>
                Load Mismatch Map
              </button>
            </div>
          );
        }
        return <MismatchMapView mismatchMap={mismatchMap} />;

      case 'pathways':
        if (pathways.length === 0) {
          return (
            <div className="placeholder-view">
              <h2>Disciplinary Pathways</h2>
              <p>Possible academic worlds for your article.</p>
              <button className="btn btn-primary" onClick={loadPathways} disabled={isLoading}>
                {isLoading ? 'Mapping...' : 'Map Pathways'}
              </button>
            </div>
          );
        }
        return (
          <div className="pathways-view">
            <h2>Disciplinary Pathways</h2>
            <div className="pathway-cards">
              {pathways.map((p) => (
                <div key={p.disciplinary_pathway_id} className="pathway-card">
                  <h3>{p.discipline_name}</h3>
                  <div className="pathway-meta">
                    <span className={`fit-strength fit-${p.fit_strength}`}>
                      Fit: {p.fit_strength}
                    </span>
                    <span className={`core-risk core-${p.field_core_risk}`}>
                      Core: {p.field_core_risk}
                    </span>
                  </div>
                  {p.required_adaptations.length > 0 && (
                    <ul className="pathway-adaptations">
                      {p.required_adaptations.map((a, i) => (
                        <li key={i}>{a}</li>
                      ))}
                    </ul>
                  )}
                  {p.strategic_value_notes && (
                    <p className="pathway-notes">{p.strategic_value_notes}</p>
                  )}
                  {p.example_venue_names.length > 0 && (
                    <div className="pathway-venues">
                      <span className="pathway-venues-label">Venues: </span>
                      {p.example_venue_names.join(', ')}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        );

      default:
        return (
          <div className="placeholder-view">
            <h2>{activeView.replace(/_/g, ' ')}</h2>
            <p>This view will be implemented in upcoming phases.</p>
          </div>
        );
    }
  };

  return (
    <div className="case-workspace">
      <StatusBar
        currentStage={caseData.stage}
        objectsPresent={caseData.objects_present}
        onStageClick={handleStageClick}
      />

      {error && (
        <div className="error-banner" role="alert">
          <span>{error}</span>
          <button onClick={() => setError(null)} aria-label="Dismiss error">&times;</button>
        </div>
      )}

      {Object.keys(qualityGates).length > 0 && (
        <QualityGateBar gates={qualityGates} />
      )}

      <div className="workspace-body">
        <main className="workspace-center">
          {renderView()}
        </main>
        <EvidenceDrawer
          evidence={evidence}
          onClose={() => setEvidence(null)}
        />
      </div>
    </div>
  );
}
