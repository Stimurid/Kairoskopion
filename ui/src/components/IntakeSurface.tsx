import { useState } from 'react';

interface IntakeResult {
  input_type: string;
  text_length: number;
  article_model_built: boolean;
  venue_investigated?: boolean;
}

interface Props {
  onSubmit: (text: string, inputType: string) => Promise<IntakeResult | void>;
  isLoading: boolean;
}

const TYPE_LABELS: Record<string, string> = {
  auto: 'Auto-detect',
  article: 'Article / Abstract',
  venue: 'Journal / Venue',
  review_letter: 'Review Letter',
};

const TYPE_ICONS: Record<string, string> = {
  abstract: 'Abstract detected',
  manuscript: 'Manuscript detected',
  article: 'Article text detected',
  venue: 'Venue / journal text detected',
  review_letter: 'Review letter detected',
};

export function IntakeSurface({ onSubmit, isLoading }: Props) {
  const [text, setText] = useState('');
  const [inputType, setInputType] = useState('auto');
  const [lastResult, setLastResult] = useState<IntakeResult | null>(null);

  const handleSubmit = async () => {
    if (!text.trim()) return;
    setLastResult(null);
    const result = await onSubmit(text.trim(), inputType);
    if (result) setLastResult(result);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      handleSubmit();
    }
  };

  return (
    <div className="intake-surface">
      <h2 className="intake-title">What are you working on?</h2>
      <p className="intake-subtitle">
        Paste an abstract, manuscript text, journal name/URL, or review letter.
        The system will classify what you provide and build the right model.
      </p>

      <div className="intake-type-selector" role="radiogroup" aria-label="Input type">
        {(['auto', 'article', 'venue', 'review_letter'] as const).map((t) => (
          <button
            key={t}
            className={`type-chip ${inputType === t ? 'type-chip--active' : ''}`}
            onClick={() => setInputType(t)}
            role="radio"
            aria-checked={inputType === t}
          >
            {TYPE_LABELS[t]}
          </button>
        ))}
      </div>

      <textarea
        className="intake-textarea"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Paste your text here..."
        rows={12}
        disabled={isLoading}
        aria-label="Input text"
      />

      <div className="intake-actions">
        <span className="intake-hint">
          {text.length > 0 ? `${text.length} characters` : 'Ctrl+Enter to submit'}
        </span>
        <button
          className="btn btn-primary"
          onClick={handleSubmit}
          disabled={!text.trim() || isLoading}
        >
          {isLoading ? 'Analyzing...' : 'Analyze'}
        </button>
      </div>

      {lastResult && (
        <div className="intake-result" role="status">
          <span className="intake-result-type">
            {TYPE_ICONS[lastResult.input_type] || `Detected: ${lastResult.input_type}`}
          </span>
          <span className="intake-result-length">{lastResult.text_length} chars</span>
          {lastResult.article_model_built && (
            <span className="intake-result-badge intake-result-badge--success">
              Article model built
            </span>
          )}
          {lastResult.venue_investigated && (
            <span className="intake-result-badge intake-result-badge--success">
              Venue profile built
            </span>
          )}
        </div>
      )}
    </div>
  );
}
