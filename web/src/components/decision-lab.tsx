'use client';
import { useEffect, useState } from 'react';
import { ArrowRight, Check, GitBranch, Save, SlidersHorizontal } from 'lucide-react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { api, compact, rupees } from '@/lib/api';
import type { Dataset, Params, Simulation, Workspace } from '@/lib/contracts';
import { Badge, SectionTitle, Spinner } from './ui';
const defaults: Params = {
  discount_reduction: 10,
  demand_drop: 8,
  max_demand_drop: 12,
  shipping_saving: 5,
  extra_return_cost: 4,
  implementation_cost: 0,
};
export function DecisionLab({
  workspace,
  onSaved,
  onMemo,
  onError,
}: {
  workspace: Workspace;
  onSaved: () => Promise<void>;
  onMemo: () => void;
  onError: (s: string) => void;
}) {
  const dataset = workspace.dataset as Dataset;
  const [params, setParams] = useState<Params>(() => ({
    ...defaults,
    discount_reduction: Math.min(
      10,
      Math.floor(dataset.summary.current.discount / dataset.summary.current.orders / 100),
    ),
    shipping_saving: Math.min(
      5,
      Math.floor(dataset.summary.current.shipping / dataset.summary.current.orders / 100),
    ),
    ...Object.fromEntries(Object.entries(workspace.scenario).map(([k, v]) => [k, Number(v)])),
  }));
  const [result, setResult] = useState<Simulation | null>(null),
    [busy, setBusy] = useState(false),
    [calculating, setCalculating] = useState(false),
    [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    setCalculating(true);
    const timer = setTimeout(
      () =>
        api<Simulation>('/scenario/preview', 'POST', params, controller.signal)
          .then((r) => {
            setResult(r);
            setError('');
          })
          .catch((e) => {
            if (!controller.signal.aborted) {
              setError(e.message);
              setResult(null);
            }
          })
          .finally(() => {
            if (!controller.signal.aborted) setCalculating(false);
          }),
      300,
    );
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [params]);
  const saved = result?.scenario_hash === workspace.scenario_hash;
  async function save(memo = false) {
    setBusy(true);
    try {
      await api('/scenario', 'PUT', params);
      if (memo) await api('/memos', 'POST');
      await onSaved();
      if (memo) onMemo();
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function input(key: keyof Params, label: string, unit: string, max: number) {
    return (
      <label className="scenario-input">
        {label}
        <div>
          <input
            aria-label={label}
            type="number"
            min={0}
            max={max}
            step="0.01"
            value={params[key]}
            onChange={(e) => setParams((p) => ({ ...p, [key]: Number(e.target.value) }))}
          />
          <span>{unit}</span>
        </div>
      </label>
    );
  }
  return (
    <>
      <SectionTitle
        eyebrow="DECISION LAB"
        title="A better answer survives a what-if."
        description="Compare actions under explicit uncertainty. Change the assumptions and see when the recommendation changes."
      />
      <div className="decision-grid">
        <section className="card assumptions-card">
          <div className="card-heading">
            <h2>
              <SlidersHorizontal size={18} /> Your assumptions
            </h2>
            <Badge>v{dataset.version}</Badge>
          </div>
          <div className="assumption-group">
            <span className="eyebrow">OPTION A · TIGHTEN DISCOUNTS</span>
            {input('discount_reduction', 'Reduce discount per order', '₹', 1000)}
            {input('demand_drop', 'Selected demand loss', '%', 50)}
            {input('max_demand_drop', 'Maximum demand loss', '%', 60)}
            <p className="micro">
              Demand loss ranges from 0% to your maximum. This range is a judgment, not a
              prediction.
            </p>
          </div>
          <div className="assumption-group">
            <span className="eyebrow">OPTION B · REDUCE SHIPPING COST</span>
            {input('shipping_saving', 'Shipping saving per order', '₹', 1000)}
            {input('extra_return_cost', 'Maximum extra return cost per order', '₹', 1000)}
            <p className="micro">
              Volume stays constant. Additional return cost ranges from ₹0 to this maximum.
            </p>
          </div>
          <div className="assumption-group">
            {input('implementation_cost', 'One-time implementation cost', '₹', 10000000)}
          </div>
          <div className="assumption-footer">
            <span>
              {saved ? (
                <>
                  <Check size={14} /> Saved assumptions
                </>
              ) : (
                <>Unsaved changes</>
              )}
            </span>
            <button
              className="button secondary"
              disabled={busy || calculating || !result || saved}
              onClick={() => save()}
            >
              {busy ? <Spinner /> : <Save size={15} />} Save
            </button>
          </div>
        </section>
        <div className="decision-output">
          {error && (
            <div className="notice danger" role="alert">
              {error}
            </div>
          )}
          {result && (
            <>
              <div className="recommendation">
                <div className="recommendation-icon">
                  <GitBranch size={24} />
                </div>
                <div>
                  <span className="eyebrow">STRONGEST WORST-CASE CONTRIBUTION</span>
                  <h2>{result.alternatives[0].label}</h2>
                  <p>
                    {rupees(result.alternatives[0].worst)} at the downside bound ·{' '}
                    {rupees(result.alternatives[0].worst - result.baseline)} vs current policy
                  </p>
                </div>
                {calculating ? <Spinner /> : <Badge tone="green">Calculated</Badge>}
              </div>
              <section className="card sensitivity">
                <div className="card-heading">
                  <div>
                    <h2>Where does the decision break?</h2>
                    <p>Contribution margin as demand falls</p>
                  </div>
                  <div className="break-even">
                    <strong>
                      {result.break_even_pct === null
                        ? 'N/A'
                        : result.break_even_pct.toFixed(2) + '%'}
                    </strong>
                    <span>discount break-even</span>
                  </div>
                </div>
                <div className="chart" role="img" aria-label="Demand sensitivity chart">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={result.curve}
                      margin={{ top: 12, right: 22, bottom: 8, left: 3 }}
                    >
                      <CartesianGrid vertical={false} stroke="#e8ede8" />
                      <XAxis
                        type="number"
                        domain={[0, params.max_demand_drop]}
                        dataKey="demand_drop"
                        tickFormatter={(v) => Number(v).toFixed(0) + '%'}
                        tickLine={false}
                        axisLine={false}
                        tick={{ fontSize: 11 }}
                        minTickGap={25}
                      />
                      <YAxis
                        tickFormatter={(v) => '₹' + compact(Number(v))}
                        width={63}
                        tickLine={false}
                        axisLine={false}
                        domain={['auto', 'auto']}
                        tick={{ fontSize: 11 }}
                      />
                      <Tooltip
                        formatter={(v) => rupees(Number(v))}
                        labelFormatter={(v) => `${Number(v).toFixed(1)}% demand loss`}
                      />
                      <Line
                        isAnimationActive={false}
                        name="Tighten discounts"
                        type="linear"
                        dataKey="discount"
                        stroke="#ac7336"
                        dot={false}
                        strokeWidth={2.5}
                      />
                      <Line
                        isAnimationActive={false}
                        name="Shipping downside"
                        dataKey="shipping"
                        stroke="#257259"
                        dot={false}
                        strokeWidth={2.5}
                      />
                      <Line
                        isAnimationActive={false}
                        name="Current policy"
                        dataKey="baseline"
                        stroke="#a0a7a0"
                        strokeDasharray="5 4"
                        dot={false}
                      />
                      <ReferenceLine
                        x={params.demand_drop}
                        stroke="#7b897f"
                        strokeDasharray="3 3"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <div className="chart-legend bottom">
                  <span>
                    <i className="legend-dot amber-bg" />
                    Tighten discounts
                  </span>
                  <span>
                    <i className="legend-dot" />
                    Shipping downside
                  </span>
                  <span>
                    <i className="legend-dot grey-bg" />
                    Current policy
                  </span>
                </div>
              </section>
              <section className="card">
                <div className="card-heading">
                  <div>
                    <h2>Compare the full range.</h2>
                    <p>Ranked by the highest minimum contribution</p>
                  </div>
                  <Badge>Scenario estimates</Badge>
                </div>
                <div className="table-wrap">
                  <table className="alternatives">
                    <thead>
                      <tr>
                        <th>Action</th>
                        <th>Downside</th>
                        <th>Upside</th>
                        <th>Selected case</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.alternatives.map((a, i) => (
                        <tr key={a.id} className={i === 0 ? 'recommended' : ''}>
                          <td>
                            <strong>{a.label}</strong>
                            {i === 0 && <small>Recommended within these bounds</small>}
                          </td>
                          <td>{rupees(a.worst)}</td>
                          <td>{rupees(a.best)}</td>
                          <td>{rupees(a.selected)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="decision-next">
                  <span>
                    Baseline: {rupees(result.baseline)} · {result.orders} orders
                  </span>
                  <button
                    className="button primary"
                    disabled={busy || calculating}
                    onClick={() => save(true)}
                  >
                    {busy ? <Spinner /> : <ArrowRight size={16} />} Create decision memo
                  </button>
                </div>
              </section>
              <details className="card model-notes">
                <summary>Read the model assumptions before approving</summary>
                <ul>
                  {result.assumptions.map((a) => (
                    <li key={a}>{a}</li>
                  ))}
                </ul>
                <p>
                  The selected shipping case uses the downside return-cost bound. No changes are
                  sent to a store or fulfilment provider.
                </p>
              </details>
            </>
          )}
          {!result && !error && (
            <div className="loading-inline">
              <Spinner /> Calculating scenarios
            </div>
          )}
        </div>
      </div>
    </>
  );
}
