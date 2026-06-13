import { useState } from 'react';

interface Props {
  onSubmit: (text: string, inputType: string) => void;
  isLoading: boolean;
}

export function IntakeSurface({ onSubmit, isLoading }: Props) {
  const [text, setText] = useState('');
  const [inputType, setInputType] = useState('auto');

  const handleSubmit = () => {
    if (!text.trim()) return;
    onSubmit(text.trim(), inputType);
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
            {t === 'auto' ? 'Auto-detect' :
             t === 'article' ? 'Article / Abstract' :
             t === 'venue' ? 'Journal / Venue' :
             'Review Letter'}
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
    </div>
  );
}
