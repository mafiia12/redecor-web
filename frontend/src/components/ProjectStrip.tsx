import { useRef } from "react";
import { Link } from "react-router-dom";
import type { ProjectCard } from "../lib/api";
import { pick, useLang } from "../lib/context";
import { Photo } from "./Photo";

/** Full-bleed strip of featured projects (3 across on desktop), with arrows. */
export function ProjectStrip({ projects }: { projects: ProjectCard[] }) {
  const { t, lang, lp } = useLang();
  const track = useRef<HTMLDivElement>(null);
  const rtl = lang === "ar";

  const go = (dir: 1 | -1) => {
    const el = track.current;
    if (!el) return;
    const slide = el.firstElementChild as HTMLElement | null;
    const step = slide ? slide.getBoundingClientRect().width : el.clientWidth;
    el.scrollBy({ left: dir * step * (rtl ? -1 : 1) });
  };

  return (
    <section className="strip" aria-label={t.home.projectsTitle}>
      <div className="strip__track" ref={track} tabIndex={0}>
        {projects.map((p, i) => {
          const title = pick(p, "title", lang);
          const meta = [t.types[p.type], pick(p, "city", lang)].filter(Boolean).join(" · ");
          return (
            <Link key={p.id} to={lp(`/projects/${p.slug}`)} className="strip__slide">
              <div className="strip__media">
                <Photo img={p.cover} alt={title} ratio="7/8" priority={i < 3} sizes="(min-width:800px) 34vw, 100vw" />
                {p.is_render && <span className="badge">{t.projects.render}</span>}
              </div>
              <div className="strip__cap">
                <b>{title}</b>
                <span>{meta}</span>
              </div>
            </Link>
          );
        })}
      </div>
      <button type="button" className="strip__btn strip__btn--prev" aria-label={t.home.prev} onClick={() => go(-1)}>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 12H5M11 6l-6 6 6 6" /></svg>
      </button>
      <button type="button" className="strip__btn strip__btn--next" aria-label={t.home.next} onClick={() => go(1)}>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M13 6l6 6-6 6" /></svg>
      </button>
    </section>
  );
}
