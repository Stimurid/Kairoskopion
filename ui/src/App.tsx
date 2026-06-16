import { useState, useEffect, useCallback } from 'react';
import type { CaseSummary, CaseDetail } from './types/domain';
import { api, getToken, clearToken, type AuthUser } from './api/client';
import { CaseWorkspace } from './components/CaseWorkspace';
import { AgentMap } from './components/AgentMap';
import { AuthGate } from './components/AuthGate';
import './styles/cockpit.css';

type AppView = 'cases' | 'agents';

export default function App() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [activeCase, setActiveCase] = useState<CaseDetail | null>(null);
  const [isConnected, setIsConnected] = useState<boolean | null>(null);
  const [appView, setAppView] = useState<AppView>('cases');
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  // Transient top-level notice for stale-case recoveries — surfaces a
  // Russian message after handleCaseGone fires so the user knows the
  // workspace reset wasn't random.
  const [globalNotice, setGlobalNotice] = useState<string | null>(null);

  useEffect(() => {
    api.health()
      .then(() => setIsConnected(true))
      .catch(() => setIsConnected(false));
  }, []);

  // Resolve current user from token on boot
  useEffect(() => {
    if (!isConnected) return;
    const tok = getToken();
    if (!tok) {
      setAuthChecked(true);
      return;
    }
    api.me()
      .then(r => setUser(r.user))
      .catch(() => { clearToken(); setUser(null); })
      .finally(() => setAuthChecked(true));
  }, [isConnected]);

  const loadCases = useCallback(async () => {
    try {
      const list = await api.listCases();
      setCases(list);
    } catch { /* backend not running or unauthenticated */ }
  }, []);

  useEffect(() => {
    if (isConnected && user) loadCases();
  }, [isConnected, user, loadCases]);

  const handleAuthenticated = useCallback((u: AuthUser) => {
    setUser(u);
  }, []);

  const handleLogout = useCallback(async () => {
    try { await api.logout(); } catch { /* ignore */ }
    clearToken();
    setUser(null);
    setActiveCase(null);
    setCases([]);
  }, []);

  const openCase = useCallback(async (caseId: string) => {
    try {
      const detail = await api.getCase(caseId);
      setActiveCase(detail);
    } catch (e) {
      console.error('Failed to open case:', e);
      // Drop stale active only when the backend specifically says
      // the case doesn't exist (literal "Case case_<id> not found"
      // from the FastAPI _user_case dep). Other 404s like
      // "Article model not built yet" must NOT clear activeCase.
      const msg = e instanceof Error ? e.message : String(e);
      if (/Case\s+case_[a-f0-9]+\s+not\s+found/i.test(msg)) {
        setActiveCase(null);
        loadCases();
      }
    }
  }, [loadCases]);

  const handleCaseGone = useCallback(() => {
    // Triggered when a case-scoped API call inside a CaseWorkspace
    // returns 404 (case deleted, server reset, etc.). Drop active +
    // re-sync the list, and explain what happened at the App level
    // since the CaseWorkspace (and its error banner) will unmount.
    setActiveCase(null);
    loadCases();
    setGlobalNotice(
      'Этот case больше не существует на сервере. Возможно, бэкенд ' +
      'был перезапущен или case был удалён в другой вкладке. Создайте ' +
      'новый case или выберите существующий.',
    );
  }, [loadCases]);

  const createCase = useCallback(async () => {
    try {
      const summary = await api.createCase('New case');
      await loadCases();
      await openCase(summary.case_id);
    } catch (e) {
      console.error('Failed to create case:', e);
    }
  }, [loadCases, openCase]);

  const deleteCase = useCallback(async (caseId: string) => {
    try {
      await api.deleteCase(caseId);
      if (activeCase?.case_id === caseId) setActiveCase(null);
      await loadCases();
    } catch (e) {
      console.error('Failed to delete case:', e);
    }
  }, [activeCase, loadCases]);

  const refreshActiveCase = useCallback(async () => {
    if (activeCase) {
      await openCase(activeCase.case_id);
      await loadCases();
    }
  }, [activeCase, openCase, loadCases]);

  if (isConnected === false) {
    return (
      <div className="app-shell">
        <div className="connection-error">
          <h1>Kairoskopion</h1>
          <p>Cannot connect to backend.</p>
          <p className="connection-hint">
            Start the API server:<br />
            <code>uvicorn kairoskopion.api.app:app --reload</code>
          </p>
          <button className="btn btn-primary" onClick={() => {
            setIsConnected(null);
            api.health()
              .then(() => setIsConnected(true))
              .catch(() => setIsConnected(false));
          }}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (isConnected === null || !authChecked) {
    return (
      <div className="app-shell">
        <div className="connecting">Connecting...</div>
      </div>
    );
  }

  // Soft-auth gate: must have a current user (token + /auth/me ok)
  if (!user) {
    return <AuthGate onAuthenticated={handleAuthenticated} />;
  }

  return (
    <div className="app-shell">
      <header className="top-bar">
        <h1 className="app-title">Kairoskopion</h1>
        <span className="app-subtitle">Publication Positioning Cockpit</span>
        <nav className="top-bar-nav">
          <button
            className={`top-bar-link ${appView === 'cases' ? 'top-bar-link--active' : ''}`}
            onClick={() => setAppView('cases')}
          >
            Cases
          </button>
          <button
            className={`top-bar-link ${appView === 'agents' ? 'top-bar-link--active' : ''}`}
            onClick={() => setAppView('agents')}
          >
            System / Agents
          </button>
        </nav>
        <div className="top-bar-user">
          <span
            className="top-bar-user-name"
            title={user.email ?? 'no email — workspace tied to this device only'}
          >
            {user.display_name}
          </span>
          <button
            className="top-bar-logout"
            onClick={handleLogout}
            title="Sign out"
          >
            Sign out
          </button>
        </div>
      </header>

      {globalNotice && (
        <div className="global-notice" role="status">
          <span>{globalNotice}</span>
          <button
            type="button"
            className="global-notice-dismiss"
            onClick={() => setGlobalNotice(null)}
            aria-label="Dismiss"
          >&times;</button>
        </div>
      )}

      <div className="app-body">
        {appView === 'agents' ? (
          <AgentMap />
        ) : (
          <>
            <nav className="case-sidebar" aria-label="Cases">
              <div className="sidebar-header">
                <h2>Cases</h2>
                <button className="btn btn-small" onClick={createCase}>+ New</button>
              </div>
              <ul className="case-list">
                {cases.map((c) => (
                  <li key={c.case_id} className="case-list-item">
                    <button
                      className={`case-item ${activeCase?.case_id === c.case_id ? 'case-item--active' : ''}`}
                      onClick={() => openCase(c.case_id)}
                    >
                      <span className="case-item-title">{c.title}</span>
                      <span className="case-item-stage">{c.stage}</span>
                    </button>
                    <button
                      className="case-item-delete"
                      onClick={(e) => { e.stopPropagation(); deleteCase(c.case_id); }}
                      aria-label={`Delete ${c.title}`}
                      title="Delete case"
                    >
                      ✕
                    </button>
                  </li>
                ))}
                {cases.length === 0 && (
                  <li className="case-list-empty">No cases yet</li>
                )}
              </ul>
            </nav>

            {activeCase ? (
              <CaseWorkspace
                key={activeCase.case_id}
                caseData={activeCase}
                onCaseUpdate={refreshActiveCase}
                onCaseGone={handleCaseGone}
              />
            ) : (
              <div className="workspace-empty">
                <h2>Publication Positioning Cockpit</h2>
                <p>Create a new case or select an existing one to begin.</p>
                <button className="btn btn-primary btn-large" onClick={createCase}>
                  + New Case
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
