import type { CSSProperties } from "react";
import { Link } from "react-router-dom";
import type { ProjectCard } from "../lib/api";
import { loc, useLang } from "../lib/context";
import { ProjectTile } from "./Cards";
import { Photo } from "./Photo";

/** Photo grid only once most projects have a cover; until then the text list reads better than empty tiles. */
export const preferGrid = (projects: ProjectCard[]) =>
  projects.length > 0 && projects.filter((p) => p.cover).length * 2 >= projects.length;

/** A set of projects as a photo mosaic or as the editorial list, whichever suits the content right now. */
export function ProjectCollection({ projects, view }: { projects: ProjectCard[]; view?: "list" | "grid" }) {
  if ((view ?? (preferGrid(projects) ? "grid" : "list")) === "list") return <ProjectIndex projects={projects} />;
  return (
    <div className="mosaic" style={{ "--n": projects.length } as CSSProperties}>
      {projects.map((p) => <ProjectTile key={p.id} p={p} />)}
    </div>
  );
}

/** Editorial project list: one row per project (number, name, type, location, year). Reads well with text only;
 *  when a project has a cover photo it appears as a small preview on hover (desktop). */
export function ProjectIndex({ projects, start = 1 }: { projects: ProjectCard[]; start?: number }) {
  const { t, lang, lp } = useLang();
  const c = t.projects.cols;
  const years = projects.some((p) => p.year); // no years on record yet: the column is left out
  return (
    <div className={`pindex${years ? "" : " pindex--noyear"}`}>
      <div className="pindex__head" aria-hidden="true">
        <span>{c.no}</span>
        <span>{c.project}</span>
        <span>{c.type}</span>
        <span>{c.location}</span>
        {years && <span>{c.year}</span>}
      </div>
      <ol className="pindex__list">
        {projects.map((p, i) => {
          const title = loc(p, "title", lang);
          const tagline = loc(p, "tagline", lang);
          const city = loc(p, "city", lang);
          const where = [city.text, t.countries[p.country]].filter(Boolean).join(lang === "ar" ? "، " : ", ");
          return (
            <li key={p.id}>
              <Link to={lp(`/projects/${p.slug}`)} className="pindex__row">
                <span className="pindex__n">{String(start + i).padStart(2, "0")}</span>
                <span className="pindex__name">
                  <b {...title.attrs}>{title.text}</b>
                  {p.is_render && <span className="pindex__tag">{t.projects.renderShort}</span>}
                  {tagline.text && <span className="pindex__line" {...tagline.attrs}>{tagline.text}</span>}
                </span>
                <span className="pindex__meta">{[t.types[p.type], where, p.year].filter(Boolean).join(" · ")}</span>
                <span className="pindex__type">{t.types[p.type]}</span>
                <span className="pindex__where">{where}</span>
                {years && <span className="pindex__year">{p.year ?? ""}</span>}
                <span className="pindex__arrow" aria-hidden="true">→</span>
                {p.cover && (
                  <span className="pindex__thumb" aria-hidden="true">
                    <Photo img={p.cover} ratio="4/3" sizes="220px" />
                  </span>
                )}
              </Link>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
