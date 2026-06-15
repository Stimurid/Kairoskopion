import { useEffect, useState } from 'react';
import { getToken } from '../api/client';

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000';

type Kind = 'article' | 'venue';

interface Props {
  caseId: string;
  kind: Kind;
  venueKey?: string;
  onConfirm?: () => void;
  onBack?: () => void;
}

interface HumanViewResponse {
  format: string;
  case_id: string;
  lifecycle_status?: string;
  not_a_submission_recommendation: boolean;
  markdown: string;
}

// Minimal, dependency-free markdown renderer — handles H1/H2/H3, bold,
// italic, blockquote, bullet lists, paragraphs, HTML comments.
function renderMarkdown(md: string): string {
  // Strip <!-- ... --> machine field anchors (kept in markdown for later
  // round-tripping but not user-facing in the cockpit).
  let s = md.replace(/<!--[\s\S]*?-->/g, '');

  // Escape HTML entities (avoid XSS from extracted text)
  s = s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Blockquotes (lines starting with `&gt; `)
  s = s.replace(/^\s*&gt;\s*(.+)$/gm, '<blockquote>$1</blockquote>');

  // Headings
  s = s.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  s = s.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  s = s.replace(/^# (.+)$/gm, '<h1>$1</h1>');

  // Bold / italics
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>');
  s = s.replace(/_([^_\n]+)_/g, '<em>$1</em>');

  // Bullet lists — wrap consecutive `- ` lines into <ul>
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

  // Paragraphs — split on blank lines, wrap non-tag chunks
  const blocks = s.split(/\n{2,}/);
  return blocks
    .map(b => {
      const t = b.trim();
      if (!t) return '';
      // Already a block-level tag — leave it alone
      if (/^<(h1|h2|h3|h4|ul|ol|blockquote|pre|hr|div|p)\b/i.test(t)) {
        return t;
      }
      // Strip the YAML frontmatter block entirely (`---\n…\n---`)
      if (/^---\n[\s\S]*?\n---\s*$/m.test(t)) {
        return '';
      }
      return `<p>${t.replace(/\n/g, '<br/>')}</p>`;
    })
    .filter(Boolean)
    .join('\n');
}

export function HumanModelView({ caseId, kind, venueKey, onConfirm, onBack }: Props) {
  const [markdown, setMarkdown] = useState<string | null>(null);
  const [lifecycle, setLifecycle] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    setMarkdown(null);
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
        <article
          className="human-view-body"
          // eslint-disable-next-line react/no-danger
          dangerouslySetInnerHTML={{ __html: renderMarkdown(markdown) }}
        />
      )}
      {onConfirm && kind === 'article' && markdown && !loading && (
        <div className="human-view-actions">
          <button className="btn btn-primary" onClick={onConfirm}>
            Подтвердить модель
          </button>
          <p className="human-view-hint">
            Подтверждение фиксирует модель как точку, от которой пойдут
            дальнейшие fit/mismatch расчёты. Если что-то неверно — сначала
            переключитесь в «Техническую модель» и поправьте поля.
          </p>
        </div>
      )}
    </div>
  );
}
