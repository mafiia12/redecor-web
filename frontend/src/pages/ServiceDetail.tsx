import { useEffect } from "react";
import { setWhatsAppContext } from "../components/WhatsApp";
import { track } from "../lib/analytics";
import { Link, useParams } from "react-router-dom";
import { ProjectCollection } from "../components/ProjectIndex";
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

const SCOPE_MATCH: Record<string, RegExp> = {
  contracting: /contract|civil|construct|structur|execution|مقاول|تنفيذ|إنشاء/i,
  fitout: /fit-?out|finish|interior|joinery|تشطيب|تجهيز|داخلي/i,
  supply: /supply|procure|furnitur|توريد|مشتريات|أثاث/i,
  "project-management": /manage|supervis|إدارة|إشراف/i,
};

export default function ServiceDetail() {
  const { slug } = useParams();
  const { t, lang, lp } = useLang();
  const { data } = useData();
  const s = services[lang].find((x) => x.slug === slug);
  usePageMeta(s ? `${s.title} | ${t.brand}` : t.brand, s?.text);
  useEffect(() => {
    if (!s) return;
    track("service_view");
    setWhatsAppContext(s.title);
    return () => setWhatsAppContext("");
  }, [s?.slug]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!s) return <NotFound />;

  // Related work = projects whose recorded scope mentions this service; otherwise the latest featured ones.
  const all = data?.projects ?? [];
  const byScope = all.filter((p) => SCOPE_MATCH[s.slug]?.test(`${p.scope_en} ${p.scope_ar}`));
  const related = (byScope.length ? byScope : all.filter((p) => p.featured)).slice(0, 4);
  return (
    <>
      <section className="page-head">
        <div className="container">
          <span className="kicker">{t.services.kicker}</span>
          <h1 className="display">{s.title}</h1>
          <p className="lead">{s.text}</p>
          <div className="btn-row btn-row--stack" style={{ marginTop: 16 }}>
            <Link to={`${lp("/contact")}?about=${encodeURIComponent(s.title)}&ref=${encodeURIComponent(`/services/${s.slug}`)}`} className="btn" data-track="cta">{t.cta}</Link>
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
            <ProjectCollection projects={related} />
          </div>
        </section>
      )}
    </>
  );
}
