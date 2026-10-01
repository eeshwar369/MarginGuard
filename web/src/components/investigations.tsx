'use client';
import { useEffect, useState } from 'react';
import { ArrowRight, Check, Clock3, RotateCcw, Send, Sparkles } from 'lucide-react';
import { api, dateTime } from '@/lib/api';
import type { Config, Run } from '@/lib/contracts';
import { Badge, Empty, SectionTitle, Spinner } from './ui';
import { Findings } from './overview';
export function Investigations({
  config,
  onEvidence,
  onError,
}: {
  config: Config;
  onEvidence: (id: string, dataset?: string) => void;
  onError: (message: string) => void;
}) {
  const [runs, setRuns] = useState<Run[]>([]),
    [selected, setSelected] = useState<Run | null>(null),
    [question, setQuestion] = useState('Why did contribution margin fall while revenue grew?'),
    [busy, setBusy] = useState(false),
    [loading, setLoading] = useState(true),
    [useAi, setUseAi] = useState(config.ai_available),
    [consent, setConsent] = useState(false);
  useEffect(() => {
    let alive = true;
    api<Run[]>('/investigations')
      .then((x) => {
        if (alive) {
          setRuns(x);
          setSelected(x[0] ?? null);
        }
      })
      .catch((e) => onError(e.message))
      .finally(() => setLoading(false));
    return () => {
      alive = false;
    };
  }, [onError]);
  useEffect(() => {
    if (!selected || !['running', 'queued'].includes(selected.status)) return;
    let alive = true;
    const timer = setInterval(
      () =>
        api<Run>('/investigations/' + selected.id)
          .then((r) => {
            if (alive) {
              setSelected(r);
              setRuns((xs) => xs.map((x) => (x.id === r.id ? r : x)));
            }
          })
          .catch((e) => {
            if (alive) onError(e.message);
          }),
      1500,
    );
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [selected, onError]);
  async function start(resume = false) {
    setBusy(true);
    try {
      const r = await api<{ id: string }>(
        resume ? `/investigations/${selected?.id}/resume` : '/investigations',
        'POST',
        resume ? undefined : { question, use_ai: useAi, consent },
      );
      const full = await api<Run>('/investigations/' + r.id);
      setSelected(full);
      setRuns((xs) => [full, ...xs.filter((x) => x.id !== full.id)]);
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <SectionTitle
        eyebrow="INVESTIGATIONS"
        title="A question. An evidence trail."
        description="Investigate the numbers, challenge a hypothesis, and inspect the records behind the answer."
      />
      <div className="investigation-grid">
        <div>
          <section className="card question-card">
            <div className="card-heading">
              <h2>
                <Sparkles size={18} /> Ask about your business
              </h2>
              <Badge tone={config.ai_available ? 'green' : 'neutral'}>
                {config.ai_available ? 'AI planning available' : 'Verified analysis'}
              </Badge>
            </div>
            <label className="sr-only" htmlFor="question">
              Business question
            </label>
            <textarea
              id="question"
              rows={3}
              maxLength={1000}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="What changed in our margins?"
            />
            <div className="question-chips">
              {['Why did margin fall?', 'Did discounts decrease?', 'Which orders lost money?'].map(
                (x) => (
                  <button key={x} onClick={() => setQuestion(x)}>
                    {x}
                    <ArrowRight size={12} />
                  </button>
                ),
              )}
            </div>
            {config.ai_available ? (
              <div className="consent-box">
                <label className="check-label">
                  <input
                    type="checkbox"
                    checked={useAi}
                    onChange={(e) => setUseAi(e.target.checked)}
                  />{' '}
                  Use AI to choose analyses
                </label>
                {useAi && (
                  <label className="check-label">
                    <input
                      type="checkbox"
                      checked={consent}
                      onChange={(e) => setConsent(e.target.checked)}
                    />{' '}
                    Send my question and numeric summaries to Google Gemini. CSV text stays on this
                    server.
                  </label>
                )}
              </div>
            ) : (
              <p className="micro">
                AI is not configured on this deployment. Questions use a deterministic analysis
                plan; all financial values are calculated from your data.
              </p>
            )}
            <div className="question-bottom">
              <span>Frozen data version · Read-only analysis</span>
              <button
                className="button primary"
                disabled={
                  busy ||
                  question.trim().length < 5 ||
                  (useAi && !consent) ||
                  (!!selected && ['running', 'queued'].includes(selected.status))
                }
                onClick={() => start()}
              >
                {busy ? <Spinner /> : <Send size={15} />} Run investigation
              </button>
            </div>
          </section>
          {loading ? (
            <div className="loading-inline">
              <Spinner /> Loading investigations
            </div>
          ) : selected ? (
            <section className="card investigation-result">
              <div className="card-heading">
                <div>
                  <span className="eyebrow">
                    {selected.mode === 'ai'
                      ? 'AI-PLANNED INVESTIGATION'
                      : selected.mode === 'fallback'
                        ? 'VERIFIED FALLBACK'
                        : 'VERIFIED INVESTIGATION'}
                  </span>
                  <h2>{selected.question}</h2>
                </div>
                <Badge
                  tone={
                    selected.status === 'complete'
                      ? 'green'
                      : selected.status === 'interrupted'
                        ? 'amber'
                        : 'neutral'
                  }
                >
                  {selected.status}
                </Badge>
              </div>
              <div className="run-stages">
                {['Validated', 'Planned', 'Investigated', 'Verified'].map((step, i) => (
                  <div
                    key={step}
                    className={selected.events.some((x) => x.stage === step) ? 'done' : ''}
                  >
                    <span>
                      {selected.events.some((x) => x.stage === step) ? <Check size={13} /> : i + 1}
                    </span>
                    {step}
                  </div>
                ))}
              </div>
              {selected.status === 'interrupted' && (
                <div className="notice amber">
                  The run was interrupted. Completed stages were saved.
                  <button className="button secondary" onClick={() => start(true)} disabled={busy}>
                    <RotateCcw size={15} /> Resume run
                  </button>
                </div>
              )}
              {selected.result ? (
                <>
                  <div className="answer">
                    <p>{selected.result.answer}</p>
                    {selected.result.warning && (
                      <div className="notice amber">{selected.result.warning}</div>
                    )}
                    {selected.result.unresolved && (
                      <Badge tone="amber">Additional information needed</Badge>
                    )}
                  </div>
                  <Findings
                    findings={selected.result.findings}
                    onEvidence={(id) => onEvidence(id, selected.dataset_id)}
                  />
                  <div className="result-footer">
                    <span>{selected.result.scope_note}</span>
                    <small>
                      {selected.result.elapsed_ms} ms · {selected.result.model_tokens} model tokens
                    </small>
                  </div>
                </>
              ) : (
                selected.status !== 'interrupted' && (
                  <div className="loading-inline">
                    <Spinner /> {selected.stage}…
                  </div>
                )
              )}
              <details className="trace">
                <summary>Execution trace · {selected.events.length} checkpoints</summary>
                {selected.events.map((e) => (
                  <div key={e.stage}>
                    <Check size={14} />
                    <span>
                      <strong>{e.stage}</strong>
                      {e.message}
                    </span>
                    <small>{dateTime(e.at)}</small>
                  </div>
                ))}
              </details>
            </section>
          ) : (
            <Empty
              title="Your first investigation starts here."
              description="Ask a question above. Every completed run stays linked to the exact data version it used."
            />
          )}
        </div>
        <aside className="card run-history">
          <div className="card-heading">
            <h2>Recent investigations</h2>
            <Clock3 size={17} />
          </div>
          {runs.length ? (
            runs.map((r) => (
              <button
                key={r.id}
                className={selected?.id === r.id ? 'selected' : ''}
                onClick={() => setSelected(r)}
              >
                <strong>{r.question}</strong>
                <span>
                  {dateTime(r.created_at)} · {r.status}
                </span>
              </button>
            ))
          ) : (
            <p className="micro">Your saved investigations will appear here.</p>
          )}
          <div className="aside-note">
            <strong>What can I investigate?</strong>
            <p>Margins, discounts, refunds, product costs, shipping, and loss-making orders.</p>
            <p>Demand causality and future sales need evidence beyond these exports.</p>
          </div>
        </aside>
      </div>
    </>
  );
}
