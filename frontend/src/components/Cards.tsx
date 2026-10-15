import { Link } from "react-router-dom";
import type { ProjectCard as ProjectCardData } from "../lib/api";
import { pick, useLang } from "../lib/context";
import { Photo, SitePhoto } from "./Photo";

export function ProjectCard({ p, sizes = "(min-width:1000px) 384px, (min-width:640px) 50vw, 100vw" }: { p: ProjectCardData; sizes?: string }) {
  const { lang, t, lp } = useLang();
  const meta = [pick(p, "city", lang), t.types[p.type], p.year].filter(Boolean).join(" · ");
  const title = pick(p, "title", lang);
  return (
    <Link to={lp(`/projects/${p.slug}`)} className="pcard">
      <div className="pcard__media">
        <Photo img={p.cover} alt={title} ratio="4/5" hint={t.projects.imgEmpty} sizes={sizes} />
        {p.is_render && <span className="badge">{t.projects.render}</span>}
      </div>
      <div className="pcard__body">
        <span className="pcard__title">{title}</span>
        <span className="caption">{meta}</span>
      </div>
    </Link>
  );
}

export function ProjectGridSkeleton({ n = 6 }: { n?: number }) {
  return (
    <div className="grid grid--3" aria-hidden="true">
      {Array.from({ length: n }, (_, i) => (
        <div key={i} className="skeleton" style={{ aspectRatio: "4 / 5" }} />
      ))}
    </div>
  );
}

export function ServiceTile({ to, title, text, slot, hint }: { to: string; title: string; text: string; slot: string; hint: string }) {
  const { t } = useLang();
  return (
    <Link to={to} className="stile">
      <div className="stile__media">
        <SitePhoto slot={slot} ratio="4/3" hint={hint} alt={title} sizes="(min-width:1000px) 384px, (min-width:640px) 50vw, 100vw" />
      </div>
      <div className="stile__body">
        <span className="stile__title">{title}</span>
        <span className="stile__text">{text}</span>
        <span className="stile__more">{t.learnMore}</span>
      </div>
    </Link>
  );
}
