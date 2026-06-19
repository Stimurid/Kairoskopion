import { useRef, useState } from 'react';

interface TruncationInfo {
  original_chars: number;
  used_chars: number;
  cap: number;
  truncated: boolean;
}

interface ClassificationVerdict {
  input_type: string;
  confidence: 'high' | 'medium' | 'low';
  needs_user_choice: boolean;
  language_detected: 'ru' | 'en' | 'mixed' | 'unknown';
  reasoning: string;
}

interface IntakeResult {
  input_type: string;
  text_length: number;
  article_model_built: boolean;
  venue_investigated?: boolean;
  filename?: string;
  extraction_status?: string;
  input_truncated_for_llm?: TruncationInfo;
  classification?: ClassificationVerdict;
  needs_user_choice?: boolean;
}

// Keep in sync with src/kairoskopion/llm/input_limits.py
const LLM_SOFT_CAP = 150_000;
const INTAKE_HARD_CAP = 400_000;

interface Props {
  onSubmit: (text: string, inputType: string, searchDepth: string, region: string) => Promise<IntakeResult | void>;
  onFileSubmit?: (file: File, inputType: string, searchDepth: string, region: string) => Promise<IntakeResult | void>;
  isLoading: boolean;
}

const ACCEPTED_EXTENSIONS = '.pdf,.docx,.doc,.txt,.md,.html,.htm,.rtf,.json';
// .doc (old Word 97-2003) is accepted at upload time but rejected at
// extraction with a clear Russian message asking the user to save as .docx.
const FORMAT_LABEL = 'PDF, DOCX, TXT, MD, HTML, RTF';

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

const SEARCH_DEPTH_LABELS: Record<string, { label: string; desc: string }> = {
  none: { label: 'No search', desc: 'LLM only, no web queries' },
  light: { label: 'Light search', desc: '3-5 queries for top unknowns' },
  deep: { label: 'Deep search', desc: 'Multiple rounds, verification' },
};

const REGION_LABELS: Record<string, { label: string; desc: string }> = {
  auto: {
    label: 'Auto',
    desc: 'Определить по языку текста',
  },
  ru: {
    label: 'RU',
    desc: 'Российская академическая зона — ВАК, ИФРАН, СМД, русскоязычные дисциплины',
  },
  international: {
    label: 'International',
    desc: 'OECD FORD, ERC, ISCED-F — англоязычная международная зона',
  },
};

export function IntakeSurface({ onSubmit, onFileSubmit, isLoading }: Props) {
  const [text, setText] = useState('');
  const [inputType, setInputType] = useState('auto');
  const [searchDepth, setSearchDepth] = useState('none');
  const [region, setRegion] = useState('auto');
  const [lastResult, setLastResult] = useState<IntakeResult | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = async () => {
    if (selectedFile && onFileSubmit) {
      setLastResult(null);
      const result = await onFileSubmit(selectedFile, inputType, searchDepth, region);
      if (result) setLastResult(result);
      setSelectedFile(null);
      return;
    }
    if (!text.trim()) return;
    setLastResult(null);
    const result = await onSubmit(text.trim(), inputType, searchDepth, region);
    if (result) setLastResult(result);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      handleSubmit();
    }
  };

  const handleFileSelect = (file: File | undefined) => {
    if (!file) return;
    setSelectedFile(file);
    setText('');
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    handleFileSelect(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  return (
    <div className="intake-surface">
      <h2 className="intake-title">What are you working on?</h2>
      <p className="intake-subtitle">
        Paste text or upload a file ({FORMAT_LABEL}).
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

      <div className="intake-search-depth" role="radiogroup" aria-label="Web search depth">
        <span className="intake-search-label">Web enrichment:</span>
        {(['none', 'light', 'deep'] as const).map((d) => (
          <button
            key={d}
            className={`search-chip ${searchDepth === d ? 'search-chip--active' : ''} ${d === 'deep' ? 'search-chip--deep' : ''}`}
            onClick={() => setSearchDepth(d)}
            role="radio"
            aria-checked={searchDepth === d}
            title={SEARCH_DEPTH_LABELS[d].desc}
          >
            {SEARCH_DEPTH_LABELS[d].label}
          </button>
        ))}
      </div>

      <div className="intake-region-selector" role="radiogroup" aria-label="Регион академической работы">
        <span className="intake-search-label">Регион:</span>
        {(['auto', 'ru', 'international'] as const).map((r) => (
          <button
            key={r}
            className={`search-chip ${region === r ? 'search-chip--active' : ''}`}
            onClick={() => setRegion(r)}
            role="radio"
            aria-checked={region === r}
            title={REGION_LABELS[r].desc}
          >
            {REGION_LABELS[r].label}
          </button>
        ))}
      </div>

      {selectedFile ? (
        <div className="intake-file-preview">
          <span className="intake-file-icon">📄</span>
          <span className="intake-file-name">{selectedFile.name}</span>
          <span className="intake-file-size">
            {(selectedFile.size / 1024).toFixed(0)} KB
          </span>
          <button
            className="intake-file-remove"
            onClick={() => setSelectedFile(null)}
            aria-label="Remove file"
          >
            ✕
          </button>
        </div>
      ) : (
        <div
          className={`intake-input-area ${dragOver ? 'intake-input-area--dragover' : ''}`}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={() => setDragOver(false)}
        >
          <textarea
            className="intake-textarea"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Paste your text here..."
            rows={10}
            disabled={isLoading}
            aria-label="Input text"
          />
          <div className="intake-file-upload-row">
            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_EXTENSIONS}
              className="intake-file-input-hidden"
              onChange={(e) => handleFileSelect(e.target.files?.[0])}
            />
            <button
              className="btn btn-secondary intake-upload-btn"
              onClick={() => fileInputRef.current?.click()}
              disabled={isLoading}
              type="button"
            >
              Upload file
            </button>
            <span className="intake-file-formats">
              or drag & drop — {FORMAT_LABEL}
            </span>
          </div>
        </div>
      )}

      <div className="intake-actions">
        <span
          className={`intake-hint ${
            text.length > INTAKE_HARD_CAP
              ? 'intake-hint--block'
              : text.length > LLM_SOFT_CAP
                ? 'intake-hint--warn'
                : ''
          }`}
        >
          {selectedFile
            ? selectedFile.name
            : text.length === 0
              ? 'Ctrl+Enter to submit'
              : text.length > INTAKE_HARD_CAP
                ? `${text.length.toLocaleString('ru-RU')} символов — превышает максимум ${INTAKE_HARD_CAP.toLocaleString('ru-RU')}. Сократите вход.`
                : text.length > LLM_SOFT_CAP
                  ? `${text.length.toLocaleString('ru-RU')} символов — LLM получит только первые ${LLM_SOFT_CAP.toLocaleString('ru-RU')}; остальное в анализ не пойдёт. Сократите вход или разбейте на части.`
                  : `${text.length} characters`}
        </span>
        <button
          className="btn btn-primary"
          onClick={handleSubmit}
          disabled={
            (!text.trim() && !selectedFile) ||
            isLoading ||
            text.length > INTAKE_HARD_CAP
          }
        >
          {isLoading ? 'Analyzing...' : 'Analyze'}
        </button>
      </div>

      {lastResult?.needs_user_choice && lastResult.classification && (
        <div className="intake-classification-banner" role="alert">
          <div className="intake-classification-headline">
            <strong>⚠ Не уверен в типе текста.</strong>{' '}
            Классификатор предположил:{' '}
            <code>{lastResult.classification.input_type}</code>{' '}
            (уверенность: {lastResult.classification.confidence}).
          </div>
          <div className="intake-classification-reasoning">
            {lastResult.classification.reasoning}
          </div>
          <div className="intake-classification-action">
            Выберите тип вручную чипом выше и нажмите Analyze ещё раз.
          </div>
        </div>
      )}

      {lastResult && (
        <div className="intake-result" role="status">
          <span className="intake-result-type">
            {TYPE_ICONS[lastResult.input_type] || `Detected: ${lastResult.input_type}`}
          </span>
          <span className="intake-result-length">{lastResult.text_length} chars</span>
          {lastResult.filename && (
            <span className="intake-result-badge">
              {lastResult.filename}
            </span>
          )}
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
          {lastResult.input_truncated_for_llm?.truncated && (
            <span
              className="intake-result-badge intake-result-badge--warn"
              title={`LLM получил первые ${lastResult.input_truncated_for_llm.used_chars.toLocaleString('ru-RU')} из ${lastResult.input_truncated_for_llm.original_chars.toLocaleString('ru-RU')} символов`}
            >
              LLM: обрезано до{' '}
              {lastResult.input_truncated_for_llm.used_chars.toLocaleString('ru-RU')} симв.
            </span>
          )}
        </div>
      )}
    </div>
  );
}
