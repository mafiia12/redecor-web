import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ProjectTile } from "../components/Cards";
import { Photo } from "../components/Photo";
import { Reveal } from "../components/Reveal";
import { ApiError, getProject, type GalleryImage, type ProjectDetail as Detail } from "../lib/api";
import { pick, useLang, usePageMeta } from "../lib/context";

/** Rows follow the design rhythm: wide, pair, full-bleed, pair... An image flagged full_bleed always gets its own row. */
function buildRows(items: GalleryImage[]) {
  const pattern = ["wide", "pair", "bleed", "pair"] as const;
  const rows: { kind: "wide" | "pair" | "bleed"; items: GalleryImage[] }[] = [];
  let i = 0;
  let step = 0;
  while (i < items.length) {
    if (items[i].full_bleed) {
      rows.push({ kind: "bleed", items: [items[i++]] });
      continue;
    }
    const kind = pattern[step++ % pattern.length];
    const take = kind === "pair" ? 2 : 1;
    const chunk: GalleryImage[] = [];
    while (chunk.length < take && i < items.length && !items[i].full_bleed) chunk.push(items[i++]);
    rows.push({ kind: chunk.length === 2 ? "pair" : kind === "pair" ? "wide" : kind, items: chunk });
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
  if (!p) return <div className="route-loading"><div className="cover"><div className="skeleton" style={{ aspectRatio: "16 / 9", borderRadius: 0 }} /></div></div>;

  const cover = p.gallery.find((g) => g.is_cover) ?? p.gallery[0];
  const rest = p.gallery.filter((g) => g !== cover);
  const facts: [string, string | number | null][] = [
    [t.projects.facts.city, [pick(p, "city", lang), t.countries[p.country]].filter(Boolean).join(lang === "ar" ? "، " : ", ")],
    [t.projects.facts.type, t.types[p.type]],
    [t.projects.facts.year, p.year],
    [t.projects.facts.area, p.area_m2 ? `${p.area_m2.toLocaleString(lang === "ar" ? "ar-EG" : "en")} ${t.form.unit}` : null],
    [t.projects.facts.scope, pick(p, "scope", lang) || null],
  ];

  return (
    <article className="fade-in">
      <div className="cover" style={{ position: "relative" }}>
        <Photo img={cover?.image} alt={title} ratio="16/9" priority hint={t.projects.imgEmpty} sizes="(min-width:1440px) 1440px, 100vw" />
        {(p.is_render || cover?.is_render) && <span className="badge">{t.projects.render}</span>}
      </div>

      <section className="section" style={{ paddingBottom: 80 }}>
        <div className="container stack" style={{ gap: 24 }}>
          <Link to={lp("/projects")} className="crumb">{t.back}</Link>
          <h1 className="display" style={{ fontSize: undefined }}>{title}</h1>
          {pick(p, "summary", lang) && <p className="lead" style={{ maxWidth: 720 }}>{pick(p, "summary", lang)}</p>}
          <dl className="facts">
            {facts.filter(([, v]) => v).map(([k, v]) => (
              <div key={k}>
                <dt>{k}</dt>
                <dd>{v}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {rest.length > 0 && (
        <section className="section section--tight-top" style={{ paddingBottom: "var(--section-y)" }}>
          <div className="gallery">
            {buildRows(rest).map((row, ri) => (
              <Reveal key={ri} className={row.kind === "bleed" ? "gallery__bleed" : "container"}>
                <div className={row.kind === "pair" ? "gallery__row gallery__row--pair" : "gallery__row"}>
                  {row.items.map((g) => {
                    const cap = pick(g, "caption", lang);
                    const ratio = row.kind === "pair" ? (g.image.width >= g.image.height ? "4/3" : "4/5") : "16/9";
                    return (
                      <figure key={g.id}>
                        <div style={{ position: "relative" }}>
                          <Photo img={g.image} alt={cap || title} ratio={ratio} radius={row.kind === "bleed" ? 0 : 20} sizes={row.kind === "pair" ? "(min-width:700px) 50vw, 100vw" : "(min-width:1440px) 1440px, 100vw"} />
                          {g.is_render && <span className="badge">{t.projects.render}</span>}
                        </div>
                        {cap && <figcaption className="caption" style={row.kind === "bleed" ? { paddingInline: "var(--gutter)" } : undefined}>{cap}</figcaption>}
                      </figure>
                    );
                  })}
                </div>
              </Reveal>
            ))}
          </div>
        </section>
      )}

      {p.related.length > 0 && (
        <section className="section section--surface">
          <div className="container">
            <Reveal className="section-head section-head--row">
              <h2 className="h2">{t.projects.related}</h2>
              <Link to={lp("/projects")} className="link">{t.home.allProjects}</Link>
            </Reveal>
            <div className="mosaic">
              {p.related.map((r) => (
                <ProjectTile key={r.id} p={r} />
              ))}
            </div>
          </div>
        </section>
      )}
    </article>
  );
}
