import { useState, useCallback } from 'react';
import type {
  CaseDetail,
  ArticleModel,
  EvidenceDetail,
  DisciplinaryPathway,
  VenueModel,
  VenueCandidate,
  PublicationRegimeModel,
  MismatchMap,
  QualityGateResult,
  RewritePlan,
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
import { PathwayMap } from './PathwayMap';
import { VenuePoolBoard } from './VenuePoolBoard';
import { AdaptationStudio } from './AdaptationStudio';
import { DecisionLog } from './DecisionLog';
import { DossierView } from './DossierView';

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
  const [venueCandidates, setVenueCandidates] = useState<VenueCandidate[]>([]);
  const [venuePoolStatus, setVenuePoolStatus] = useState<string>('not_discovered');
  const [mismatchMap, setMismatchMap] = useState<MismatchMap | null>(null);
  const [qualityGates, setQualityGates] = useState<Record<string, QualityGateResult>>({});
  const [rewritePlan, setRewritePlan] = useState<RewritePlan | null>(null);
  const [protectedCore, setProtectedCore] = useState<string[]>([]);
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

  const handleIntakeResult = useCallback(async (result: { article_model_built: boolean; venue_investigated?: boolean }) => {
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
  }, [caseId, onCaseUpdate]);

  const handleIntakeSubmit = useCallback(async (text: string, inputType: string, searchDepth: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await api.intakeText(caseId, text, inputType, searchDepth);
      await handleIntakeResult(result);
      return result;
    } catch (e) {
      handleError(e);
    } finally {
      setIsLoading(false);
    }
  }, [caseId, handleIntakeResult]);

  const handleIntakeFile = useCallback(async (file: File, inputType: string, searchDepth: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await api.intakeFile(caseId, file, inputType);
      await handleIntakeResult(result);
      return result;
    } catch (e) {
      handleError(e);
    } finally {
      setIsLoading(false);
    }
  }, [caseId, handleIntakeResult]);

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

  // --- Venue pool ---

  const discoverVenues = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await api.discoverVenues(caseId);
      const candidates = (result.candidates ?? []) as VenueCandidate[];
      setVenueCandidates(candidates);
      setVenuePoolStatus(result.status ?? 'discovered');
      if (candidates.length > 0) {
        setActiveView('venue_pool');
      }
      onCaseUpdate();
    } catch (e) {
      handleError(e);
    } finally {
      setIsLoading(false);
    }
  }, [caseId, onCaseUpdate]);

  const loadVenuePool = useCallback(async () => {
    try {
      const result = await api.getVenuePool(caseId);
      const candidates = (result.candidates ?? []) as VenueCandidate[];
      setVenueCandidates(candidates);
      setVenuePoolStatus(result.status ?? 'not_discovered');
    } catch { /* not available */ }
  }, [caseId]);

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

  // --- Venue selection ---

  const handleSelectVenue = useCallback(async (venueId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await api.selectVenue(caseId, venueId);
      await loadMismatchMap();
      await loadQualityGates();
      if (result.rewrite_plan_available) {
        setActiveView('adapting');
      } else {
        setActiveView('fit_assessed');
      }
      onCaseUpdate();
    } catch (e) {
      handleError(e);
    } finally {
      setIsLoading(false);
    }
  }, [caseId, onCaseUpdate, loadMismatchMap, loadQualityGates]);

  // --- Adaptation ---

  const loadAdaptationPlan = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await api.getAdaptationPlan(caseId);
      if (result.rewrite_plan) {
        setRewritePlan(result.rewrite_plan as RewritePlan);
      }
      if (articleModel?.protected_core) {
        setProtectedCore(articleModel.protected_core);
      }
    } catch (e) {
      handleError(e);
    } finally {
      setIsLoading(false);
    }
  }, [caseId, articleModel]);

  const handleAdaptDecision = useCallback(async (changeId: string, action: string) => {
    setIsLoading(true);
    setError(null);
    try {
      await api.applyDecisions(caseId, [{ change_id: changeId, action }]);
      const result = await api.getAdaptationPlan(caseId);
      if (result.rewrite_plan) {
        setRewritePlan(result.rewrite_plan as RewritePlan);
      }
      onCaseUpdate();
    } catch (e) {
      handleError(e);
    } finally {
      setIsLoading(false);
    }
  }, [caseId, onCaseUpdate]);

  const handleApplyAll = useCallback(async () => {
    if (!rewritePlan) return;
    const accepted = rewritePlan.changes
      .filter(c => c.status === 'accepted')
      .map(c => ({ change_id: c.change_id, action: 'apply' }));
    if (accepted.length === 0) return;
    setIsLoading(true);
    setError(null);
    try {
      await api.applyDecisions(caseId, accepted);
      onCaseUpdate();
    } catch (e) {
      handleError(e);
    } finally {
      setIsLoading(false);
    }
  }, [caseId, rewritePlan, onCaseUpdate]);

  // --- Render view ---

  const renderView = () => {
    switch (activeView) {
      case 'empty':
      case 'intake':
        return (
          <IntakeSurface onSubmit={handleIntakeSubmit} onFileSubmit={handleIntakeFile} isLoading={isLoading} />
        );

      case 'article_model':
        if (!articleModel) {
          return (
            <div className="loading-view">
              <button className="btn btn-back" onClick={() => setActiveView('intake')}>← Back to Intake</button>
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
            onBack={() => setActiveView('intake')}
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
            onBack={() => setActiveView('article_model')}
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
              <button className="btn btn-back" onClick={() => setActiveView('scenario')}>← Back</button>
              <h2>Disciplinary Pathways</h2>
              <p>Possible academic worlds for your article.</p>
              <button className="btn btn-primary" onClick={loadPathways} disabled={isLoading}>
                {isLoading ? 'Mapping...' : 'Map Pathways'}
              </button>
            </div>
          );
        }
        return (
          <PathwayMap
            pathways={pathways}
            onSelectPathway={() => {
              discoverVenues();
            }}
          />
        );

      case 'venue_pool':
        if (venueCandidates.length === 0 && venuePoolStatus === 'not_discovered') {
          loadVenuePool();
        }
        return (
          <VenuePoolBoard
            candidates={venueCandidates}
            onSelectVenue={handleSelectVenue}
            onDiscover={discoverVenues}
            isLoading={isLoading}
            poolStatus={venuePoolStatus}
          />
        );

      case 'adapting':
        if (!rewritePlan) {
          return (
            <div className="placeholder-view">
              <h2>Adaptation Studio</h2>
              <p>Review and decide on proposed changes to your manuscript.</p>
              <button className="btn btn-primary" onClick={loadAdaptationPlan} disabled={isLoading}>
                {isLoading ? 'Loading...' : 'Load Adaptation Plan'}
              </button>
            </div>
          );
        }
        return (
          <AdaptationStudio
            rewritePlan={rewritePlan}
            protectedCore={protectedCore}
            onDecision={handleAdaptDecision}
            onApplyAll={handleApplyAll}
            isLoading={isLoading}
          />
        );

      case 'submission_pack':
        return (
          <div className="placeholder-view">
            <h2>Submission Pack</h2>
            <p>Final submission package assembly — coming in a future phase.</p>
            <DecisionLog caseId={caseId} />
          </div>
        );

      case 'dossier':
        return <DossierView caseId={caseId} />;

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

      <div className="preliminary-banner" role="note">
        <strong>Preliminary positioning</strong> — this is not a submission
        recommendation. Outputs are evidence-traceable hypotheses, not
        decisions. Unknowns are marked explicitly.
      </div>

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
