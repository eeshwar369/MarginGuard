'use client';
import { useState, type FormEvent } from 'react';
import {
  ArrowRight,
  ArrowUpRight,
  Check,
  Database,
  FileCheck2,
  Fingerprint,
  GitBranch,
  ShieldCheck,
} from 'lucide-react';
import { api, setCsrf } from '@/lib/api';
import type { Config, User } from '@/lib/contracts';
import { Brand, Spinner } from './ui';
export function Auth({ config, onLogin }: { config: Config; onLogin: (user: User) => void }) {
  const [mode, setMode] = useState<'landing' | 'login' | 'register'>('landing');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function submit(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    setBusy(true);
    setError('');
    try {
      const body = event ? Object.fromEntries(new FormData(event.currentTarget)) : undefined;
      const u = await api<User>(event ? '/auth/' + mode : '/auth/demo', 'POST', body);
      setCsrf(u.csrf_token);
      onLogin(u);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="landing">
      <header className="landing-nav">
        <Brand />
        <div>
          <span className="tagline">DECISIONS WITH RECEIPTS</span>
          <button
            className="button secondary"
            onClick={() => {
              setError('');
              setMode(mode === 'landing' ? 'login' : 'landing');
            }}
          >
            {mode === 'landing' ? 'Sign in' : 'Back to home'}
            <ArrowUpRight size={16} />
          </button>
        </div>
      </header>
      <main className="landing-grid">
        <div className="landing-copy">
          <div className="eyebrow">
            <span className="live-dot" /> YOUR MARGIN HAS A STORY
          </div>
          <h1>
            Know what changed.
            <br />
            <em>Decide what’s next.</em>
          </h1>
          <p>
            Turn scattered business exports into evidence you can inspect, decisions you can
            stress-test, and a record you can stand behind.
          </p>
          <div className="hero-actions">
            {config.demo && (
              <button className="button primary large" onClick={() => submit()} disabled={busy}>
                {busy ? <Spinner /> : <ArrowRight size={19} />} Explore the live workspace
              </button>
            )}
            {config.registration && (
              <button
                className="text-button"
                onClick={() => {
                  setMode('register');
                  setError('');
                }}
              >
                Create your workspace <ArrowUpRight size={16} />
              </button>
            )}
          </div>
          <div className="hero-note">
            <Check size={15} /> Private demo workspace · Synthetic data · No card required
          </div>
          <div className="hero-proof">
            <div>
              <Database size={18} />
              <strong>Trace every number</strong>
              <span>From the finding to the source row.</span>
            </div>
            <div>
              <GitBranch size={18} />
              <strong>Challenge every decision</strong>
              <span>See where the recommendation breaks.</span>
            </div>
            <div>
              <FileCheck2 size={18} />
              <strong>Approve the exact version</strong>
              <span>Changed inputs require a fresh review.</span>
            </div>
          </div>
        </div>
        {mode === 'landing' ? (
          <div className="hero-visual">
            <div className="visual-top">
              <span className="tiny-label">ILLUSTRATIVE DECISION WORKFLOW</span>
              <ShieldCheck size={18} />
            </div>
            <div className="visual-heading">
              From a question
              <br />
              to a defensible decision.
            </div>
            <div className="flow-card">
              <span className="step-no">01</span>
              <div>
                <strong>“Why is margin shrinking?”</strong>
                <span>Orders + refunds + fulfilment costs</span>
              </div>
              <Database size={19} />
            </div>
            <div className="flow-connector" />
            <div className="flow-card">
              <span className="step-no">02</span>
              <div>
                <strong>Follow the evidence</strong>
                <span>Reconciled ledger. Inspectable calculations.</span>
              </div>
              <Fingerprint size={19} />
            </div>
            <div className="flow-connector" />
            <div className="flow-card highlight">
              <span className="step-no">03</span>
              <div>
                <strong>Test the trade-offs</strong>
                <span>Demand loss, cost savings, and uncertainty.</span>
              </div>
              <GitBranch size={19} />
            </div>
            <div className="flow-connector" />
            <div className="visual-footer">
              <ShieldCheck size={20} />
              <div>
                <strong>You make the final call.</strong>
                <span>Every approval is tied to its inputs.</span>
              </div>
              <Check size={18} />
            </div>
            <div className="visual-grid" />
          </div>
        ) : (
          <form className="auth-card" onSubmit={submit}>
            <div className="eyebrow">YOUR PRIVATE WORKSPACE</div>
            <h2>{mode === 'login' ? 'Welcome back.' : 'Build better decisions.'}</h2>
            <p>
              {mode === 'login'
                ? 'Sign in to your evidence and decision history.'
                : 'Start with CSV exports or explore the built-in sample.'}
            </p>
            {mode === 'register' && (
              <>
                <label>
                  Full name
                  <input name="name" required minLength={2} maxLength={80} autoComplete="name" />
                </label>
                <label>
                  Workspace name
                  <input
                    name="workspace_name"
                    required
                    minLength={2}
                    maxLength={80}
                    placeholder="Your business"
                  />
                </label>
              </>
            )}
            <label>
              Email address
              <input type="email" name="email" required autoComplete="email" maxLength={254} />
            </label>
            <label>
              Password
              <input
                type="password"
                name="password"
                required
                minLength={12}
                maxLength={128}
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              />
              <small>At least 12 characters.</small>
            </label>
            <button className="button primary" disabled={busy}>
              {busy ? <Spinner /> : <ArrowRight size={17} />}{' '}
              {mode === 'login' ? 'Sign in' : 'Create workspace'}
            </button>
            {(config.registration || mode === 'register') && (
              <button
                type="button"
                className="text-button"
                onClick={() => {
                  setMode(mode === 'login' ? 'register' : 'login');
                  setError('');
                }}
              >
                {mode === 'login'
                  ? 'Need a workspace? Create one'
                  : 'Already have an account? Sign in'}
              </button>
            )}
          </form>
        )}
        {error && (
          <div role="alert" className="auth-error notice danger">
            {error}
          </div>
        )}
      </main>
      <footer className="landing-footer">
        <span>Built by Genztech</span>
        <span>Evidence first. Human approved.</span>
        <span>PS-04 · AI Decision Engine for Business Data</span>
      </footer>
    </div>
  );
}
