import { useState } from 'react';

interface Props {
  onSubmit: (data: Record<string, unknown>) => void;
  isLoading: boolean;
  hasArticleModel: boolean;
  onBack?: () => void;
}

const PRIORITY_OPTIONS = ['low', 'medium', 'high'];
const REWRITE_DEPTH_OPTIONS = ['minimal', 'medium', 'deep', 'full'];
const RISK_TOLERANCE_OPTIONS = ['conservative', 'medium', 'aggressive'];
const INDEXING_OPTIONS = ['Scopus', 'Web of Science', 'DOAJ', 'PubMed', 'ERIH PLUS', 'RSCI'];

export function ScenarioBuilder({ onSubmit, isLoading, hasArticleModel, onBack }: Props) {
  const [goal, setGoal] = useState('');
  const [prestigePriority, setPrestigePriority] = useState('medium');
  const [speedPriority, setSpeedPriority] = useState('medium');
  const [apcMax, setApcMax] = useState('');
  const [deadline, setDeadline] = useState('');
  const [rewriteDepth, setRewriteDepth] = useState('medium');
  const [riskTolerance, setRiskTolerance] = useState('medium');
  const [targetIndexing, setTargetIndexing] = useState<string[]>([]);
  const [language, setLanguage] = useState('en');

  const handleIndexingToggle = (idx: string) => {
    setTargetIndexing(prev =>
      prev.includes(idx) ? prev.filter(i => i !== idx) : [...prev, idx]
    );
  };

  const handleSubmit = () => {
    onSubmit({
      goal,
      prestige_priority: prestigePriority,
      speed_priority: speedPriority,
      apc_max: apcMax ? parseFloat(apcMax) : null,
      deadline: deadline || null,
      rewrite_depth_allowed: rewriteDepth,
      risk_tolerance: riskTolerance,
      target_indexing: targetIndexing,
      language,
    });
  };

  if (!hasArticleModel) {
    return (
      <div className="placeholder-view">
        <h2>Scenario Builder</h2>
        <p>Confirm the article model first to set your publication scenario.</p>
      </div>
    );
  }

  return (
    <div className="scenario-builder">
      {onBack && <button className="btn btn-back" onClick={onBack}>← Back</button>}
      <h2>Publication Scenario</h2>
      <p className="scenario-subtitle">
        Define your publication goal and constraints. This shapes venue discovery and fit assessment.
      </p>

      <div className="scenario-form">
        <div className="form-group">
          <label className="form-label" htmlFor="sc-goal">Goal</label>
          <input
            id="sc-goal"
            className="form-input"
            type="text"
            value={goal}
            onChange={e => setGoal(e.target.value)}
            placeholder="e.g. Q1-Q2 Scopus publication in philosophy of technology"
          />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Prestige priority</label>
            <div className="chip-group">
              {PRIORITY_OPTIONS.map(p => (
                <button
                  key={p}
                  className={`type-chip ${prestigePriority === p ? 'type-chip--active' : ''}`}
                  onClick={() => setPrestigePriority(p)}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Speed priority</label>
            <div className="chip-group">
              {PRIORITY_OPTIONS.map(p => (
                <button
                  key={p}
                  className={`type-chip ${speedPriority === p ? 'type-chip--active' : ''}`}
                  onClick={() => setSpeedPriority(p)}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label className="form-label" htmlFor="sc-apc">Max APC (USD)</label>
            <input
              id="sc-apc"
              className="form-input form-input--narrow"
              type="number"
              value={apcMax}
              onChange={e => setApcMax(e.target.value)}
              placeholder="No limit"
              min="0"
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="sc-deadline">Deadline</label>
            <input
              id="sc-deadline"
              className="form-input form-input--narrow"
              type="date"
              value={deadline}
              onChange={e => setDeadline(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="sc-lang">Language</label>
            <select
              id="sc-lang"
              className="form-input form-input--narrow"
              value={language}
              onChange={e => setLanguage(e.target.value)}
            >
              <option value="en">English</option>
              <option value="ru">Russian</option>
              <option value="any">Any</option>
            </select>
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Rewrite depth allowed</label>
          <div className="chip-group">
            {REWRITE_DEPTH_OPTIONS.map(d => (
              <button
                key={d}
                className={`type-chip ${rewriteDepth === d ? 'type-chip--active' : ''}`}
                onClick={() => setRewriteDepth(d)}
              >
                {d}
              </button>
            ))}
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Risk tolerance</label>
          <div className="chip-group">
            {RISK_TOLERANCE_OPTIONS.map(r => (
              <button
                key={r}
                className={`type-chip ${riskTolerance === r ? 'type-chip--active' : ''}`}
                onClick={() => setRiskTolerance(r)}
              >
                {r}
              </button>
            ))}
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Target indexing</label>
          <div className="chip-group">
            {INDEXING_OPTIONS.map(idx => (
              <button
                key={idx}
                className={`type-chip ${targetIndexing.includes(idx) ? 'type-chip--active' : ''}`}
                onClick={() => handleIndexingToggle(idx)}
              >
                {idx}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="scenario-actions">
        <button
          className="btn btn-primary"
          onClick={handleSubmit}
          disabled={!goal.trim() || isLoading}
        >
          {isLoading ? 'Saving...' : 'Set Scenario'}
        </button>
      </div>
    </div>
  );
}
