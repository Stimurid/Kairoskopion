import type { ExtractionAttempt } from '../types/domain';

interface LayerSpec {
  key: string;
  /** Russian label shown in the user-facing warning. */
  label: string;
  attempt?: ExtractionAttempt | null;
}

interface Props {
  layers: LayerSpec[];
}

/**
 * Aggregated Russian-language fallback warning across multiple LLM
 * analysis layers (article / semantic profile / pathways / fit).
 *
 * Renders nothing when no layer fell back. With ONE failing layer,
 * shows the single-banner shape we've used per-layer. With TWO+
 * failing layers, switches to a bullet list under one parent block —
 * same shape as the backend `aggregate_warnings` helper produces in
 * markdown.
 *
 * Never renders raw provider output, raw_output_ref, traceback, or
 * model-internal prompt text — only the Russian sentence and a
 * compact ASCII technical hint.
 */
export function LLMAttemptWarning({ layers }: Props) {
  const failing = layers.filter(l => l.attempt?.fallback_used);
  if (failing.length === 0) return null;

  if (failing.length === 1) {
    const { label, attempt } = failing[0];
    const warning =
      attempt?.warning_for_user ??
      'LLM-вызов не дал корректный результат, поэтому использован fallback.';
    const ps = attempt?.parse_status ?? 'unknown';
    const fr = attempt?.fallback_reason ?? 'unknown';
    return (
      <div className="llm-attempt-warning" role="note">
        <p className="llm-attempt-warning-headline">
          <strong>⚠ {label}: {warning}</strong>
        </p>
        <p className="llm-attempt-warning-hint">
          <code>parse_status: '{ps}'</code>{' · '}
          <code>fallback_reason: '{fr}'</code>
        </p>
      </div>
    );
  }

  return (
    <div className="llm-attempt-warning" role="note">
      <p className="llm-attempt-warning-headline">
        <strong>⚠ Несколько слоёв анализа построены в предварительном режиме.</strong>
      </p>
      <ul className="llm-attempt-warning-list">
        {failing.map(({ key, label, attempt }) => {
          const warning =
            attempt?.warning_for_user ??
            'LLM-вызов не дал корректный результат.';
          const ps = attempt?.parse_status ?? 'unknown';
          const fr = attempt?.fallback_reason ?? 'unknown';
          return (
            <li key={key}>
              <strong>{label}</strong> — {warning}
              <div className="llm-attempt-warning-hint">
                <code>parse_status: '{ps}'</code>{' · '}
                <code>fallback_reason: '{fr}'</code>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
