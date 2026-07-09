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
 *   LLM: parsed_ok (gpt-4o-mini)
 *   LLM: repaired_ok (gpt-4o-mini, 2 attempts)
 *   LLM: fallback (provider_error) [AUTH_FAILED]
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

  const modelDisplay = attempt.effective_model || attempt.llm_model || '';
  const attemptCount = attempt.attempt_count ?? 0;
  const errorCode = attempt.final_error_code || '';

  let text = isFallback ? `fallback (${reason})` : status;
  if (modelDisplay) text += ` (${modelDisplay}`;
  if (attemptCount > 1) text += modelDisplay ? `, ${attemptCount} attempts` : `(${attemptCount} attempts`;
  if (modelDisplay || attemptCount > 1) text += ')';
  if (isFallback && errorCode) text += ` [${errorCode}]`;

  const cls = isFallback
    ? 'llm-attempt-badge llm-attempt-badge--fallback'
    : 'llm-attempt-badge llm-attempt-badge--ok';

  const titleParts = [
    `parse_status: ${status}`,
    `fallback_reason: ${reason}`,
  ];
  if (attempt.requested_model) titleParts.push(`requested: ${attempt.requested_model}`);
  if (attempt.effective_model) titleParts.push(`effective: ${attempt.effective_model}`);
  if (attemptCount) titleParts.push(`attempts: ${attemptCount}`);
  if (attempt.agent_role) titleParts.push(`agent: ${attempt.agent_role}`);
  if (errorCode) titleParts.push(`error: ${errorCode}`);

  return (
    <span
      className={cls}
      title={titleParts.join(' · ')}
    >
      {label ? `${label}: ` : 'LLM: '}{text}
    </span>
  );
}
