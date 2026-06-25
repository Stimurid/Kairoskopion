import { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import { api, getToken } from '../api/client';

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000';

type Kind = 'article' | 'venue';

type BlockDecision = 'accepted' | 'rejected' | null;

interface ParsedBlock {
  id: string;
  fieldPath: string | null;
  allFieldPaths: string[];
  rawMarkdown: string;
  html: string;
}

// ---- Enum typology options (Russian descriptions from PROSE dictionaries) ----

interface TypologyOption {
  value: string;
  label: string;
}

const GENRE_OPTIONS: TypologyOption[] = [
  { value: 'research_article', label: 'Исследовательская статья — сообщает результат конкретного исследования' },
  { value: 'conceptual_article', label: 'Концептуальная статья — вводит или переосмысляет понятие' },
  { value: 'theoretical_essay', label: 'Теоретическое эссе — строит понятие, различение или модель' },
  { value: 'review', label: 'Обзорная статья — синтез существующей литературы по теме' },
  { value: 'systematic_review', label: 'Систематический обзор — структурированный сбор по протоколу' },
  { value: 'position_paper', label: 'Позиционная статья — заявление позиции автора' },
  { value: 'commentary', label: 'Комментарий — реплика на чужую работу' },
  { value: 'conference_paper', label: 'Конференционный доклад' },
  { value: 'forum_piece', label: 'Форумная публикация — вклад в дискуссионную рубрику' },
  { value: 'book_symposium_piece', label: 'Симпозиум по книге' },
  { value: 'unknown', label: 'Жанр не определён' },
];

const METHOD_OPTIONS: TypologyOption[] = [
  { value: 'no_method', label: 'Методом в эмпирическом смысле не пользуется' },
  { value: 'implicit_method', label: 'Метод не назван явно' },
  { value: 'conceptual_method', label: 'Использует концептуальный метод' },
  { value: 'empirical_method', label: 'Использует эмпирический метод' },
  { value: 'case_based', label: 'Работает через разбор случаев' },
  { value: 'review_method', label: 'Обзорный метод' },
  { value: 'mixed', label: 'Смешанные методы' },
  { value: 'unknown', label: 'Метод не определён' },
];

const NOVELTY_OPTIONS: TypologyOption[] = [
  { value: 'new_object', label: 'Вводит новый объект исследования' },
  { value: 'new_theory', label: 'Формулирует новую теорию или модель' },
  { value: 'new_method', label: 'Предлагает новый метод' },
  { value: 'new_application', label: 'Применяет существующий подход к новому материалу' },
  { value: 'new_synthesis', label: 'Синтезирует существующие позиции' },
  { value: 'critique', label: 'Критикует существующее положение' },
  { value: 'translation_between_fields', label: 'Переводит понятие из одной области в другую' },
  { value: 'case_contribution', label: 'Вносит вклад через разбор нового случая' },
  { value: 'empirical_finding', label: 'Представляет новое эмпирическое свидетельство' },
  { value: 'unknown', label: 'Характер новизны не определён' },
];

const FIELD_TYPOLOGY_MAP: Record<string, TypologyOption[]> = {
  'article_model.genre_current': GENRE_OPTIONS,
  'article_model.method_status': METHOD_OPTIONS,
  'article_model.novelty_mode': NOVELTY_OPTIONS,
};

interface BlockTypology {
  fieldPath: string;
  label: string;
  options: TypologyOption[];
}

const FIELD_TYPOLOGY_LABELS: Record<string, string> = {
  'article_model.genre_current': 'Жанр',
  'article_model.method_status': 'Способ работы',
  'article_model.novelty_mode': 'Новизна',
};

function getTypologiesForBlock(block: ParsedBlock): BlockTypology[] {
  const result: BlockTypology[] = [];
  for (const fp of block.allFieldPaths) {
    if (FIELD_TYPOLOGY_MAP[fp]) {
      result.push({
        fieldPath: fp,
        label: FIELD_TYPOLOGY_LABELS[fp] || fp,
        options: FIELD_TYPOLOGY_MAP[fp],
      });
    }
  }
  return result;
}

interface TextEvidence {
  fieldPath: string;
  selectedText: string;
  charOffset?: number;
}

interface Props {
  caseId: string;
  kind: Kind;
  venueKey?: string;
  onConfirm?: (
    decisions: Record<string, BlockDecision>,
    overrides: Record<string, string>,
    comments: Record<string, string>,
    textEvidence: TextEvidence[],
  ) => void;
  onBack?: () => void;
}

interface HumanViewResponse {
  format: string;
  case_id: string;
  lifecycle_status?: string;
  not_a_submission_recommendation: boolean;
  markdown: string;
}

// Extract field paths from HTML comments: <!-- field: article_model.X -->
const FIELD_RE = /<!--\s*field:\s*([\w.]+)\s*-->/g;

function extractFieldPaths(md: string): string[] {
  const paths: string[] = [];
  let m: RegExpExecArray | null;
  const re = new RegExp(FIELD_RE.source, 'g');
  while ((m = re.exec(md)) !== null) {
    if (!paths.includes(m[1])) paths.push(m[1]);
  }
  return paths;
}

// Split markdown into blocks by H2 headings. Each block is a section
// that starts with `## Title` and runs until the next `## ` or EOF.
function splitIntoBlocks(md: string): ParsedBlock[] {
  const lines = md.split('\n');
  const blocks: ParsedBlock[] = [];
  let currentLines: string[] = [];
  let blockIndex = 0;

  const flushBlock = () => {
    const raw = currentLines.join('\n').trim();
    if (!raw) return;
    const fields = extractFieldPaths(raw);
    const primaryField = fields.length > 0 ? fields[0] : null;
    blocks.push({
      id: `block_${blockIndex}`,
      fieldPath: primaryField,
      allFieldPaths: fields,
      rawMarkdown: raw,
      html: renderMarkdown(raw),
    });
    blockIndex++;
  };

  for (const line of lines) {
    if (/^## /.test(line) && currentLines.length > 0) {
      flushBlock();
      currentLines = [line];
    } else {
      currentLines.push(line);
    }
  }
  flushBlock();
  return blocks;
}

// Minimal, dependency-free markdown renderer — handles H1/H2/H3, bold,
// italic, blockquote, bullet lists, paragraphs, HTML comments.
function renderMarkdown(md: string): string {
  // Strip <!-- ... --> machine field anchors
  let s = md.replace(/<!--[\s\S]*?-->/g, '');

  // Escape HTML entities
  s = s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Blockquotes
  s = s.replace(/^\s*&gt;\s*(.+)$/gm, '<blockquote>$1</blockquote>');

  // Headings
  s = s.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  s = s.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  s = s.replace(/^# (.+)$/gm, '<h1>$1</h1>');

  // Bold / italics
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>');
  s = s.replace(/_([^_\n]+)_/g, '<em>$1</em>');

  // Bullet lists
  const lines = s.split('\n');
  const out: string[] = [];
  let inList = false;
  for (const line of lines) {
    const m = line.match(/^\s*[-*]\s+(.+)$/);
    if (m) {
      if (!inList) {
        out.push('<ul>');
        inList = true;
      }
      out.push(`<li>${m[1]}</li>`);
    } else {
      if (inList) {
        out.push('</ul>');
        inList = false;
      }
      out.push(line);
    }
  }
  if (inList) out.push('</ul>');
  s = out.join('\n');

  // Paragraphs
  const blocks = s.split(/\n{2,}/);
  return blocks
    .map(b => {
      const t = b.trim();
      if (!t) return '';
      if (/^<(h1|h2|h3|h4|ul|ol|blockquote|pre|hr|div|p)\b/i.test(t)) {
        return t;
      }
      if (/^---\n[\s\S]*?\n---\s*$/m.test(t)) {
        return '';
      }
      return `<p>${t.replace(/\n/g, '<br/>')}</p>`;
    })
    .filter(Boolean)
    .join('\n');
}

// Blocks that are structural (intro summary, questions, corrections
// guide) — not individual model fields the user needs to judge.
const NON_FIELD_BLOCK_PREFIXES = [
  'block_0', // Usually the top-level summary before any H2
];

function isReviewableBlock(block: ParsedBlock): boolean {
  // Must have a field path to be reviewable
  if (!block.fieldPath) return false;
  // Skip the corrections guide section — it's meta, not a field
  if (block.rawMarkdown.includes('Что можно поправить')) return false;
  if (block.rawMarkdown.includes('Вопросы автору')) return false;
  return true;
}

export function HumanModelView({ caseId, kind, venueKey, onConfirm, onBack }: Props) {
  const [markdown, setMarkdown] = useState<string | null>(null);
  const [lifecycle, setLifecycle] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [decisions, setDecisions] = useState<Record<string, BlockDecision>>({});
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [comments, setComments] = useState<Record<string, string>>({});
  const [expandedPickers, setExpandedPickers] = useState<Record<string, boolean>>({});
  // M-6: TextEvidence state
  const [sourceText, setSourceText] = useState<string | null>(null);
  const [sourceOpen, setSourceOpen] = useState(false);
  const [textEvidence, setTextEvidence] = useState<TextEvidence[]>([]);
  const [pendingSelection, setPendingSelection] = useState<string | null>(null);
  const [bindTarget, setBindTarget] = useState<string | null>(null);
  const sourceRef = useRef<HTMLDivElement>(null);
  // M-9: correction signals
  const [signals, setSignals] = useState<{ type: string; field?: string; severity: string; message: string }[]>([]);
  const [signalsOpen, setSignalsOpen] = useState(false);

  useEffect(() => {
    if (kind !== 'article') return;
    api.getCorrectionSignals().then(r => {
      if (r.signals && r.signals.length > 0) setSignals(r.signals);
    }).catch(() => {});
  }, [kind]);

  // M-8: LLM refinement dialog
  interface ChatEntry {
    role: string;
    content: string;
    suggestions?: { field: string; value: string; reason: string }[];
  }
  const [chatOpen, setChatOpen] = useState(false);
  const [chatHistory, setChatHistory] = useState<ChatEntry[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatSending, setChatSending] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    setMarkdown(null);
    setDecisions({});
    setOverrides({});
    setComments({});
    setExpandedPickers({});
    const tok = getToken();
    const path =
      kind === 'article'
        ? `/cases/${caseId}/article-model/human-view`
        : `/cases/${caseId}/venues/${encodeURIComponent(venueKey ?? '')}/human-view`;
    fetch(`${BASE}${path}`, {
      headers: tok ? { Authorization: `Bearer ${tok}` } : undefined,
    })
      .then(async (r) => {
        if (!r.ok) {
          const body = await r.text();
          throw new Error(`API ${r.status}: ${body}`);
        }
        return (await r.json()) as HumanViewResponse;
      })
      .then((d) => {
        if (!active) return;
        setMarkdown(d.markdown);
        setLifecycle(d.lifecycle_status ?? null);
      })
      .catch((e) => {
        if (!active) return;
        setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [caseId, kind, venueKey]);

  // M-6: fetch source text when panel is opened
  useEffect(() => {
    if (!sourceOpen || sourceText !== null) return;
    const tok = getToken();
    fetch(`${BASE}/cases/${caseId}/source-text`, {
      headers: tok ? { Authorization: `Bearer ${tok}` } : undefined,
    })
      .then(async (r) => {
        if (!r.ok) return;
        const d = await r.json();
        setSourceText(d.text ?? '');
      })
      .catch(() => {});
  }, [sourceOpen, sourceText, caseId]);

  // M-6: text selection handler on the source panel
  useEffect(() => {
    if (!sourceOpen) return;
    const handler = () => {
      const sel = window.getSelection();
      const text = sel?.toString().trim() ?? '';
      if (text.length >= 5 && sourceRef.current?.contains(sel?.anchorNode ?? null)) {
        setPendingSelection(text);
      } else {
        setPendingSelection(null);
      }
    };
    document.addEventListener('mouseup', handler);
    return () => document.removeEventListener('mouseup', handler);
  }, [sourceOpen]);

  const handleBindEvidence = useCallback((fieldPath: string) => {
    if (!pendingSelection) return;
    const offset = sourceText ? sourceText.indexOf(pendingSelection) : undefined;
    setTextEvidence(prev => [
      ...prev.filter(e => !(e.fieldPath === fieldPath && e.selectedText === pendingSelection)),
      { fieldPath, selectedText: pendingSelection, charOffset: offset !== undefined && offset >= 0 ? offset : undefined },
    ]);
    setPendingSelection(null);
    setBindTarget(null);
    window.getSelection()?.removeAllRanges();
  }, [pendingSelection, sourceText]);

  const removeEvidence = useCallback((fieldPath: string, idx: number) => {
    setTextEvidence(prev => prev.filter((e, i) => !(e.fieldPath === fieldPath && i === idx)));
  }, []);

  // M-8: send refinement message
  const sendRefinement = useCallback(async () => {
    const msg = chatInput.trim();
    if (!msg || chatSending) return;
    setChatInput('');
    setChatSending(true);
    setChatError(null);
    setChatHistory(prev => [...prev, { role: 'user', content: msg }]);
    try {
      const result = await api.refineArticleModel(caseId, msg);
      setChatHistory(prev => [
        ...prev,
        {
          role: 'assistant',
          content: result.reply,
          suggestions: result.suggestions,
        },
      ]);
    } catch (e) {
      setChatError(e instanceof Error ? e.message : String(e));
    } finally {
      setChatSending(false);
    }
  }, [caseId, chatInput, chatSending]);

  // M-8: apply a suggestion from the chat
  const applySuggestion = useCallback((field: string, value: string) => {
    setOverrides(prev => ({ ...prev, [`article_model.${field}`]: value }));
  }, []);

  // M-8: auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  const blocks = useMemo(() => {
    if (!markdown) return [];
    return splitIntoBlocks(markdown);
  }, [markdown]);

  const reviewableBlocks = useMemo(() => {
    return blocks.filter(isReviewableBlock);
  }, [blocks]);

  // M-6: all field paths for bind target picker
  const allFieldPaths = useMemo(() => {
    const paths: string[] = [];
    for (const b of reviewableBlocks) {
      for (const fp of b.allFieldPaths) {
        if (!paths.includes(fp)) paths.push(fp);
      }
    }
    return paths;
  }, [reviewableBlocks]);

  const isConfirmed = lifecycle === 'confirmed' || lifecycle === 'confirmed_by_user';
  const showPerBlock = kind === 'article' && !isConfirmed && reviewableBlocks.length > 0;

  const handleDecision = useCallback((blockId: string, decision: BlockDecision) => {
    setDecisions(prev => ({ ...prev, [blockId]: decision }));
  }, []);

  const allDecided = showPerBlock && reviewableBlocks.every(b => decisions[b.id] != null);
  const decidedCount = reviewableBlocks.filter(b => decisions[b.id] != null).length;
  const hasRejections = reviewableBlocks.some(b => decisions[b.id] === 'rejected');

  const handleAcceptAll = useCallback(() => {
    const next: Record<string, BlockDecision> = {};
    for (const b of reviewableBlocks) {
      next[b.id] = 'accepted';
    }
    setDecisions(next);
  }, [reviewableBlocks]);

  const handleOverride = useCallback((fieldPath: string, value: string) => {
    setOverrides(prev => ({ ...prev, [fieldPath]: value }));
  }, []);

  const togglePicker = useCallback((blockId: string) => {
    setExpandedPickers(prev => ({ ...prev, [blockId]: !prev[blockId] }));
  }, []);

  const handleComment = useCallback((blockId: string, text: string) => {
    setComments(prev => ({ ...prev, [blockId]: text }));
  }, []);

  const handleConfirm = useCallback(() => {
    if (onConfirm) {
      onConfirm(decisions, overrides, comments, textEvidence);
    }
  }, [onConfirm, decisions, overrides, comments, textEvidence]);

  return (
    <div className="human-view">
      {onBack && (
        <button className="btn btn-back" onClick={onBack}>← Назад</button>
      )}
      {lifecycle && (
        <div className="human-view-lifecycle">
          <span className={`lifecycle-badge lifecycle-${lifecycle}`}>{lifecycle}</span>
        </div>
      )}
      {loading && <div className="human-view-loading">Готовим человеческую модель…</div>}
      {error && (
        <div className="human-view-error" role="alert">
          Не удалось загрузить человеческое представление: {error}
        </div>
      )}
      {markdown && !loading && (
        <>
          {showPerBlock && (
            <div className="block-review-toolbar">
              <span className="block-review-counter">
                {decidedCount} / {reviewableBlocks.length} блоков рассмотрено
              </span>
              <button
                className="btn btn-small btn-accept-all"
                onClick={handleAcceptAll}
                title="Принять все блоки"
              >
                Принять все
              </button>
              <button
                className={`btn btn-small btn-source-toggle ${sourceOpen ? 'btn-source-toggle--active' : ''}`}
                onClick={() => setSourceOpen(prev => !prev)}
                title="Показать исходный текст для привязки свидетельств"
              >
                {sourceOpen ? '✕ Исходник' : '📄 Исходник'}
              </button>
              <button
                className={`btn btn-small btn-source-toggle ${chatOpen ? 'btn-source-toggle--active' : ''}`}
                onClick={() => setChatOpen(prev => !prev)}
                title="Диалог с LLM для уточнения модели"
              >
                {chatOpen ? '✕ Диалог' : '💬 Диалог'}
              </button>
              {textEvidence.length > 0 && (
                <span className="evidence-counter">
                  {textEvidence.length} свидетельств{textEvidence.length === 1 ? 'о' : textEvidence.length < 5 ? 'а' : ''}
                </span>
              )}
              {signals.length > 0 && (
                <button
                  className={`btn btn-small btn-signals ${signalsOpen ? 'btn-signals--active' : ''}`}
                  onClick={() => setSignalsOpen(prev => !prev)}
                  title="Обнаружены паттерны коррекций"
                >
                  {signals.length} сигнал{signals.length === 1 ? '' : signals.length < 5 ? 'а' : 'ов'}
                </button>
              )}
            </div>
          )}

          {/* M-9: correction signals panel */}
          {signalsOpen && signals.length > 0 && (
            <div className="correction-signals-panel">
              <div className="correction-signals-header">
                Паттерны коррекций (промпт может систематически ошибаться)
              </div>
              {signals.map((sig, i) => (
                <div key={i} className={`correction-signal correction-signal--${sig.severity}`}>
                  <span className="correction-signal-badge">{sig.severity}</span>
                  <span className="correction-signal-text">{sig.message}</span>
                </div>
              ))}
            </div>
          )}

          {/* M-6: floating bind popup */}
          {pendingSelection && sourceOpen && (
            <div className="evidence-bind-popup">
              <div className="evidence-bind-header">
                Выделено: «{pendingSelection.length > 80 ? pendingSelection.slice(0, 77) + '…' : pendingSelection}»
              </div>
              {bindTarget ? (
                <div className="evidence-bind-confirm">
                  <span>Привязать к <strong>{bindTarget}</strong>?</span>
                  <button className="btn btn-small btn-primary" onClick={() => handleBindEvidence(bindTarget)}>
                    Привязать
                  </button>
                  <button className="btn btn-small" onClick={() => setBindTarget(null)}>
                    Отмена
                  </button>
                </div>
              ) : (
                <div className="evidence-bind-targets">
                  <span className="evidence-bind-label">Привязать к полю:</span>
                  {allFieldPaths.map(fp => (
                    <button
                      key={fp}
                      className="btn btn-small btn-evidence-target"
                      onClick={() => setBindTarget(fp)}
                    >
                      {fp.replace('article_model.', '')}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="human-view-split">

          {/* M-6: source text panel */}
          {sourceOpen && (
            <div className="source-text-panel">
              <div className="source-text-header">Исходный текст</div>
              <div className="source-text-body" ref={sourceRef}>
                {sourceText === null
                  ? <div className="source-text-loading">Загрузка…</div>
                  : <pre className="source-text-content">{sourceText}</pre>
                }
              </div>
            </div>
          )}

          {/* M-8: refinement chat panel */}
          {chatOpen && (
            <div className="refinement-chat-panel">
              <div className="refinement-chat-header">Диалог с LLM</div>
              <div className="refinement-chat-messages">
                {chatHistory.length === 0 && (
                  <div className="refinement-chat-empty">
                    Задайте вопрос или попросите пересмотреть конкретное поле модели.
                  </div>
                )}
                {chatHistory.map((entry, i) => (
                  <div
                    key={i}
                    className={`refinement-chat-msg refinement-chat-msg--${entry.role}`}
                  >
                    <div className="refinement-chat-msg-role">
                      {entry.role === 'user' ? 'Вы' : 'Система'}
                    </div>
                    <div className="refinement-chat-msg-text">{entry.content}</div>
                    {entry.suggestions && entry.suggestions.length > 0 && (
                      <div className="refinement-chat-suggestions">
                        {entry.suggestions.map((s, j) => (
                          <div key={j} className="refinement-suggestion">
                            <span className="refinement-suggestion-field">{s.field}</span>
                            <span className="refinement-suggestion-arrow">&rarr;</span>
                            <span className="refinement-suggestion-value">{s.value}</span>
                            {s.reason && (
                              <span className="refinement-suggestion-reason">({s.reason})</span>
                            )}
                            <button
                              className="btn btn-small btn-primary refinement-suggestion-apply"
                              onClick={() => applySuggestion(s.field, s.value)}
                            >
                              Применить
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
                {chatSending && (
                  <div className="refinement-chat-msg refinement-chat-msg--assistant">
                    <div className="refinement-chat-msg-text refinement-chat-thinking">Думаю…</div>
                  </div>
                )}
                {chatError && (
                  <div className="refinement-chat-error">{chatError}</div>
                )}
                <div ref={chatEndRef} />
              </div>
              <div className="refinement-chat-input-row">
                <input
                  className="refinement-chat-input"
                  type="text"
                  placeholder="Напишите, что хотите уточнить…"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      sendRefinement();
                    }
                  }}
                  disabled={chatSending}
                />
                <button
                  className="btn btn-small btn-primary"
                  onClick={sendRefinement}
                  disabled={chatSending || !chatInput.trim()}
                >
                  Отправить
                </button>
              </div>
            </div>
          )}

          <div className="human-view-body">
            {blocks.map((block) => {
              const reviewable = showPerBlock && isReviewableBlock(block);
              const decision = decisions[block.id];

              const blockStyle: React.CSSProperties = decision === 'accepted'
                ? { borderLeftColor: '#34c77b', background: 'rgba(52, 199, 123, 0.06)', transition: 'none' }
                : decision === 'rejected'
                  ? { borderLeftColor: '#e5534b', background: 'rgba(229, 83, 75, 0.06)', transition: 'none' }
                  : {};

              return (
                <div
                  key={block.id}
                  className={[
                    'human-view-block',
                    reviewable ? 'human-view-block--reviewable' : '',
                    decision === 'accepted' ? 'human-view-block--accepted' : '',
                    decision === 'rejected' ? 'human-view-block--rejected' : '',
                  ].filter(Boolean).join(' ')}
                  style={blockStyle}
                >
                  <div
                    // eslint-disable-next-line react/no-danger
                    dangerouslySetInnerHTML={{ __html: block.html }}
                  />
                  {reviewable && (() => {
                    const typologies = getTypologiesForBlock(block);
                    const pickerExpanded = expandedPickers[block.id];
                    const hasOverrides = typologies.some(t => overrides[t.fieldPath]);
                    return (
                      <>
                        <div className="block-controls">
                          <button
                            className={`block-btn block-btn--accept ${decision === 'accepted' ? 'block-btn--active' : ''}`}
                            onClick={() => handleDecision(block.id, decision === 'accepted' ? null : 'accepted')}
                            title="Принять этот блок"
                          >
                            {decision === 'accepted' ? '✓ Принято' : 'Принять'}
                          </button>
                          <button
                            className={`block-btn block-btn--reject ${decision === 'rejected' ? 'block-btn--active' : ''}`}
                            onClick={() => handleDecision(block.id, decision === 'rejected' ? null : 'rejected')}
                            title="Оспорить / отклонить этот блок"
                          >
                            {decision === 'rejected' ? '✗ Оспорено' : 'Оспорить'}
                          </button>
                          {typologies.length > 0 && (
                            <button
                              className={`block-btn block-btn--typology ${pickerExpanded ? 'block-btn--active' : ''}`}
                              onClick={() => togglePicker(block.id)}
                              title="Показать типологию — выбрать другой вариант"
                            >
                              {hasOverrides ? '⇄ Заменено' : '⇄ Поменять'}
                            </button>
                          )}
                        </div>
                        {typologies.length > 0 && pickerExpanded && (
                          <div className="typology-picker">
                            {typologies.map(typology => {
                              const currentOverride = overrides[typology.fieldPath];
                              return (
                                <div key={typology.fieldPath} className="typology-section">
                                  <div className="typology-picker-header">{typology.label}:</div>
                                  <div className="typology-options">
                                    {typology.options.map(opt => (
                                      <label key={opt.value} className={`typology-option ${currentOverride === opt.value ? 'typology-option--selected' : ''}`}>
                                        <input
                                          type="radio"
                                          name={`typology_${block.id}_${typology.fieldPath}`}
                                          value={opt.value}
                                          checked={currentOverride === opt.value}
                                          onChange={() => {
                                            handleOverride(typology.fieldPath, opt.value);
                                            handleDecision(block.id, 'rejected');
                                          }}
                                        />
                                        <span className="typology-option-label">{opt.label}</span>
                                      </label>
                                    ))}
                                  </div>
                                  {currentOverride && (
                                    <button
                                      className="block-btn block-btn--small"
                                      onClick={() => {
                                        setOverrides(prev => {
                                          const next = { ...prev };
                                          delete next[typology.fieldPath];
                                          return next;
                                        });
                                      }}
                                    >
                                      Сбросить выбор
                                    </button>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        )}
                        {decision === 'rejected' && (
                          <div className="block-comment">
                            <textarea
                              className="block-comment-input"
                              placeholder="Почему не согласны? (необязательно)"
                              value={comments[block.id] || ''}
                              onChange={(e) => handleComment(block.id, e.target.value)}
                              rows={2}
                            />
                          </div>
                        )}
                        {/* M-6: show bound evidence for this block's fields */}
                        {(() => {
                          const blockEvidence = textEvidence.filter(e =>
                            block.allFieldPaths.includes(e.fieldPath)
                          );
                          if (blockEvidence.length === 0) return null;
                          return (
                            <div className="block-evidence-list">
                              <div className="block-evidence-header">Привязанные свидетельства:</div>
                              {blockEvidence.map((ev, i) => (
                                <div key={`${ev.fieldPath}_${i}`} className="block-evidence-item">
                                  <span className="block-evidence-field">{ev.fieldPath.replace('article_model.', '')}</span>
                                  <span className="block-evidence-text">
                                    «{ev.selectedText.length > 100 ? ev.selectedText.slice(0, 97) + '…' : ev.selectedText}»
                                  </span>
                                  <button
                                    className="block-evidence-remove"
                                    onClick={() => removeEvidence(ev.fieldPath, textEvidence.indexOf(ev))}
                                    title="Убрать свидетельство"
                                  >
                                    ✕
                                  </button>
                                </div>
                              ))}
                            </div>
                          );
                        })()}
                      </>
                    );
                  })()}
                </div>
              );
            })}
          </div>

          </div>{/* close human-view-split */}
        </>
      )}
      {onConfirm && kind === 'article' && markdown && !loading && !isConfirmed && (
        <div className="human-view-actions">
          {allDecided ? (
            <>
              <button className="btn btn-primary" onClick={handleConfirm}>
                {hasRejections
                  ? `Зафиксировать модель (${decidedCount - Object.values(decisions).filter(d => d === 'rejected').length} принято, ${Object.values(decisions).filter(d => d === 'rejected').length} оспорено)`
                  : 'Зафиксировать модель — все блоки приняты'
                }
              </button>
              {hasRejections && (
                <p className="human-view-hint human-view-hint--warning">
                  Оспоренные блоки будут помечены для пересмотра. Вы сможете
                  исправить их в технической модели или запросить повторный анализ.
                </p>
              )}
            </>
          ) : (
            <>
              <button className="btn btn-primary" disabled>
                Зафиксировать модель
              </button>
              <p className="human-view-hint">
                Рассмотрите каждый блок модели — нажмите «Принять» или «Оспорить»
                для каждого раздела. Когда все решения приняты, кнопка
                фиксации станет активной.
              </p>
            </>
          )}
        </div>
      )}
    </div>
  );
}
