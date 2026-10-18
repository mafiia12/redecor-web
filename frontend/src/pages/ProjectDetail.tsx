import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ProjectCollection } from "../components/ProjectIndex";
import { Photo } from "../components/Photo";
import { Reveal } from "../components/Reveal";
import { ApiError, getProject, type GalleryImage, type ProjectDetail as Detail } from "../lib/api";
import { Lightbox } from "../components/Lightbox";
import { setWhatsAppContext } from "../components/WhatsApp";
import { track } from "../lib/analytics";
import { loc, pick, useLang, usePageMeta } from "../lib/context";

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
  const { t, lp } = useLang();
  const [p, setP] = useState<Detail | null>(null);
  const [status, setStatus] = useState<"loading" | "ok" | "missing" | "error">("loading");

  useEffect(() => {
    let live = true;
    setStatus("loading");
    getProject(slug)
      .then((d) => {
        if (!live) return;
        setP(d);
        setStatus("ok");
        track("project_view");
      })
      .catch((e) => live && setStatus(e instanceof ApiError && e.status === 404 ? "missing" : "error"));
    return () => {
      live = false;
    };
  }, [slug]);

  if (status === "missing" || status === "error") {
    return (
      <div className="container notice">
        <h1 className="h2">{status === "missing" ? t.projects.notFound : t.projects.loadError}</h1>
        <Link to={lp("/projects")} className="btn btn--outline">{t.back}</Link>
      </div>
    );
  }
  if (!p) return <div className="route-loading"><div className="skeleton" style={{ aspectRatio: "16 / 9", borderRadius: 0 }} /></div>;
  return <ProjectView p={p} />;
}

/** The project page itself. Also used by the admin "Preview" for drafts (preview = no tracking / CTA links). */
export function ProjectView({ p, preview = false }: { p: Detail; preview?: boolean }) {
  const { t, lang, lp } = useLang();
  const [open, setOpen] = useState<number | null>(null);
  const title = loc(p, "title", lang);
  usePageMeta(`${title.text} | ${t.brand}`, pick(p, "summary", lang) || undefined);

  useEffect(() => {
    if (preview) return;
    setWhatsAppContext(title.text);
    return () => setWhatsAppContext("");
  }, [title.text, preview]);

  const cover = p.gallery.find((g) => g.is_cover) ?? p.gallery[0];
  const rest = p.gallery.filter((g) => g !== cover);
  const ordered = cover ? [cover, ...rest] : rest; // lightbox order = page order
  const tagline = loc(p, "tagline", lang);
  const summary = loc(p, "summary", lang);
  const storyLoc = loc(p, "story", lang);
  const story = parseStory(storyLoc.text);
  const detailsLoc = loc(p, "details", lang);
  const written = parseDetails(detailsLoc.text);
  const city = pick(p, "city", lang);
  const place = [city, t.countries[p.country]].filter(Boolean).join(lang === "ar" ? "، " : ", ");
  const area = p.area_m2 ? `${p.area_m2.toLocaleString(lang === "ar" ? "ar-EG" : "en")} ${t.form.unit}` : "";
  // Facts written in the admin win; otherwise build them from the project fields (never shown twice).
  const details: (readonly [string, string])[] = written.length
    ? written
    : ([
        [t.projects.facts.client, p.client_name],
        [t.projects.facts.city, place],
        [t.projects.facts.type, t.types[p.type]],
        [t.projects.facts.year, p.year ? String(p.year) : ""],
        [t.projects.facts.area, area],
        [t.projects.facts.scope, pick(p, "scope", lang)],
      ] as const).filter(([, v]) => v);
  const ask = `${lp("/contact")}?about=${encodeURIComponent(title.text)}&ref=${encodeURIComponent(`/projects/${p.slug}`)}`;

  const photo = (g: GalleryImage, sizes: string, priority = false) => {
    const cap = loc(g, "caption", lang);
    const alt = (lang === "ar" ? g.alt_ar || g.alt_en : g.alt_en) || cap.text || title.text;
    return (
      <button type="button" className="case__zoom" onClick={() => setOpen(ordered.indexOf(g))} aria-label={`${t.lightbox.open}: ${cap.text || title.text}`}>
        <Photo img={g.image} alt={alt} ratio={`${g.image.width}/${g.image.height}`} priority={priority} sizes={sizes} />
      </button>
    );
  };

  // Renders and site photos are shown as separate groups when a project has both.
  const views = rest.filter((g) => g.kind === "render" || (!g.kind && g.is_render));
  const done = rest.filter((g) => !views.includes(g));
  const groups = views.length && done.length ? [[t.projects.views, views], [t.projects.executed, done]] as const : [["", rest]] as const;

  return (
    <article className="case fade-in">
      <header className="case__head container">
        <div className="case__lead">
          <nav className="case__crumbs" aria-label={t.projects.title}>
            <Link to={lp("/projects")} className="case__back">{t.projects.title}</Link>
            <span aria-hidden="true">/</span>
            <span aria-current="page" {...title.attrs}>{title.text}</span>
          </nav>
          <span className="case__kicker">{t.types[p.type]}{p.is_render && <span className="pindex__tag">{t.projects.renderShort}</span>}</span>
          <h1 className="case__title" {...title.attrs}>{title.text}</h1>
          {tagline.text && <p className="case__tagline" {...tagline.attrs}>{tagline.text}</p>}
          {summary.text && <p className="case__summary" {...summary.attrs}>{summary.text}</p>}
          {!preview && (
            <div className="case__ctas">
              <Link to={ask} className="btn" data-track="cta">{t.projects.askCta}</Link>
            </div>
          )}
        </div>
        <aside className="case__side">
          {p.logo && (
            <div className="case__logo">
              <img src={p.logo.src} alt={p.client_name || title.text} width={p.logo.width} height={p.logo.height} />
            </div>
          )}
          {details.length > 0 && (
            <dl className="case__facts" {...detailsLoc.attrs}>
              {details.map(([k, v], i) => (k ? <div key={i}><dt>{k}</dt><dd>{v}</dd></div> : <div key={i}><dd>{v}</dd></div>))}
            </dl>
          )}
        </aside>
      </header>

      {cover && (
        <div className="case__hero">
          {photo(cover, "(min-width:1440px) 1440px, 100vw", true)}
          {(p.is_render || cover.is_render) && <span className="badge">{t.projects.render}</span>}
        </div>
      )}

      {story.length > 0 && (
        <div className="case__story container">
          {story.map((s, i) => (
            <section key={i} {...storyLoc.attrs}>
              {s.head && <h2>{s.head}</h2>}
              {s.paras.map((para, j) => <p key={j}>{para}</p>)}
            </section>
          ))}
        </div>
      )}

      {rest.length > 0 && groups.map(([heading, items]) => (
        <section key={heading || "gallery"} className="case__gallery" aria-label={heading || undefined}>
          {heading && <h2 className="case__group">{heading}</h2>}
          {buildRows([...items]).map((row, ri) => (
            <Reveal key={ri} className={row.length === 2 ? "case__row case__row--pair" : "case__row"}>
              {row.map((g) => {
                const cap = loc(g, "caption", lang);
                return (
                  <figure key={g.id}>
                    <div style={{ position: "relative" }}>
                      {photo(g, row.length === 2 ? "(min-width:900px) 720px, 100vw" : "(min-width:1440px) 1440px, 100vw")}
                      {g.is_render && !p.is_render && !heading && <span className="badge badge--sm">{t.projects.renderShort}</span>}
                    </div>
                    {cap.text && <figcaption {...cap.attrs}>{cap.text}</figcaption>}
                  </figure>
                );
              })}
            </Reveal>
          ))}
        </section>
      ))}

      {!preview && (rest.length > 0 || story.length > 0) && (
        <section className="case__ask">
          <div className="case__col">
            <h2>{t.projects.askTitle}</h2>
            <p>{t.projects.askSub}</p>
            <div className="case__ask-ctas">
              <Link to={ask} className="btn" data-track="cta">{t.projects.askCta}</Link>
            </div>
          </div>
        </section>
      )}

      {(p.prev || p.next) && (
        <nav className="case__pn container" aria-label={t.projects.related}>
          {p.prev ? (
            <Link to={lp(`/projects/${p.prev.slug}`)} className="case__pn-link" rel="prev">
              <span>{t.projects.prevProject}</span>
              <b {...loc(p.prev, "title", lang).attrs}>{loc(p.prev, "title", lang).text}</b>
            </Link>
          ) : <span />}
          {p.next && (
            <Link to={lp(`/projects/${p.next.slug}`)} className="case__pn-link case__pn-link--next" rel="next">
              <span>{t.projects.nextProject}</span>
              <b {...loc(p.next, "title", lang).attrs}>{loc(p.next, "title", lang).text}</b>
            </Link>
          )}
        </nav>
      )}

      {p.related.length > 0 && (
        <section className="case__related">
          <div className="container">
            <Reveal className="section-head section-head--row">
              <h2 className="h2">{t.projects.related}</h2>
              <Link to={lp("/projects")} className="link">{t.home.allProjects}</Link>
            </Reveal>
            <ProjectCollection projects={p.related} />
          </div>
        </section>
      )}

      {open !== null && <Lightbox items={ordered} index={open} onIndex={setOpen} onClose={() => setOpen(null)} title={title.text} />}
    </article>
  );
}
