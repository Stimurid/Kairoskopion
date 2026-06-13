import { useState, useEffect, useCallback } from 'react';
import type { CaseSummary, CaseDetail } from './types/domain';
import { api } from './api/client';
import { CaseWorkspace } from './components/CaseWorkspace';
import './styles/cockpit.css';

export default function App() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [activeCase, setActiveCase] = useState<CaseDetail | null>(null);
  const [isConnected, setIsConnected] = useState<boolean | null>(null);

  useEffect(() => {
    api.health()
      .then(() => setIsConnected(true))
      .catch(() => setIsConnected(false));
  }, []);

  const loadCases = useCallback(async () => {
    try {
      const list = await api.listCases();
      setCases(list);
    } catch { /* backend not running */ }
  }, []);

  useEffect(() => {
    if (isConnected) loadCases();
  }, [isConnected, loadCases]);

  const openCase = useCallback(async (caseId: string) => {
    try {
      const detail = await api.getCase(caseId);
      setActiveCase(detail);
    } catch (e) {
      console.error('Failed to open case:', e);
    }
  }, []);

  const createCase = useCallback(async () => {
    try {
      const summary = await api.createCase('New case');
      await loadCases();
      await openCase(summary.case_id);
    } catch (e) {
      console.error('Failed to create case:', e);
    }
  }, [loadCases, openCase]);

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

  if (isConnected === null) {
    return (
      <div className="app-shell">
        <div className="connecting">Connecting...</div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header className="top-bar">
        <h1 className="app-title">Kairoskopion</h1>
        <span className="app-subtitle">Publication Positioning Cockpit</span>
      </header>

      <div className="app-body">
        <nav className="case-sidebar" aria-label="Cases">
          <div className="sidebar-header">
            <h2>Cases</h2>
            <button className="btn btn-small" onClick={createCase}>+ New</button>
          </div>
          <ul className="case-list">
            {cases.map((c) => (
              <li key={c.case_id}>
                <button
                  className={`case-item ${activeCase?.case_id === c.case_id ? 'case-item--active' : ''}`}
                  onClick={() => openCase(c.case_id)}
                >
                  <span className="case-item-title">{c.title}</span>
                  <span className="case-item-stage">{c.stage}</span>
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
            caseData={activeCase}
            onCaseUpdate={refreshActiveCase}
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
      </div>
    </div>
  );
}
