import { useState, type FormEvent } from 'react';
import { api, setToken, type AuthUser } from '../api/client';

type Mode = 'signup' | 'continue';

interface AuthGateProps {
  onAuthenticated: (user: AuthUser) => void;
}

export function AuthGate({ onAuthenticated }: AuthGateProps) {
  const [mode, setMode] = useState<Mode>('signup');
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (mode === 'signup') {
        const trimmedName = displayName.trim();
        if (!trimmedName) {
          setError('Please enter a display name.');
          setBusy(false);
          return;
        }
        const res = await api.signup(trimmedName, email.trim() || undefined);
        setToken(res.session_token);
        onAuthenticated(res.user);
      } else {
        const trimmedEmail = email.trim();
        if (!trimmedEmail) {
          setError('Please enter the email you used to sign up.');
          setBusy(false);
          return;
        }
        const res = await api.continueSession(trimmedEmail);
        setToken(res.session_token);
        onAuthenticated(res.user);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      // Friendly mapping of common backend error codes
      if (msg.includes('email_already_registered')) {
        setError('That email is already registered. Switch to Continue and use it to sign in.');
      } else if (msg.includes('email_not_found')) {
        setError('No account with that email. Switch to Sign up to create one.');
      } else if (msg.includes('display_name_required')) {
        setError('Please enter a display name.');
      } else if (msg.includes('email_required')) {
        setError('Please enter your email.');
      } else {
        setError(msg);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-gate">
      <div className="auth-card">
        <h1 className="auth-title">Kairoskopion</h1>
        <p className="auth-sub">
          Publication-positioning cockpit — staging tester preview
        </p>

        <div className="auth-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'signup'}
            className={`auth-tab ${mode === 'signup' ? 'auth-tab--active' : ''}`}
            onClick={() => { setMode('signup'); setError(null); }}
          >
            Sign up
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'continue'}
            className={`auth-tab ${mode === 'continue' ? 'auth-tab--active' : ''}`}
            onClick={() => { setMode('continue'); setError(null); }}
          >
            Continue
          </button>
        </div>

        <form className="auth-form" onSubmit={onSubmit}>
          {mode === 'signup' && (
            <label className="auth-field">
              <span className="auth-label">Display name *</span>
              <input
                className="auth-input"
                type="text"
                value={displayName}
                onChange={e => setDisplayName(e.target.value)}
                placeholder="e.g. Anna Researcher"
                autoComplete="name"
                disabled={busy}
                required
              />
            </label>
          )}

          <label className="auth-field">
            <span className="auth-label">
              Email {mode === 'signup' ? '(optional)' : '*'}
            </span>
            <input
              className="auth-input"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@example.org"
              autoComplete="email"
              disabled={busy}
              required={mode === 'continue'}
            />
            {mode === 'signup' && (
              <span className="auth-hint">
                Optional, but useful if you want to continue from another device.
              </span>
            )}
          </label>

          {error && (
            <div className="auth-error" role="alert">{error}</div>
          )}

          <button
            type="submit"
            className="auth-submit"
            disabled={busy}
          >
            {busy
              ? 'Working…'
              : mode === 'signup' ? 'Create workspace' : 'Continue'}
          </button>
        </form>

        <p className="auth-disclaimer">
          This staging login has <strong>no password</strong> and{' '}
          <strong>no email confirmation</strong>. Anyone who knows your email
          can access your workspace. Use only with trusted testers.
        </p>
      </div>
    </div>
  );
}
