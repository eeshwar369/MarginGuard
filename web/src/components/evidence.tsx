'use client';
import { useEffect, useState, type FormEvent } from 'react';
import { ArrowLeft, ArrowRight, Fingerprint, Search } from 'lucide-react';
import { api, rupees } from '@/lib/api';
import type { Evidence } from '@/lib/contracts';
import { Badge, Modal, Spinner } from './ui';
export function EvidenceDrawer({
  id,
  datasetId,
  activeId,
  onClose,
  onChanged,
}: {
  id: string;
  datasetId: string;
  activeId?: string;
  onClose: () => void;
  onChanged: () => Promise<void>;
}) {
  const [data, setData] = useState<Evidence | null>(null),
    [offset, setOffset] = useState(0),
    [search, setSearch] = useState(''),
    [query, setQuery] = useState(''),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false),
    [loading, setLoading] = useState(true),
    [correction, setCorrection] = useState(false);
  useEffect(() => {
    const control = new AbortController();
    setLoading(true);
    api<Evidence>(
      `/evidence/${id}?dataset_id=${datasetId}&offset=${offset}&limit=20&search=${encodeURIComponent(query)}`,
      'GET',
      undefined,
      control.signal,
    )
      .then((x) => {
        setData(x);
        setError('');
      })
      .catch((e) => {
        if (!control.signal.aborted) setError(e.message);
      })
      .finally(() => {
        if (!control.signal.aborted) setLoading(false);
      });
    return () => control.abort();
  }, [id, datasetId, offset, query]);
  async function correct(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError('');
    const fields = Object.fromEntries(new FormData(e.currentTarget));
    try {
      await api('/datasets/correct-cost', 'POST', { ...fields, expected_hash: data?.content_hash });
      await onChanged();
      onClose();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title="Evidence explorer" onClose={onClose} wide>
      {error && (
        <div role="alert" className="notice danger">
          {error}
        </div>
      )}
      {data && (
        <>
          <div className="evidence-intro">
            <div>
              <div className="eyebrow">
                <Fingerprint size={14} /> SOURCE-VERIFIED · VERSION {data.version}
              </div>
              <h3>{data.finding.title}</h3>
              <p>{data.finding.explanation}</p>
            </div>
            <Badge tone="green">{data.finding.status}</Badge>
          </div>
          {data.finding.evidence?.before !== undefined && (
            <div className="evidence-math">
              <div>
                <small>Previous period</small>
                <strong>{rupees(data.finding.evidence.before, 2)}</strong>
              </div>
              <ArrowRight size={19} />
              <div>
                <small>Current period</small>
                <strong>{rupees(data.finding.evidence.after!, 2)}</strong>
              </div>
              <div>
                <small>Difference</small>
                <strong>{rupees(data.finding.evidence.delta!, 2)}</strong>
              </div>
            </div>
          )}
          <div className="evidence-tools">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                setQuery(search);
                setOffset(0);
              }}
              className="search"
            >
              <Search size={16} />
              <input
                aria-label="Search source rows"
                placeholder="Search line ID or SKU"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <button className="text-button">Search</button>
            </form>
            <span>{data.total} matching ledger rows</span>
          </div>
          <p className="micro evidence-note">
            Money shown in INR. Source row numbers refer to the original CSV, including its header.
            Product cost is net of recovered cost.
          </p>
          <div className="table-wrap evidence-table" aria-busy={loading}>
            <table>
              <thead>
                <tr>
                  <th>Order line</th>
                  <th>SKU</th>
                  <th>Net revenue</th>
                  <th>Product cost</th>
                  <th>Shipping</th>
                  <th>Margin</th>
                  <th>CSV rows</th>
                </tr>
              </thead>
              <tbody>
                {data.rows.map((r) => (
                  <tr key={r.line_id}>
                    <td>
                      <strong>{r.line_id}</strong>
                      <small>{r.date}</small>
                    </td>
                    <td>{r.sku}</td>
                    <td>{rupees(r.revenue, 2)}</td>
                    <td>{rupees(r.product_cost, 2)}</td>
                    <td>{rupees(r.shipping, 2)}</td>
                    <td className={r.margin < 0 ? 'negative' : 'positive'}>
                      {rupees(r.margin, 2)}
                    </td>
                    <td>
                      <small>
                        Orders {r.order_source_row}
                        <br />
                        Costs {r.cost_source_row}
                      </small>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {data.rows.length === 0 && <p className="padded">No matching rows.</p>}
          </div>
          <div className="pagination">
            <span>
              {loading
                ? 'Loading…'
                : `Showing ${data.total ? offset + 1 : 0}–${Math.min(offset + 20, data.total)} of ${data.total}`}
            </span>
            <button
              className="button secondary small"
              disabled={offset === 0 || loading}
              onClick={() => setOffset((x) => Math.max(0, x - 20))}
            >
              <ArrowLeft size={14} /> Previous
            </button>
            <button
              className="button secondary small"
              disabled={offset + 20 >= data.total || loading}
              onClick={() => setOffset((x) => x + 20)}
            >
              Next <ArrowRight size={14} />
            </button>
          </div>
          <details className="trace">
            <summary>Inspect the calculation and source fingerprints</summary>
            <p>
              <strong>Finding formula:</strong> <code>{data.finding.evidence?.formula}</code>
            </p>
            <pre>{data.finding.evidence?.query}</pre>
            <p>Ledger construction: refunds are aggregated before joining order lines.</p>
            <pre>{data.ledger_query}</pre>
            {Object.entries(data.source_hashes).map(([k, v]) => (
              <p key={k} className="hash-detail">
                <strong>{k}</strong>
                <code>{v}</code>
              </p>
            ))}
            <p className="hash-detail">
              <strong>Data version</strong>
              <code>{data.content_hash}</code>
            </p>
          </details>
          {activeId === datasetId && (
            <div className="correction">
              <button className="text-button" onClick={() => setCorrection(!correction)}>
                {correction
                  ? 'Cancel correction'
                  : 'Found an incorrect cost? Create a corrected version'}{' '}
                <ArrowRight size={14} />
              </button>
              {correction && (
                <form onSubmit={correct}>
                  <p>
                    Enter the original total product cost before recoveries. This creates a new
                    version, resets scenario assumptions, and invalidates previous approvals.
                  </p>
                  <div className="correction-grid">
                    <label>
                      Order line ID
                      <input
                        name="line_id"
                        required
                        maxLength={100}
                        placeholder={data.rows[0]?.line_id}
                      />
                    </label>
                    <label>
                      Product cost (₹)
                      <input
                        type="number"
                        name="product_cost"
                        min={0}
                        max={10000000}
                        step="0.01"
                        required
                      />
                    </label>
                    <label>
                      Shipping cost (₹)
                      <input
                        type="number"
                        name="shipping_cost"
                        min={0}
                        max={10000000}
                        step="0.01"
                        required
                      />
                    </label>
                  </div>
                  <label>
                    Reason for correction
                    <input name="reason" minLength={5} maxLength={300} required />
                  </label>
                  <button className="button primary" disabled={busy}>
                    {busy ? <Spinner /> : <ArrowRight size={15} />} Create corrected version
                  </button>
                </form>
              )}
            </div>
          )}
        </>
      )}
      {!data && loading && (
        <div className="loading-inline">
          <Spinner /> Loading source evidence
        </div>
      )}
    </Modal>
  );
}
