import type { CSSProperties } from "react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ProjectTile } from "../components/Cards";
import { Photo } from "../components/Photo";
import { Reveal } from "../components/Reveal";
import { ApiError, getProject, type GalleryImage, type ProjectDetail as Detail } from "../lib/api";
import { pick, useLang, usePageMeta } from "../lib/context";

/** Story text: "## Heading" starts a section, blank lines split paragraphs. */
function parseStory(text: string) {
  const out: { head: string; paras: string[] }[] = [];
  for (const block of text.split(/\n{2,}/)) {
    const b = block.trim();
    if (!b) continue;
    if (b.startsWith("##")) {
      const [first, ...rest] = b.split("\n");
      out.push({ head: first.replace(/^#+\s*/, ""), paras: rest.join("\n").trim() ? [rest.join("\n").trim()] : [] });
    } else if (out.length) out[out.length - 1].paras.push(b);
    else out.push({ head: "", paras: [b] });
  }
  return out;
}

/** "Label: Value" per line (also accepts the Arabic colon). */
function parseDetails(text: string) {
  return text
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean)
    .map((l) => {
      const m = l.match(/^([^:：]{1,40})[:：]\s*(.+)$/);
      return m ? ([m[1].trim(), m[2].trim()] as const) : (["", l] as const);
    });
}

/** Consecutive "half" images pair up; everything else is a full row. */
function buildRows(items: GalleryImage[]) {
  const rows: GalleryImage[][] = [];
  for (let i = 0; i < items.length; i++) {
    if (items[i].layout === "half" && items[i + 1]?.layout === "half") rows.push([items[i], items[++i]]);
    else rows.push([items[i]]);
  }
  return rows;
}

export default function ProjectDetail() {
  const { slug = "" } = useParams();
  const { t, lang, lp } = useLang();
  const [p, setP] = useState<Detail | null>(null);
  const [status, setStatus] = useState<"loading" | "ok" | "missing" | "error">("loading");

  useEffect(() => {
    let live = true;
    setStatus("loading");
    getProject(slug)
      .then((d) => live && (setP(d), setStatus("ok")))
      .catch((e) => live && setStatus(e instanceof ApiError && e.status === 404 ? "missing" : "error"));
    return () => {
      live = false;
    };
  }, [slug]);

  const title = p ? pick(p, "title", lang) : "";
  usePageMeta(p ? `${title} | ${t.brand}` : t.brand, p ? pick(p, "summary", lang) : undefined);

  if (status === "missing" || status === "error") {
    return (
      <div className="container notice">
        <h1 className="h2">{status === "missing" ? t.projects.notFound : t.projects.loadError}</h1>
        <Link to={lp("/projects")} className="btn btn--outline">{t.back}</Link>
      </div>
    );
  }
  if (!p) return <div className="route-loading"><div className="skeleton" style={{ aspectRatio: "16 / 9", borderRadius: 0 }} /></div>;

  const cover = p.gallery.find((g) => g.is_cover) ?? p.gallery[0];
  const rest = p.gallery.filter((g) => g !== cover);
  const tagline = pick(p, "tagline", lang);
  const summary = pick(p, "summary", lang);
  const story = parseStory(pick(p, "story", lang));
  const details = parseDetails(pick(p, "details", lang));
  const place = [pick(p, "city", lang), t.countries[p.country]].filter(Boolean).join(lang === "ar" ? "، " : ", ");
  const area = p.area_m2 ? `${p.area_m2.toLocaleString(lang === "ar" ? "ar-EG" : "en")} ${t.form.unit}` : "";
  const meta = [t.types[p.type], p.year, area, pick(p, "scope", lang)].filter(Boolean).join(" · ");

  return (
    <article className="case fade-in">
      <div className="case__col">
        <Link to={lp("/projects")} className="case__back">{t.back}</Link>
        <h1 className="case__title">{title}</h1>
        {p.logo && (
          <div className="case__logo">
            <img src={p.logo.src} alt={p.client_name || title} width={p.logo.width} height={p.logo.height} />
          </div>
        )}
      </div>

      {cover && (
        <div className="case__hero">
          <Photo img={cover.image} alt={title} ratio={`${cover.image.width}/${cover.image.height}`} priority sizes="(min-width:1200px) 1200px, 100vw" />
          {(p.is_render || cover.is_render) && <span className="badge">{t.projects.render}</span>}
        </div>
      )}

      <div className="case__col case__text">
        {tagline && <p className="case__tagline">{tagline}</p>}
        {summary && <p>{summary}</p>}
        <p className="case__meta">{[place, p.client_name].filter(Boolean).join(" · ")}</p>
        {meta && <p className="case__meta">{meta}</p>}
        {details.length > 0 && (
          <dl className="case__facts">
            {details.map(([k, v], i) => (k ? <div key={i} style={{ display: "contents" }}><dt>{k}</dt><dd>{v}</dd></div> : <dd key={i} style={{ gridColumn: "1 / -1" }}>{v}</dd>))}
          </dl>
        )}
        {story.map((s, i) => (
          <section key={i}>
            {s.head && <h2>{s.head}</h2>}
            {s.paras.map((para, j) => <p key={j}>{para}</p>)}
          </section>
        ))}
      </div>

      <div className="case__gallery">
        {buildRows(rest).map((row, ri) => (
          <Reveal key={ri} className={row.length === 2 ? "case__row case__row--pair" : "case__row"}>
            {row.map((g) => {
              const cap = pick(g, "caption", lang);
              return (
                <figure key={g.id}>
                  <div style={{ position: "relative" }}>
                    <Photo img={g.image} alt={cap || title} ratio={`${g.image.width}/${g.image.height}`} sizes={row.length === 2 ? "(min-width:900px) 600px, 100vw" : "(min-width:1200px) 1200px, 100vw"} />
                    {g.is_render && <span className="badge">{t.projects.render}</span>}
                  </div>
                  {cap && <figcaption>{cap}</figcaption>}
                </figure>
              );
            })}
          </Reveal>
        ))}
      </div>

      {p.related.length > 0 && (
        <section className="case__related">
          <div className="container">
            <Reveal className="section-head section-head--row">
              <h2 className="h2">{t.projects.related}</h2>
              <Link to={lp("/projects")} className="link">{t.home.allProjects}</Link>
            </Reveal>
            <div className="mosaic" style={{ "--n": p.related.length } as CSSProperties}>
              {p.related.map((r) => <ProjectTile key={r.id} p={r} />)}
            </div>
          </div>
        </section>
      )}
    </article>
  );
}
