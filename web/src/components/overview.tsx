'use client';
import { ArrowDownRight, ArrowRight, ArrowUpRight, CheckCheck, Fingerprint } from 'lucide-react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { compact, periodName, rupees } from '@/lib/api';
import type { Dataset, Finding } from '@/lib/contracts';
import { Badge, SectionTitle } from './ui';
const labels: Record<string, string> = {
  gross: 'Gross sales',
  discount: 'Discounts',
  refunds: 'Refunds',
  product_cost: 'Net product costs',
  shipping: 'Shipping',
};
export function Findings({
  findings,
  onEvidence,
}: {
  findings: Finding[];
  onEvidence: (id: string) => void;
}) {
  return (
    <div className="findings">
      {findings.map((f, i) => (
        <button
          key={f.id}
          className="finding"
          onClick={() => onEvidence(f.id)}
          disabled={!f.evidence}
        >
          <span className={'finding-no ' + (f.status === 'contradicted' ? 'amber' : '')}>
            {String(i + 1).padStart(2, '0')}
          </span>
          <span className="finding-body">
            <strong>{f.title}</strong>
            <span>
              {f.count !== undefined
                ? f.count === 0
                  ? 'No negative order lines in this period'
                  : `${f.count} order lines need a closer look`
                : f.per_order_change !== undefined
                  ? `${rupees(f.per_order_change, 2)} change per order`
                  : 'Comparison period required'}
            </span>
            {f.hypothesis && (
              <small>
                Hypothesis: {f.hypothesis} · {f.status}
              </small>
            )}
          </span>
          <span className="finding-impact">
            {f.count !== undefined ? (
              <Badge tone={f.count === 0 ? 'green' : 'amber'}>
                {f.count === 0 ? 'Clear' : 'Review'}
              </Badge>
            ) : (
              <strong className={f.amount < 0 ? 'negative' : 'positive'}>{rupees(f.amount)}</strong>
            )}
            <small>{f.count !== undefined ? 'Inspect records' : 'margin contribution'}</small>
          </span>
          <ArrowUpRight size={16} />
        </button>
      ))}
    </div>
  );
}
export function Overview({
  dataset,
  onEvidence,
  navigate,
}: {
  dataset: Dataset;
  onEvidence: (id: string) => void;
  navigate: (page: string) => void;
}) {
  const s = dataset.summary,
    c = s.current,
    p = s.previous;
  const change = (key: 'revenue' | 'margin' | 'orders') =>
    p && p[key] ? ((c[key] - p[key]) / Math.abs(p[key])) * 100 : null;
  const metrics = [
    {
      label: 'Net revenue',
      value: rupees(c.revenue),
      delta: change('revenue'),
      note: 'After discounts and refunds',
    },
    {
      label: 'Contribution margin',
      value: rupees(c.margin),
      delta: change('margin'),
      note: `${c.margin_pct}% of net revenue`,
    },
    {
      label: 'Orders fulfilled',
      value: c.orders.toLocaleString('en-IN'),
      delta: change('orders'),
      note: `${c.units} units across ${s.products.length} products`,
    },
    {
      label: 'Refund rate',
      value: c.refund_rate + '%',
      delta: null,
      note: p ? `${p.refund_rate}% in the previous period` : 'By distinct refunded orders',
    },
  ];
  return (
    <>
      <SectionTitle
        eyebrow="BUSINESS HEALTH"
        title="See the story behind your margin."
        description={`${periodName(c.period)}${p ? ' compared with ' + periodName(p.period) : ''}. Every number reconciles to your source data.`}
      >
        <button className="button primary" onClick={() => navigate('Investigations')}>
          Investigate a question <ArrowRight size={16} />
        </button>
      </SectionTitle>
      <div className="metrics">
        {metrics.map((m) => (
          <div className="metric" key={m.label}>
            <span className="metric-label">{m.label}</span>
            <div className="metric-value">{m.value}</div>
            <div className="metric-bottom">
              {m.delta !== null && (
                <span className={'delta ' + (m.delta >= 0 ? 'positive' : 'negative')}>
                  {m.delta >= 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}{' '}
                  {Math.abs(m.delta).toFixed(1)}%
                </span>
              )}
              <small>{m.note}</small>
            </div>
          </div>
        ))}
      </div>
      <div className="overview-grid">
        <section className="card chart-card">
          <div className="card-heading">
            <div>
              <h2>Revenue is only half the story.</h2>
              <p>Daily net revenue and contribution margin</p>
            </div>
            <div className="chart-legend">
              <span>
                <i className="legend-dot light" />
                Revenue
              </span>
              <span>
                <i className="legend-dot" />
                Margin
              </span>
            </div>
          </div>
          <div className="chart" role="img" aria-label="Daily revenue and margin chart">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={s.daily} margin={{ top: 15, right: 10, bottom: 0, left: 0 }}>
                <defs>
                  <linearGradient id="marginFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#24755a" stopOpacity={0.18} />
                    <stop offset="100%" stopColor="#24755a" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid vertical={false} stroke="#e9eee9" />
                <XAxis
                  dataKey="date"
                  tickFormatter={(x) => String(x).slice(8)}
                  tickLine={false}
                  axisLine={false}
                  minTickGap={28}
                  tick={{ fontSize: 11, fill: '#7e8880' }}
                />
                <YAxis
                  tickFormatter={(x) => '₹' + compact(Number(x))}
                  tickLine={false}
                  axisLine={false}
                  width={58}
                  tick={{ fontSize: 11, fill: '#7e8880' }}
                />
                <Tooltip
                  formatter={(v) => rupees(Number(v))}
                  labelFormatter={(x) => String(x)}
                  contentStyle={{ border: '1px solid #dce3dc', borderRadius: 10, fontSize: 12 }}
                />
                <Area
                  isAnimationActive={false}
                  name="Revenue"
                  type="monotone"
                  dataKey="revenue"
                  stroke="#a7bca6"
                  strokeWidth={2}
                  fill="transparent"
                />
                <Area
                  isAnimationActive={false}
                  name="Margin"
                  type="monotone"
                  dataKey="margin"
                  stroke="#24755a"
                  strokeWidth={2.5}
                  fill="url(#marginFill)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="chart-footer">
            <CheckCheck size={15} /> Reconciliation difference:{' '}
            {rupees(s.reconciliation_residual, 2)}
            <span>Fixed overhead and tax excluded</span>
          </div>
        </section>
        <section className="card bridge-card">
          <div className="card-heading">
            <div>
              <h2>What moved the margin?</h2>
              <p>Exact accounting bridge between periods</p>
            </div>
          </div>
          {p ? (
            <>
              <div className="bridge-end">
                <span>Previous contribution</span>
                <strong>{rupees(p.margin)}</strong>
              </div>
              {s.bridge.map((b) => (
                <div className="bridge-row" key={b.key}>
                  <span>{labels[b.key]}</span>
                  <div className="bridge-track">
                    <i
                      style={{
                        width:
                          Math.max(
                            3,
                            (Math.abs(b.value) /
                              Math.max(...s.bridge.map((x) => Math.abs(x.value)))) *
                              100,
                          ) + '%',
                      }}
                      className={b.value >= 0 ? 'positive-bg' : 'negative-bg'}
                    />
                  </div>
                  <strong className={b.value >= 0 ? 'positive' : 'negative'}>
                    {b.value > 0 ? '+' : ''}
                    {rupees(b.value)}
                  </strong>
                </div>
              ))}
              <div className="bridge-end current">
                <span>Current contribution</span>
                <strong>{rupees(c.margin)}</strong>
              </div>
              <p className="micro">
                Contributions explain the arithmetic change, not the causal effect of a policy.
              </p>
            </>
          ) : (
            <p className="micro">Add a second month to compare changes.</p>
          )}
        </section>
      </div>
      <div className="lower-grid">
        <section className="card">
          <div className="card-heading">
            <div>
              <h2>Follow the evidence.</h2>
              <p>Start with the largest changes</p>
            </div>
            <Fingerprint size={21} className="muted" />
          </div>
          <Findings findings={s.findings.slice(0, 4)} onEvidence={onEvidence} />
        </section>
        <section className="card">
          <div className="card-heading">
            <div>
              <h2>Product contribution</h2>
              <p>Revenue doesn’t always mean profit</p>
            </div>
            <Badge>{s.products.length} SKUs</Badge>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Margin</th>
                  <th>Rate</th>
                </tr>
              </thead>
              <tbody>
                {s.products.map((p) => (
                  <tr key={p.sku}>
                    <td>
                      <strong>{p.name}</strong>
                      <small>
                        {p.sku} · {p.orders} orders
                      </small>
                    </td>
                    <td>{rupees(p.margin)}</td>
                    <td>
                      <span className={'rate ' + (p.margin < 0 ? 'negative' : '')}>
                        {p.margin_pct}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button className="card-link" onClick={() => navigate('Decision lab')}>
            Turn these findings into a decision <ArrowRight size={16} />
          </button>
        </section>
      </div>
    </>
  );
}
