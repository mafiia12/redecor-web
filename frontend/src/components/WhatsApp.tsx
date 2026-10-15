import { useEffect, useRef, useState } from "react";
import { isRealNumber, useData, useLang, waLink } from "../lib/context";

export const WA_EVENT = "redecor:whatsapp";
export const openWhatsApp = () => window.dispatchEvent(new Event(WA_EVENT));

export function WhatsApp() {
  const { t } = useLang();
  const { office } = useData();
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const fab = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const onOpen = () => setOpen(true);
    window.addEventListener(WA_EVENT, onOpen);
    return () => window.removeEventListener(WA_EVENT, onOpen);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        fab.current?.focus();
      }
    };
    const onDown = (e: MouseEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("mousedown", onDown);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("mousedown", onDown);
    };
  }, [open]);

  const rows = [
    { country: t.wa.egypt, num: office("eg")?.whatsapp || office("eg")?.phone || "" },
    { country: t.wa.qatar, num: office("qa")?.whatsapp || office("qa")?.phone || "" },
  ];

  return (
    <div className="wa" ref={root}>
      {open && (
        <div className="wa__sheet" role="dialog" aria-label={t.wa.title}>
          <div className="wa__head">
            <div>
              <strong>{t.wa.title}</strong>
              <span className="caption">{t.wa.sub}</span>
            </div>
            <button className="wa__close" onClick={() => setOpen(false)} aria-label={t.close}>
              <svg width="14" height="14" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round">
                <path d="M4 4l10 10M14 4L4 14" />
              </svg>
            </button>
          </div>
          <div className="wa__rows">
            {rows.map((r) => {
              const real = isRealNumber(r.num);
              const body = (
                <>
                  <span className="meta">
                    <b>{r.country}</b>
                    <span className="num">{real ? r.num : t.wa.soon}</span>
                  </span>
                  {real && <span className="chev">{t.chev}</span>}
                </>
              );
              return real ? (
                <a key={r.country} className="wa__row" href={waLink(r.num)} target="_blank" rel="noopener noreferrer">
                  {body}
                </a>
              ) : (
                <div key={r.country} className="wa__row" aria-disabled="true">
                  {body}
                </div>
              );
            })}
          </div>
        </div>
      )}
      <button ref={fab} className="wa__fab" aria-label={t.wa.label} aria-expanded={open} onClick={() => setOpen((v) => !v)}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" aria-hidden="true">
          <path d="M4.2 19.8l1.2-3.9A8.2 8.2 0 1 1 8.3 18.7z" />
          <path
            d="M9.3 8.4c.3-.5.8-.5 1.1-.2l.8 1.3c.2.3.1.6-.1.9l-.4.4c.5 1.1 1.3 1.9 2.4 2.4l.4-.4c.3-.2.6-.3.9-.1l1.3.8c.3.3.3.8-.2 1.1-.7.5-1.6.6-2.6.1a6.6 6.6 0 0 1-3.8-3.8c-.4-1-.4-1.9.2-2.5z"
            fill="currentColor"
            stroke="none"
          />
        </svg>
        <span className="wa__label">{t.wa.fab}</span>
      </button>
    </div>
  );
}
