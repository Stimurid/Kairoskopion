import { useState, type FormEvent } from 'react';
import { api, setToken, type AuthUser } from '../api/client';

interface AuthGateProps {
  onAuthenticated: (user: AuthUser) => void;
}

export function AuthGate({ onAuthenticated }: AuthGateProps) {
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const trimmedName = displayName.trim();
    if (!trimmedName) {
      setError('Введите имя.');
      return;
    }
    setBusy(true);
    try {
      const res = await api.signup(trimmedName, email.trim() || undefined);
      setToken(res.session_token);
      onAuthenticated(res.user);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-gate">
      <div className="auth-card">
        <h1 className="auth-title">Kairoskopion</h1>
        <p className="auth-sub">
          Кокпит позиционирования публикаций — staging preview
        </p>

        <form className="auth-form" onSubmit={onSubmit}>
          <label className="auth-field">
            <span className="auth-label">Имя *</span>
            <input
              className="auth-input"
              type="text"
              value={displayName}
              onChange={e => setDisplayName(e.target.value)}
              placeholder="Например: Анна Исследователь"
              autoComplete="name"
              disabled={busy}
              required
            />
          </label>

          <label className="auth-field">
            <span className="auth-label">Email (необязательно)</span>
            <input
              className="auth-input"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@example.org"
              autoComplete="email"
              disabled={busy}
            />
            <span className="auth-hint">
              Если указать email — можно продолжить работу с другого устройства.
            </span>
          </label>

          {error && (
            <div className="auth-error" role="alert">{error}</div>
          )}

          <button
            type="submit"
            className="auth-submit"
            disabled={busy}
          >
            {busy ? 'Подождите…' : 'Войти'}
          </button>
        </form>
      </div>
    </div>
  );
}
