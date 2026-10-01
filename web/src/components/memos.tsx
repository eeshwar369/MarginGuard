'use client';
import { useEffect, useState } from 'react';
import { ArrowRight, CheckCheck, Download, FileCheck2, ShieldCheck } from 'lucide-react';
import { api, dateTime, rupees } from '@/lib/api';
import type { Memo } from '@/lib/contracts';
import { Badge, Empty, Modal, SectionTitle, Spinner } from './ui';
export function Memos({
  onError,
  navigate,
}: {
  onError: (s: string) => void;
  navigate: (p: string) => void;
}) {
  const [memos, setMemos] = useState<Memo[]>([]),
    [loading, setLoading] = useState(true),
    [review, setReview] = useState<Memo | null>(null),
    [ack, setAck] = useState(false),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    api<Memo[]>('/memos')
      .then(setMemos)
      .catch((e) => onError(e.message))
      .finally(() => setLoading(false));
  }, [onError]);
  async function approve() {
    if (!review) return;
    setBusy(true);
    try {
      const m = await api<Memo>(`/memos/${review.id}/approve`, 'POST', {
        expected_dataset_hash: review.content.data_hash,
        expected_scenario_hash: review.scenario_hash,
        acknowledged: ack,
      });
      setMemos((xs) => xs.map((x) => (x.id === m.id ? m : x)));
      setReview(null);
    } catch (e) {
      onError((e as Error).message);
      await api<Memo[]>('/memos')
        .then(setMemos)
        .catch(() => undefined);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <SectionTitle
        eyebrow="DECISION MEMOS"
        title="Make the call. Keep the evidence."
        description="A reviewable decision record with assumptions, source fingerprints, and your approval."
      >
        <button className="button primary" onClick={() => navigate('Decision lab')}>
          New decision <ArrowRight size={16} />
        </button>
      </SectionTitle>
      {loading ? (
        <div className="loading-inline">
          <Spinner /> Loading decision records
        </div>
      ) : memos.length ? (
        <div className="memo-list">
          {memos.map((m) => {
            const s = m.content.scenario,
              a = s.alternatives[0];
            return (
              <article className={'card memo-card ' + m.status} key={m.id}>
                <div className="memo-symbol">
                  <FileCheck2 size={24} />
                </div>
                <div className="memo-main">
                  <div className="memo-title">
                    <h2>{a.label}</h2>
                    <Badge
                      tone={
                        m.status === 'approved'
                          ? 'green'
                          : m.status === 'stale'
                            ? 'amber'
                            : 'neutral'
                      }
                    >
                      {m.status}
                    </Badge>
                    {m.content.synthetic && <Badge>Synthetic data</Badge>}
                  </div>
                  <p>
                    Version {m.content.version} · {dateTime(m.created_at)} ·{' '}
                    {m.content.data_hash.slice(0, 12)}
                  </p>
                  <div className="memo-stats">
                    <div>
                      <span>Downside contribution</span>
                      <strong>{rupees(a.worst)}</strong>
                    </div>
                    <div>
                      <span>Upside contribution</span>
                      <strong>{rupees(a.best)}</strong>
                    </div>
                    <div>
                      <span>Compared with baseline</span>
                      <strong>{rupees(a.worst - s.baseline)}</strong>
                    </div>
                  </div>
                  {m.status === 'stale' ? (
                    <div className="memo-state amber">
                      Inputs changed. This record is retained for history and cannot be approved.
                    </div>
                  ) : m.status === 'approved' ? (
                    <div className="memo-state">
                      <ShieldCheck size={15} /> Approved by {m.approved_by} ·{' '}
                      {dateTime(m.approved_at!)}
                    </div>
                  ) : (
                    <div className="memo-state muted">
                      Review the assumptions before approving this decision.
                    </div>
                  )}
                  <div className="memo-actions">
                    <button
                      className="button secondary"
                      onClick={() => {
                        setReview(m);
                        setAck(false);
                      }}
                    >
                      {m.status === 'draft' ? 'Review and approve' : 'View decision record'}
                      <ArrowRight size={15} />
                    </button>
                    <a className="text-button" href={`/api/memos/${m.id}/export?format=pdf`}>
                      <Download size={15} /> PDF
                    </a>
                    <a className="text-button" href={`/api/memos/${m.id}/export?format=json`}>
                      <Download size={15} /> JSON
                    </a>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      ) : (
        <Empty
          title="Your next decision deserves a record."
          description="Compare the options in the decision lab, then create a memo to review and approve."
        >
          <button className="button primary" onClick={() => navigate('Decision lab')}>
            Open decision lab <ArrowRight size={16} />
          </button>
        </Empty>
      )}
      {review && (
        <Modal title="Review decision memo" onClose={() => !busy && setReview(null)}>
          <div className="review-body">
            <Badge tone={review.status === 'stale' ? 'amber' : 'green'}>
              {review.status} · data v{review.content.version}
            </Badge>
            <h3>{review.content.scenario.alternatives[0].label}</h3>
            <p>
              Recommended by maximizing worst-case contribution within the entered bounds. This is a
              scenario estimate, not a guaranteed outcome.
            </p>
            <h4>Assumptions in this decision</h4>
            <dl className="params-list">
              {Object.entries(review.content.scenario.params).map(([k, v]) => (
                <div key={k}>
                  <dt>{k.replaceAll('_', ' ')}</dt>
                  <dd>
                    {Number(v).toLocaleString('en-IN')}
                    {k.includes('demand') ? '%' : ' INR'}
                  </dd>
                </div>
              ))}
            </dl>
            <ul className="assumptions-list">
              {review.content.scenario.assumptions.map((a) => (
                <li key={a}>{a}</li>
              ))}
            </ul>
            <p className="micro">
              Approval records your review. It does not change prices, discounts, or shipping
              providers.
            </p>
            {review.status === 'draft' && (
              <>
                <label className="check-label approval-check">
                  <input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} />{' '}
                  I have reviewed the evidence and accept the assumptions for this exact data
                  version.
                </label>
                <button className="button primary" disabled={!ack || busy} onClick={approve}>
                  {busy ? <Spinner /> : <CheckCheck size={17} />} Approve decision
                </button>
              </>
            )}
            {review.status === 'stale' && (
              <div className="notice amber">
                Create a fresh memo from the current data and assumptions.
              </div>
            )}
          </div>
        </Modal>
      )}
    </>
  );
}
