import type { ExtractionAttempt } from '../types/domain';

interface Props {
  attempt?: ExtractionAttempt | null;
  /** Optional label prefix, e.g. "Article", "Pathways", "Fit". */
  label?: string;
  /** Show only when fallback fired (hides on success). */
  onlyOnFallback?: boolean;
}

/**
 * Compact, ASCII, sanitized status badge for an LLM attempt.
 *
 * Examples:
 *   LLM: parsed_ok
 *   LLM: repaired_ok
 *   LLM: fallback (provider_error)
 *   LLM: fallback (schema_validation_failed)
 *
 * Never renders raw provider output, raw_output_ref, traceback, or
 * model-internal prompt text. Safe in any technical or human view.
 */
export function LLMAttemptBadge({ attempt, label, onlyOnFallback }: Props) {
  if (!attempt) return null;
  const isFallback = !!attempt.fallback_used;
  if (onlyOnFallback && !isFallback) return null;

  const status = attempt.parse_status ?? 'not_attempted';
  const reason = attempt.fallback_reason ?? 'not_applicable';
  const text = isFallback ? `fallback (${reason})` : status;
  const cls = isFallback
    ? 'llm-attempt-badge llm-attempt-badge--fallback'
    : 'llm-attempt-badge llm-attempt-badge--ok';
  return (
    <span
      className={cls}
      title={`parse_status: ${status} · fallback_reason: ${reason}`}
    >
      {label ? `${label}: ` : 'LLM: '}{text}
    </span>
  );
}
