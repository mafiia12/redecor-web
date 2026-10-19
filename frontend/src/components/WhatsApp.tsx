import { useEffect, useRef, useState } from "react";
import { track } from "../lib/analytics";
import { useData, useLang, waLink, whatsappContacts } from "../lib/context";

export const WA_EVENT = "redecor:whatsapp";
export const openWhatsApp = () => window.dispatchEvent(new Event(WA_EVENT));

/** What the visitor is looking at (a project or a service), added to the prefilled WhatsApp message. */
let context = "";
export const setWhatsAppContext = (c: string) => {
  context = c;
};

const Icon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" aria-hidden="true">
    <path d="M4.2 19.8l1.2-3.9A8.2 8.2 0 1 1 8.3 18.7z" />
    <path
      d="M9.3 8.4c.3-.5.8-.5 1.1-.2l.8 1.3c.2.3.1.6-.1.9l-.4.4c.5 1.1 1.3 1.9 2.4 2.4l.4-.4c.3-.2.6-.3.9-.1l1.3.8c.3.3.3.8-.2 1.1-.7.5-1.6.6-2.6.1a6.6 6.6 0 0 1-3.8-3.8c-.4-1-.4-1.9.2-2.5z"
      fill="currentColor"
      stroke="none"
    />
  </svg>
);

export function WhatsApp() {
  const { t } = useLang();
  const { data } = useData();
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const fab = useRef<HTMLButtonElement>(null);
  const contacts = whatsappContacts(data?.offices ?? [], t.countries);
  const message = () => (context ? t.wa.about(context) : t.wa.hello);
  const go = (num: string) => {
    track("whatsapp_click");
    window.open(waLink(num, message()), "_blank", "noopener,noreferrer");
    setOpen(false);
  };

  useEffect(() => {
    const onOpen = () => {
      track("whatsapp_open");
      if (contacts.length === 1) go(contacts[0].num);
      else setOpen(true);
    };
    window.addEventListener(WA_EVENT, onOpen);
    return () => window.removeEventListener(WA_EVENT, onOpen);
  });

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

  if (!contacts.length) return null; // no confirmed number: no button rather than a dead one

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
            {contacts.map((c) => (
              <button key={c.num} type="button" className="wa__row" onClick={() => go(c.num)}>
                <span className="meta">
                  <b>{c.label}</b>
                  <span className="num" dir="ltr">{c.num}</span>
                </span>
                <span className="chev" aria-hidden="true">{t.chev}</span>
              </button>
            ))}
          </div>
        </div>
      )}
      <button
        ref={fab}
        className="wa__fab"
        aria-label={t.wa.label}
        aria-haspopup={contacts.length > 1 ? "dialog" : undefined}
        aria-expanded={contacts.length > 1 ? open : undefined}
        onClick={() => (open ? setOpen(false) : openWhatsApp())}
      >
        <Icon />
        <span className="wa__label">{t.wa.fab}</span>
      </button>
    </div>
  );
}
