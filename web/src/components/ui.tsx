'use client';
import { useEffect, useRef, type ReactNode } from 'react';
import { ArrowUpRight, Check, LoaderCircle, ShieldCheck, X } from 'lucide-react';
export function Brand({ small = false }: { small?: boolean }) {
  return (
    <div className={'brand ' + (small ? 'small' : '')}>
      <span className="brand-icon">
        <ShieldCheck size={22} />
      </span>
      <span>
        Margin<span className="brand-light">Guard</span>
      </span>
    </div>
  );
}
export function Spinner() {
  return <LoaderCircle size={17} className="spin" aria-label="Loading" />;
}
export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: string }) {
  return (
    <span className={'badge ' + tone}>
      {tone === 'green' && <Check size={12} />} {children}
    </span>
  );
}
export function Empty({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty">
      <ShieldCheck size={35} />
      <h2>{title}</h2>
      <p>{description}</p>
      {children}
    </div>
  );
}
export function Modal({
  title,
  children,
  onClose,
  wide = false,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const close = useRef(onClose);
  close.current = onClose;
  useEffect(() => {
    const node = ref.current;
    node?.showModal();
    const cancel = (e: Event) => {
      e.preventDefault();
      close.current();
    };
    node?.addEventListener('cancel', cancel);
    return () => {
      node?.removeEventListener('cancel', cancel);
      node?.close();
    };
  }, []);
  return (
    <dialog ref={ref} className={'modal ' + (wide ? 'wide' : '')} aria-label={title}>
      <div className="modal-head">
        <h2>{title}</h2>
        <button className="icon-button" aria-label="Close dialog" onClick={onClose}>
          <X size={21} />
        </button>
      </div>
      {children}
    </dialog>
  );
}
export function SectionTitle({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <div className="section-title">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {children}
    </div>
  );
}
export function OutLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a className="button secondary" href={href} target="_blank" rel="noreferrer">
      {children}
      <ArrowUpRight size={15} />
    </a>
  );
}
