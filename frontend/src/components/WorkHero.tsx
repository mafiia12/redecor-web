import { useEffect, useRef } from "react";
import { Photo } from "./Photo";
import type { Img } from "../lib/api";
import { prefersReducedMotion } from "../lib/hooks";
import { useLang } from "../lib/context";

/** Full-width intro with a darkened image; the text fades out while scrolling. */
export function WorkHero({ title, sub, bg, target }: { title: string; sub: string; bg?: Img | null; target: string }) {
  const { t } = useLang();
  const copy = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (prefersReducedMotion()) return;
    let raf = 0;
    const update = () => {
      raf = 0;
      if (copy.current) copy.current.style.opacity = String(Math.max(0, 1 - window.scrollY / 380));
    };
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(update);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      if (raf) cancelAnimationFrame(raf);
    };
  }, []);
  return (
    <section className="work-hero" data-dark>
      {bg && (
        <div className="work-hero__bg" aria-hidden="true">
          <Photo img={bg} alt="" ratio="16/9" dark priority sizes="100vw" />
        </div>
      )}
      <div className="work-hero__copy" ref={copy}>
        <h1>{title}</h1>
        <p>{sub}</p>
        <button type="button" className="scroll-cue" onClick={() => document.getElementById(target)?.scrollIntoView({ behavior: "smooth" })}>
          {t.home.scrollCue}
          <svg width="40" height="20" viewBox="0 0 40 20" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M2 3l18 14L38 3" /></svg>
        </button>
      </div>
    </section>
  );
}
