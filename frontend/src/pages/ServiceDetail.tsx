import type { CSSProperties } from "react";
import { Link, useParams } from "react-router-dom";
import { ProjectTile } from "../components/Cards";
import { SitePhoto } from "../components/Photo";
import { Reveal } from "../components/Reveal";
import { services } from "../i18n";
import { useData, useLang, usePageMeta } from "../lib/context";
import NotFound from "./NotFound";

const HINTS: Record<string, string> = {
  contracting: "Service hero: site works in progress",
  fitout: "Service hero: hallway with stone floor and timber joinery, finished",
  supply: "Service hero: curated materials and fixtures ready for delivery",
  "project-management": "Service hero: project team reviewing drawings on site",
};

export default function ServiceDetail() {
  const { slug } = useParams();
  const { t, lang, lp } = useLang();
  const { data } = useData();
  const s = services[lang].find((x) => x.slug === slug);
  usePageMeta(s ? `${s.title} | ${t.brand}` : t.brand, s?.text);
  if (!s) return <NotFound />;

  const related = (data?.projects ?? []).slice(0, 3);
  return (
    <>
      <section className="page-head">
        <div className="container">
          <span className="kicker">{t.services.kicker}</span>
          <h1 className="display">{s.title}</h1>
          <p className="lead">{s.text}</p>
          <div className="btn-row btn-row--stack" style={{ marginTop: 16 }}>
            <Link to={lp("/contact")} className="btn">{t.cta}</Link>
            <a href="#related" className="link">{t.services.relatedProjects}</a>
          </div>
        </div>
      </section>
      <div className="cover ratio-mobile-45">
        <SitePhoto hideIfEmpty slot={`service-${s.slug}-hero`} ratio="16/9" priority hint={HINTS[s.slug]} alt={s.title} sizes="(min-width:1440px) 1440px, 100vw" />
      </div>

      {s.included.length > 0 && <section className="section">
        <div className="container">
          <Reveal className="section-head">
            <h2 className="h2">{t.services.included}</h2>
            <p className="lead">{t.services.includedSub}</p>
          </Reveal>
          <div className="included">
            {s.included.map(([title, text], i) => (
              <Reveal key={title} delay={(i % 3) * 80}>
                <h3>{title}</h3>
                <p>{text}</p>
              </Reveal>
            ))}
          </div>
        </div>
      </section>}

      {s.slug === "fitout" && (
        <section className="section section--tight-top" style={{ paddingBottom: "var(--section-y)" }}>
          <div className="container grid grid--2" style={{ gap: 24 }}>
            <SitePhoto slot="service-fitout-d1" ratio="4/5" radius={20} hint="Detail: marble floor junction with skirting" alt="" sizes="(min-width:700px) 50vw, 100vw" />
            <SitePhoto slot="service-fitout-d2" ratio="4/5" radius={20} hint="Detail: joinery with brass inlay" alt="" sizes="(min-width:700px) 50vw, 100vw" />
          </div>
        </section>
      )}

      {related.length > 0 && (
        <section className="section section--surface" id="related">
          <div className="container">
            <Reveal className="section-head section-head--row">
              <div>
                <h2 className="h2">{t.projects.related}</h2>
                <p className="lead">{t.services.relatedSub}</p>
              </div>
              <Link to={lp("/projects")} className="link">{t.home.allProjects}</Link>
            </Reveal>
            <div className="mosaic" style={{ "--n": related.length } as CSSProperties}>
              {related.map((p) => (
                <ProjectTile key={p.id} p={p} />
              ))}
            </div>
          </div>
        </section>
      )}
    </>
  );
}
