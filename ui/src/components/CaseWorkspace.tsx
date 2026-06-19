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
import { HumanModelView } from './HumanModelView';
import { DisciplineMatches } from './DisciplineMatches';
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
  onCaseGone?: () => void;
}

// Match ONLY the case-orchestrator 404, which always uses the literal
// "Case case_<hex> not found" shape produced by the FastAPI _user_case
// dependency. Tightened so it does NOT match other 404 messages such
// as "Article model not built yet" or "Scenario not set" — those
// should NOT trigger the activeCase reset.
const _CASE_GONE_RE = /Case\s+case_[a-f0-9]+\s+not\s+found/i;

function _isCaseGoneError(err: unknown): boolean {
  const msg = err instanceof Error ? err.message : String(err ?? '');
  return _CASE_GONE_RE.test(msg);
}

export function CaseWorkspace({ caseData, onCaseUpdate, onCaseGone }: Props) {
  const [activeView, setActiveView] = useState<string>(caseData.stage);
  const [evidence, setEvidence] = useState<EvidenceDetail | null>(null);
  const [articleModel, setArticleModel] = useState<ArticleModel | null>(null);
  // Human / Technical toggle for ArticleModel view. Human is default —
  // the Mavrinsky reviewer feedback that triggered this was that the raw
  // structured view was unreadable.
  const [articleViewMode, setArticleViewMode] = useState<'human' | 'technical'>('human');
  const [venueViewMode, setVenueViewMode] = useState<'human' | 'technical'>('human');
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
    // If the backend says this case no longer exists (e.g. server
    // storage was reset, case deleted in another tab), don't strand
    // the user on a dead workspace — clear active state and refresh
    // the case list.
    if (_isCaseGoneError(err)) {
      setError(
        'Этот case больше не существует на сервере. Возможно, бэкенд ' +
        'был перезапущен или case был удалён в другой вкладке. ' +
        'Создайте новый case или выберите существующий.',
      );
      if (onCaseGone) {
        onCaseGone();
      }
      return;
    }
    const raw = err instanceof Error ? err.message : String(err);
    // FastAPI structured detail (e.g. 413 input_too_large) — pull the
    // user-facing Russian message out of the JSON body instead of
    // showing the raw `API 413: {...}` blob.
    const m = raw.match(/^API \d+:\s*(\{.*\})$/);
    if (m) {
      try {
        const body = JSON.parse(m[1]);
        const detail = body?.detail ?? body;
        if (typeof detail === 'object' && detail?.message) {
          setError(detail.message);
          return;
        }
      } catch {
        /* fall through to raw */
      }
    }
    setError(raw);
  };

  // --- Intake ---

  const handleIntakeResult = useCallback(async (result: {
    article_model_built: boolean;
    venue_investigated?: boolean;
    needs_user_choice?: boolean;
    input_type?: string;
  }) => {
    // If the LLM classifier was uncertain (or returned unknown), stay
    // on intake — IntakeSurface renders the classifier verdict and
    // asks the user to pick a chip explicitly. Routing to a wrong
    // pipeline is worse than asking one extra question.
    if (result.needs_user_choice) {
      setActiveView('intake');
      onCaseUpdate();
      return;
    }
    if (result.article_model_built) {
      try {
        const am = await api.getArticleModel(caseId);
        setArticleModel(am);
      } catch (e) {
        // getArticleModel can 404 with "Article model not built yet"
        // if persistence raced. Swallow — the article-model view will
        // re-fetch via its own loader.
        console.warn('getArticleModel after intake failed:', e);
      }
      setActiveView('article_model');
    } else if (result.venue_investigated) {
      try {
        const venueResult = await api.getInvestigatedVenue(caseId);
        setVenueModel(venueResult.venue);
        setPubRegime(venueResult.publication_regime);
      } catch (e) {
        console.warn('getInvestigatedVenue after intake failed:', e);
      }
      setActiveView('venue_investigation');
    } else {
      // Classified as something we don't have a pipeline for yet
      // (review_letter), or LLM provider was down and classifier
      // returned unknown. Stay on intake so the user can re-route.
      setActiveView('intake');
    }
    onCaseUpdate();
  }, [caseId, onCaseUpdate]);

  const handleIntakeSubmit = useCallback(async (text: string, inputType: string, searchDepth: string, region: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await api.intakeText(caseId, text, inputType, searchDepth, region);
      await handleIntakeResult(result);
      return result;
    } catch (e) {
      handleError(e);
    } finally {
      setIsLoading(false);
    }
  }, [caseId, handleIntakeResult]);

  const handleIntakeFile = useCallback(async (file: File, inputType: string, searchDepth: string, region: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await api.intakeFile(caseId, file, inputType, region);
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
          <>
            <div className="model-view-toggle" role="tablist" aria-label="Article view mode">
              <button
                type="button"
                role="tab"
                aria-selected={articleViewMode === 'human'}
                className={`model-view-toggle-btn ${articleViewMode === 'human' ? 'model-view-toggle-btn--active' : ''}`}
                onClick={() => setArticleViewMode('human')}
              >
                Человеческая модель
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={articleViewMode === 'technical'}
                className={`model-view-toggle-btn ${articleViewMode === 'technical' ? 'model-view-toggle-btn--active' : ''}`}
                onClick={() => setArticleViewMode('technical')}
              >
                Техническая модель
              </button>
            </div>
            {articleViewMode === 'human' ? (
              <HumanModelView
                caseId={caseId}
                kind="article"
                onBack={() => setActiveView('intake')}
                onConfirm={() => handleConfirmArticle(articleModel.protected_core || [], {})}
              />
            ) : (
              <ArticleCard
                article={articleModel}
                onConfirm={handleConfirmArticle}
                onEvidenceClick={handleEvidenceClick}
                onBack={() => setActiveView('intake')}
              />
            )}
            <DisciplineMatches caseId={caseId} />
          </>
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
          <>
            <div className="model-view-toggle" role="tablist" aria-label="Venue view mode">
              <button
                type="button"
                role="tab"
                aria-selected={venueViewMode === 'human'}
                className={`model-view-toggle-btn ${venueViewMode === 'human' ? 'model-view-toggle-btn--active' : ''}`}
                onClick={() => setVenueViewMode('human')}
              >
                Человеческая модель
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={venueViewMode === 'technical'}
                className={`model-view-toggle-btn ${venueViewMode === 'technical' ? 'model-view-toggle-btn--active' : ''}`}
                onClick={() => setVenueViewMode('technical')}
              >
                Техническая модель
              </button>
            </div>
            {venueViewMode === 'human' ? (
              <HumanModelView
                caseId={caseId}
                kind="venue"
                venueKey="investigated"
              />
            ) : (
              <VenueProfile
                venue={venueModel}
                regime={pubRegime}
                onEvidenceClick={handleEvidenceClick}
              />
            )}
          </>
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
