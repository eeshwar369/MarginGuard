'use client';
import { useCallback, useEffect, useState } from 'react';
import {
  Activity,
  ArrowRight,
  ChevronDown,
  Database,
  FileCheck2,
  FlaskConical,
  GitBranch,
  LayoutDashboard,
  LogOut,
  Menu,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  X,
} from 'lucide-react';
import { api, dateTime, setCsrf } from '@/lib/api';
import type { AuditEvent, Config, User, Workspace } from '@/lib/contracts';
import { Auth } from './auth';
import { Badge, Brand, Empty, SectionTitle, Spinner } from './ui';
import { Overview } from './overview';
import { Investigations } from './investigations';
import { DecisionLab } from './decision-lab';
import { DataSources } from './data-sources';
import { EvidenceDrawer } from './evidence';
import { Memos } from './memos';
const navigation = [
  { name: 'Overview', icon: LayoutDashboard },
  { name: 'Investigations', icon: Search },
  { name: 'Decision lab', icon: GitBranch },
  { name: 'Data sources', icon: Database },
  { name: 'Decision memos', icon: FileCheck2 },
  { name: 'Activity', icon: Activity },
];
const initialConfig: Config = {
  ai_available: false,
  model: '',
  registration: false,
  demo: false,
  max_upload_mb: 8,
  max_rows: 50000,
};
function ActivityView({
  workspace,
  onRefresh,
  onError,
}: {
  workspace: Workspace;
  onRefresh: () => Promise<void>;
  onError: (s: string) => void;
}) {
  const [events, setEvents] = useState<AuditEvent[]>([]),
    [name, setName] = useState(workspace.name),
    [busy, setBusy] = useState(false),
    [offset, setOffset] = useState(0),
    [loaded, setLoaded] = useState(false);
  useEffect(() => {
    api<AuditEvent[]>('/audit?offset=' + offset)
      .then((x) => {
        setEvents(x);
        setLoaded(true);
      })
      .catch((e) => onError(e.message));
  }, [offset, onError]);
  return (
    <>
      <SectionTitle
        eyebrow="WORKSPACE ACTIVITY"
        title="An accountable decision trail."
        description="Review imports, investigations, corrections, scenario changes, and approvals."
      />
      <div className="activity-grid">
        <section className="card">
          <div className="card-heading">
            <h2>
              <Activity size={18} /> Audit history
            </h2>
            <Badge>Server recorded</Badge>
          </div>
          {!loaded ? (
            <div className="loading-inline">
              <Spinner />
            </div>
          ) : events.length ? (
            events.map((e) => (
              <details className="audit-event" key={e.id}>
                <summary>
                  <span className="audit-dot" />
                  <strong>{e.action.replaceAll('.', ' / ').replaceAll('_', ' ')}</strong>
                  <time>{dateTime(e.created_at)}</time>
                </summary>
                <pre>{JSON.stringify(e.details, null, 2)}</pre>
              </details>
            ))
          ) : (
            <p className="padded muted">No events on this page.</p>
          )}
          <div className="pagination">
            <button
              className="button secondary small"
              disabled={!offset}
              onClick={() => setOffset((x) => Math.max(0, x - 100))}
            >
              Previous
            </button>
            <span>Page {offset / 100 + 1}</span>
            <button
              className="button secondary small"
              disabled={events.length < 100}
              onClick={() => setOffset((x) => x + 100)}
            >
              Next
            </button>
          </div>
        </section>
        <section className="card settings-card">
          <Settings2 size={22} />
          <h2>Workspace settings</h2>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              setBusy(true);
              try {
                await api('/workspace', 'PATCH', { name });
                await onRefresh();
              } catch (e) {
                onError((e as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            <label>
              Workspace name
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                minLength={2}
                maxLength={80}
                required
              />
            </label>
            <button className="button secondary" disabled={busy || name === workspace.name}>
              {busy ? <Spinner /> : null} Save name
            </button>
          </form>
          <div className="aside-note">
            <ShieldCheck size={19} />
            <h3>Your data boundary</h3>
            <p>
              Your workspace is isolated from other accounts. AI planning only receives your
              question and numeric summaries after consent.
            </p>
            <p>Demo workspaces are temporary. Export records you need to keep.</p>
          </div>
        </section>
      </div>
    </>
  );
}
export default function MarginGuard() {
  const [user, setUser] = useState<User | null>(null),
    [config, setConfig] = useState(initialConfig),
    [workspace, setWorkspace] = useState<Workspace | null>(null),
    [loading, setLoading] = useState(true),
    [page, setPage] = useState('Overview'),
    [error, setError] = useState(''),
    [mobile, setMobile] = useState(false),
    [evidence, setEvidence] = useState<{ id: string; datasetId: string } | null>(null),
    [refreshing, setRefreshing] = useState(false);
  const onError = useCallback((s: string) => setError(s), []);
  const refresh = useCallback(async () => {
    const w = await api<Workspace>('/workspace');
    setWorkspace(w);
  }, []);
  useEffect(() => {
    Promise.all([
      api<Config>('/config'),
      api<User>('/auth/me').catch((e) => {
        if (e.status === 401) return null;
        throw e;
      }),
    ])
      .then(async ([c, u]) => {
        setConfig(c);
        if (u) {
          setCsrf(u.csrf_token);
          setUser(u);
          await refresh();
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
    const expired = () => {
      setUser(null);
      setWorkspace(null);
      setCsrf('');
    };
    window.addEventListener('session-expired', expired);
    return () => window.removeEventListener('session-expired', expired);
  }, [refresh]);
  function navigate(value: string) {
    setPage(value);
    setMobile(false);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
  async function login(u: User) {
    setUser(u);
    setError('');
    setLoading(true);
    try {
      await refresh();
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }
  const openEvidence = (id: string, datasetId?: string) => {
    if (datasetId || workspace?.dataset)
      setEvidence({ id, datasetId: datasetId ?? workspace!.dataset!.id });
  };
  if (loading)
    return (
      <div className="app-loading">
        <Brand />
        <Spinner />
        <p>Preparing your workspace</p>
      </div>
    );
  if (!user)
    return (
      <>
        {error && (
          <div className="global-error notice danger" role="alert">
            {error}
            <button className="text-button" onClick={() => window.location.reload()}>
              Retry connection
            </button>
          </div>
        )}
        <Auth config={config} onLogin={login} />
      </>
    );
  const dataset = workspace?.dataset,
    ready = dataset?.status === 'ready';
  return (
    <div className="app-shell">
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      {mobile && (
        <button
          aria-label="Close navigation"
          className="nav-backdrop"
          onClick={() => setMobile(false)}
        />
      )}
      <aside className={'sidebar ' + (mobile ? 'open' : '')}>
        <div className="sidebar-content">
          <Brand />
          <div className="workspace-switch">
            <div className="workspace-avatar">{workspace?.name.slice(0, 1) ?? 'M'}</div>
            <div>
              <strong>{workspace?.name ?? 'Workspace'}</strong>
              <span>{user.is_demo ? 'Demo workspace' : 'Private workspace'}</span>
            </div>
            <ChevronDown size={14} />
          </div>
          <div className="nav-label">WORKSPACE</div>
          <nav aria-label="Main navigation">
            {navigation.map((n) => (
              <button
                key={n.name}
                className={page === n.name ? 'active' : ''}
                onClick={() => navigate(n.name)}
                aria-current={page === n.name ? 'page' : undefined}
              >
                <n.icon size={18} />
                {n.name}
                {n.name === 'Data sources' && dataset?.status !== 'ready' && (
                  <span className="nav-attention" />
                )}
              </button>
            ))}
          </nav>
          <div className="sidebar-note">
            <ShieldCheck size={20} />
            <strong>Every decision has receipts.</strong>
            <p>
              Evidence you can inspect.
              <br />
              Assumptions you can challenge.
            </p>
          </div>
        </div>
        <div className="sidebar-bottom">
          <div className="user-row">
            <div className="user-avatar">
              {user.name
                .split(' ')
                .map((x) => x[0])
                .slice(0, 2)
                .join('')}
            </div>
            <div>
              <strong>{user.name}</strong>
              <span>{user.is_demo ? 'Guest reviewer' : 'Workspace owner'}</span>
            </div>
          </div>
          <button
            aria-label="Sign out"
            className="sidebar-signout"
            onClick={async () => {
              try {
                await api('/auth/logout', 'POST');
                setUser(null);
                setWorkspace(null);
                setCsrf('');
                setPage('Overview');
              } catch (e) {
                onError((e as Error).message);
              }
            }}
          >
            <LogOut size={17} />
            Sign out
          </button>
        </div>
      </aside>
      <div className="app-body">
        <header className="topbar">
          <div>
            <button
              className="icon-button mobile-menu"
              aria-label="Open navigation"
              onClick={() => setMobile(true)}
            >
              <Menu size={21} />
            </button>
            <span className="breadcrumb">
              Workspace <span>/</span> <strong>{page}</strong>
            </span>
          </div>
          <div className="topbar-right">
            {dataset?.synthetic && (
              <Badge tone="amber">
                <FlaskConical size={12} /> Synthetic sample
              </Badge>
            )}
            <span className="engine-status">
              <span className="live-dot" />
              {config.ai_available ? 'AI + verified calculations' : 'Verified calculations'}
            </span>
            <button
              title="Refresh workspace"
              className="topbar-version"
              disabled={refreshing}
              onClick={async () => {
                setRefreshing(true);
                try {
                  await refresh();
                } catch (e) {
                  onError((e as Error).message);
                } finally {
                  setRefreshing(false);
                }
              }}
            >
              {refreshing ? <Spinner /> : dataset ? `Data v${dataset.version}` : 'No data'}
              <Database size={14} />
            </button>
          </div>
        </header>
        <main id="main" className="main-content">
          {error && (
            <div role="alert" className="notice danger app-error">
              <span>{error}</span>
              <button
                aria-label="Dismiss error"
                className="icon-button"
                onClick={() => setError('')}
              >
                <X size={17} />
              </button>
            </div>
          )}
          {!workspace ? (
            <Empty
              title="Your workspace could not be loaded."
              description="Check your connection and retry."
            >
              <button
                className="button primary"
                onClick={() => refresh().catch((e) => onError(e.message))}
              >
                Retry
              </button>
            </Empty>
          ) : (
            <>
              {page === 'Data sources' ? (
                <DataSources
                  workspace={workspace}
                  config={config}
                  onRefresh={refresh}
                  onError={onError}
                />
              ) : page === 'Activity' ? (
                <ActivityView workspace={workspace} onRefresh={refresh} onError={onError} />
              ) : page === 'Decision memos' ? (
                <Memos onError={onError} navigate={navigate} />
              ) : !ready ? (
                <Empty
                  title={
                    dataset
                      ? 'Your data needs a quick review.'
                      : 'Your first insight starts with your data.'
                  }
                  description={
                    dataset
                      ? 'Resolve the import issues before investigating or comparing decisions.'
                      : 'Import your exports or load the built-in sample to explore MarginGuard.'
                  }
                >
                  <button className="button primary" onClick={() => navigate('Data sources')}>
                    Open data sources <ArrowRight size={16} />
                  </button>
                </Empty>
              ) : page === 'Overview' ? (
                <Overview dataset={dataset!} onEvidence={openEvidence} navigate={navigate} />
              ) : page === 'Investigations' ? (
                <Investigations config={config} onEvidence={openEvidence} onError={onError} />
              ) : page === 'Decision lab' ? (
                <DecisionLab
                  key={dataset!.id}
                  workspace={workspace}
                  onSaved={refresh}
                  onMemo={() => navigate('Decision memos')}
                  onError={onError}
                />
              ) : null}
            </>
          )}
          <footer className="app-footer">
            <span>
              <ShieldCheck size={13} /> Built for decisions you can defend.
            </span>
            <span>MarginGuard · Genztech</span>
          </footer>
        </main>
      </div>
      {evidence && (
        <EvidenceDrawer
          id={evidence.id}
          datasetId={evidence.datasetId}
          activeId={dataset?.id}
          onClose={() => setEvidence(null)}
          onChanged={refresh}
        />
      )}
    </div>
  );
}
