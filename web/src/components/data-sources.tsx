'use client';
import { useState, type FormEvent } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  CheckCheck,
  Database,
  Download,
  FileSpreadsheet,
  FlaskConical,
  History,
  Upload,
} from 'lucide-react';
import { api, dateTime } from '@/lib/api';
import type { Config, Workspace } from '@/lib/contracts';
import { Badge, Modal, SectionTitle, Spinner } from './ui';
export function DataSources({
  workspace,
  config,
  onRefresh,
  onError,
}: {
  workspace: Workspace;
  config: Config;
  onRefresh: () => Promise<void>;
  onError: (s: string) => void;
}) {
  const [upload, setUpload] = useState(false),
    [busy, setBusy] = useState(false),
    [localError, setLocalError] = useState('');
  const d = workspace.dataset;
  async function action(path: string) {
    setBusy(true);
    try {
      await api(path, 'POST');
      await onRefresh();
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function importData(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    setBusy(true);
    setLocalError('');
    try {
      await api('/datasets/import', 'POST', form);
      await onRefresh();
      setUpload(false);
    } catch (e) {
      setLocalError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <SectionTitle
        eyebrow="DATA SOURCES"
        title="Good decisions start with clean inputs."
        description="Connect your exports, resolve data issues, and keep an immutable record of every version."
      >
        <button className="button primary" onClick={() => setUpload(true)}>
          <Upload size={16} /> Import CSV exports
        </button>
      </SectionTitle>
      <div className={'data-status ' + (d?.status === 'ready' ? 'ready' : '')}>
        <div className="status-icon">
          {d?.status === 'ready' ? <CheckCheck size={27} /> : <Database size={27} />}
        </div>
        <div>
          <h2>
            {d
              ? d.status === 'ready'
                ? 'Your data is ready for decisions.'
                : d.status === 'blocked'
                  ? 'This import needs corrected records.'
                  : 'Review the quarantined records.'
              : 'Bring your business into focus.'}
          </h2>
          <p>
            {d
              ? `${d.name} · Version ${d.version} · ${dateTime(d.created_at)}`
              : 'Import three CSV files, or load a sample to explore the product.'}
          </p>
        </div>
        {d && (
          <Badge tone={d.status === 'ready' ? 'green' : 'amber'}>
            {d.status.replace('_', ' ')}
          </Badge>
        )}
      </div>
      <div className="source-grid">
        {['orders', 'refunds', 'costs'].map((kind) => {
          const f = d?.files.find((x) => x.kind === kind);
          return (
            <section className="card source-card" key={kind}>
              <div className="source-icon">
                <FileSpreadsheet size={24} />
              </div>
              <h2>
                {kind === 'costs' ? 'Fulfilment costs' : kind[0].toUpperCase() + kind.slice(1)}
              </h2>
              <p>
                {kind === 'orders'
                  ? 'Line items, quantities, prices, discounts.'
                  : kind === 'refunds'
                    ? 'Refund amounts and recovered product costs.'
                    : 'Product and shipping costs per order line.'}
              </p>
              <strong>
                {f ? f.rows.toLocaleString('en-IN') : '—'} <span>records</span>
              </strong>
              {f && (
                <div className="hash-line" title={f.hash}>
                  SOURCE SHA-256 <code>{f.hash.slice(0, 16)}…</code>
                </div>
              )}
              <a
                className="text-button"
                href={f ? `/api/datasets/${d!.id}/export/${kind}` : `/api/templates/${kind}`}
              >
                <Download size={14} />
                {f ? 'Export current data' : 'Download example CSV'}
              </a>
            </section>
          );
        })}
      </div>
      {d && d.issues.length > 0 && (
        <section className="card quality-card">
          <div className="card-heading">
            <div>
              <h2>
                <AlertTriangle size={18} /> Data quality review
              </h2>
              <p>
                {d.issues.length} issue{d.issues.length !== 1 ? 's' : ''} detected. Duplicates are
                never silently counted twice.
              </p>
            </div>
            {d.status === 'needs_review' && (
              <button
                className="button primary"
                disabled={busy}
                onClick={() => action(`/datasets/${d.id}/acknowledge`)}
              >
                {busy ? <Spinner /> : <CheckCheck size={16} />} Acknowledge quarantine
              </button>
            )}
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Severity</th>
                  <th>Source</th>
                  <th>Record</th>
                  <th>What happened</th>
                </tr>
              </thead>
              <tbody>
                {d.issues.map((issue, i) => (
                  <tr key={i}>
                    <td>
                      <Badge tone={issue.severity === 'error' ? 'red' : 'amber'}>
                        {issue.severity}
                      </Badge>
                    </td>
                    <td>
                      {issue.file} · row {issue.row || 'multiple'}
                    </td>
                    <td>
                      <code>{issue.record_id}</code>
                    </td>
                    <td>{issue.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {d.status === 'ready' && (
            <p className="quality-note">
              <CheckCheck size={15} /> Quarantine acknowledged. Issue history remains available.
            </p>
          )}
        </section>
      )}
      <div className="lower-grid">
        <section className="card">
          <div className="card-heading">
            <div>
              <h2>
                <History size={18} /> Data version history
              </h2>
              <p>Switching versions invalidates existing approvals.</p>
            </div>
          </div>
          {workspace.versions.length ? (
            <div className="version-list">
              {workspace.versions.map((v) => (
                <div key={v.id}>
                  <span className="version-number">v{v.version}</span>
                  <div>
                    <strong>{v.name}</strong>
                    <small>
                      {dateTime(v.created_at)} · {v.content_hash.slice(0, 12)}
                    </small>
                  </div>
                  {v.id === d?.id ? (
                    <Badge tone="green">Active</Badge>
                  ) : (
                    <button
                      className="button secondary small"
                      disabled={busy || v.status !== 'ready'}
                      onClick={() => action(`/datasets/${v.id}/activate`)}
                    >
                      Activate
                    </button>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="padded muted">Your first import creates version 1.</p>
          )}
        </section>
        <section className="card sample-card">
          <FlaskConical size={24} />
          <h2>Explore a realistic data-quality problem.</h2>
          <p>
            Load a synthetic store with two months of orders. The quality challenge adds an
            identical refund twice so you can inspect the quarantine and acknowledge it.
          </p>
          <div className="sample-buttons">
            <button
              className="button secondary"
              disabled={busy}
              onClick={() => action('/datasets/sample')}
            >
              {busy ? <Spinner /> : <Database size={16} />} Load clean sample
            </button>
            <button
              className="button secondary"
              disabled={busy}
              onClick={() => action('/datasets/sample?quality_challenge=true')}
            >
              <AlertTriangle size={16} /> Load quality challenge
            </button>
          </div>
          <p className="micro">
            Creates a new active version and marks earlier memos stale. Previous versions remain
            available.
          </p>
        </section>
      </div>
      {upload && (
        <Modal title="Import business exports" onClose={() => !busy && setUpload(false)}>
          <form onSubmit={importData} className="import-form">
            <p>
              Upload a matched set of UTF-8 CSVs. All amounts must be INR with at most two decimal
              places. Costs and discounts are totals per line.
            </p>
            <label>
              Data version name
              <input
                name="name"
                placeholder="September business exports"
                required
                minLength={2}
                maxLength={80}
              />
            </label>
            {['orders', 'refunds', 'costs'].map((kind) => (
              <label className="file-field" key={kind}>
                <span>
                  <FileSpreadsheet size={17} />
                  {kind}.csv<a href={'/api/templates/' + kind}>Download example</a>
                </span>
                <input type="file" name={kind} accept=".csv,text/csv" required />
              </label>
            ))}
            <p className="micro">
              Up to {config.max_upload_mb} MB and {config.max_rows.toLocaleString()} rows per file.
              Use a header-only refunds file when there are no refunds. Refunds are attributed to
              the original order month.
            </p>
            {localError && (
              <div className="notice danger" role="alert">
                {localError}
              </div>
            )}
            <button className="button primary" disabled={busy}>
              {busy ? <Spinner /> : <ArrowRight size={17} />} Validate and import
            </button>
          </form>
        </Modal>
      )}
    </>
  );
}
