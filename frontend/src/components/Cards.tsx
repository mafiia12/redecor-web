import { Link } from "react-router-dom";
import type { ProjectCard as ProjectCardData } from "../lib/api";
import { loc, useLang } from "../lib/context";
import { Photo } from "./Photo";

export function ProjectGridSkeleton({ n = 6 }: { n?: number }) {
  return (
    <div className="grid grid--3" aria-hidden="true">
      {Array.from({ length: n }, (_, i) => (
        <div key={i} className="skeleton" style={{ aspectRatio: "4 / 5" }} />
      ))}
    </div>
  );
}

/** Mosaic tile. With a cover photo: image with the title on hover. Without one (photos come later):
 *  a typographic tile built only from the project's published facts. Same grid, so photos can be added any time. */
export function ProjectTile({ p }: { p: ProjectCardData }) {
  const { lang, t, lp } = useLang();
  const title = loc(p, "title", lang);
  const city = loc(p, "city", lang);
  const tagline = loc(p, "tagline", lang);
  const where = [city.text, t.countries[p.country]].filter(Boolean).join(lang === "ar" ? "، " : ", ");
  if (!p.cover) {
    return (
      <Link to={lp(`/projects/${p.slug}`)} className="tile tile--type">
        <span className="tile__kind">{t.types[p.type]}</span>
        <span className="tile__name" {...title.attrs}>{title.text}</span>
        {tagline.text && <span className="tile__line" {...tagline.attrs}>{tagline.text}</span>}
        <span className="tile__foot">
          <span>{[where, p.year].filter(Boolean).join(" · ")}</span>
          <span className="tile__arrow" aria-hidden="true">→</span>
        </span>
      </Link>
    );
  }
  const meta = [p.year, city.text, t.types[p.type]].filter(Boolean)[0] ?? t.types[p.type];
  return (
    <Link to={lp(`/projects/${p.slug}`)} className="tile" aria-label={title.text}>
      <Photo img={p.cover} alt={title.text} ratio="5/4" sizes="(min-width:1100px) 25vw, (min-width:700px) 33vw, 50vw" />
      {p.is_render && <span className="badge badge--sm">{t.projects.renderShort}</span>}
      <span className="tile__veil">
        <b {...title.attrs}>{title.text}</b>
        <span>{meta}</span>
      </span>
    </Link>
  );
}
