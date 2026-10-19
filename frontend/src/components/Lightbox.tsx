import { useEffect, useRef } from "react";
import type { GalleryImage } from "../lib/api";
import { loc, useLang } from "../lib/context";

/** Full-screen viewer for project photos: arrows/swipe to move, Esc to close, focus kept inside, zoom on click.
 *  Rendered only when a photo is opened, so pages without photos carry no cost. */
export function Lightbox({ items, index, onIndex, onClose, title }: {
  items: GalleryImage[];
  index: number;
  onIndex: (i: number) => void;
  onClose: () => void;
  title: string;
}) {
  const { t, lang } = useLang();
  const box = useRef<HTMLDivElement>(null);
  const closeBtn = useRef<HTMLButtonElement>(null);
  const touchX = useRef<number | null>(null);
  const g = items[index];
  const rtl = lang === "ar";
  const go = (d: number) => onIndex((index + d + items.length) % items.length);

  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    closeBtn.current?.focus();
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
      opener?.focus();
    };
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowRight") go(rtl ? -1 : 1);
      else if (e.key === "ArrowLeft") go(rtl ? 1 : -1);
      else if (e.key === "Tab") {
        const f = box.current?.querySelectorAll<HTMLElement>("button");
        if (!f?.length) return;
        const first = f[0], last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) (e.preventDefault(), last.focus());
        else if (!e.shiftKey && document.activeElement === last) (e.preventDefault(), first.focus());
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  if (!g) return null;
  const cap = loc(g, "caption", lang);
  return (
    <div
      className="lb"
      role="dialog"
      aria-modal="true"
      aria-label={`${title}: ${t.lightbox.label(index + 1, items.length)}`}
      ref={box}
      onTouchStart={(e) => (touchX.current = e.touches[0].clientX)}
      onTouchEnd={(e) => {
        if (touchX.current === null) return;
        const dx = e.changedTouches[0].clientX - touchX.current;
        if (Math.abs(dx) > 50) go((dx < 0 ? 1 : -1) * (rtl ? -1 : 1));
        touchX.current = null;
      }}
    >
      <div className="lb__bar">
        <span className="lb__count" aria-live="polite">{index + 1} / {items.length}</span>
        <button ref={closeBtn} type="button" className="lb__btn" onClick={onClose} aria-label={t.close}>✕</button>
      </div>
      <figure className="lb__fig">
        <img
          key={g.id}
          src={g.image.src}
          srcSet={g.image.srcset}
          sizes="100vw"
          alt={cap.text || title}
          className="lb__img"
          onClick={(e) => e.currentTarget.classList.toggle("is-zoomed")}
        />
        {(cap.text || g.is_render) && (
          <figcaption {...cap.attrs}>
            {cap.text}
            {g.is_render && <span className="lb__tag">{t.projects.render}</span>}
          </figcaption>
        )}
      </figure>
      {items.length > 1 && (
        <>
          <button type="button" className="lb__btn lb__nav lb__nav--prev" onClick={() => go(-1)} aria-label={t.lightbox.prev}>‹</button>
          <button type="button" className="lb__btn lb__nav lb__nav--next" onClick={() => go(1)} aria-label={t.lightbox.next}>›</button>
        </>
      )}
    </div>
  );
}
