import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ProjectCard, ProjectGridSkeleton, ServiceTile } from "../components/Cards";
import { Segmented } from "../components/Filters";
import { ClientWall } from "../components/ClientWall";
import { HowWeWork } from "../components/HowWeWork";
import { SitePhoto } from "../components/Photo";
import { ProjectStrip } from "../components/ProjectStrip";
import { Reveal } from "../components/Reveal";
import { useData, useLang, usePageMeta } from "../lib/context";
import type { Country } from "../lib/api";
import { useHeroScale } from "../lib/hooks";
import { services } from "../i18n";

const SERVICE_HINTS: Record<string, string> = {
  contracting: "Service: structural and finishing works on site",
  fitout: "Service: close-up of stone floor meeting timber joinery",
  supply: "Service: curated materials and fixtures ready for delivery",
  "project-management": "Service: project manager reviewing progress on site",
};

export default function Home() {
  const { t, lp, lang } = useLang();
  const { data, error, reload } = useData();
  const [country, setCountry] = useState<"all" | Country>("all");
  const heroRef = useHeroScale<HTMLDivElement>();
  usePageMeta(t.home.title, t.home.description);

  const strip = useMemo(() => (data?.projects ?? []).filter((p) => p.featured && p.cover).slice(0, 8), [data]);

  const featured = useMemo(() => {
    const all = (data?.projects ?? []).filter((p) => p.featured);
    return all.filter((p) => country === "all" || p.country === country).slice(0, 6);
  }, [data, country]);

  return (
    <>
      {strip.length >= 3 ? (
        <>
          <ProjectStrip projects={strip} />
          <section className="intro">
            <div className="container">
              <h1 className="display">{t.home.h1}</h1>
              <p className="lead" style={{ maxWidth: 720 }}>{t.home.sub}</p>
              <div className="btn-row center btn-row--stack" style={{ marginTop: 12 }}>
                <Link to={lp("/contact")} className="btn">{t.cta}</Link>
                <Link to={lp("/projects")} className="link">{t.home.seeProjects}</Link>
              </div>
            </div>
          </section>
        </>
      ) : (
      <section className="hero" data-dark>
        <div className="hero__copy">
          <h1 className="display">{t.home.h1}</h1>
          <p className="lead">{t.home.sub}</p>
          <div className="btn-row center btn-row--stack" style={{ marginTop: 16 }}>
            <Link to={lp("/contact")} className="btn">{t.cta}</Link>
            <Link to={lp("/projects")} className="link">{t.home.seeProjects}</Link>
          </div>
        </div>
        <div className="hero__media" ref={heroRef}>
          <SitePhoto hideIfEmpty slot="home-hero" ratio="16/9" dark priority alt={t.home.heroAlt} hint="Hero: finished villa living room, warm daylight" sizes="(min-width:1440px) 1440px, 100vw" />
        </div>
      </section>
      )}

      <section className="section" aria-labelledby="services-title">
        <div className="container">
          <Reveal className="section-head">
            <h2 className="h2" id="services-title">{t.home.servicesTitle}</h2>
            <p className="lead">{t.home.servicesSub}</p>
          </Reveal>
          <div className="grid grid--4">
            {services[lang].map((s, i) => (
              <Reveal key={s.slug} delay={i * 80}>
                <ServiceTile to={lp(`/services/${s.slug}`)} title={s.title} text={s.text} slot={`service-${s.slug}`} hint={SERVICE_HINTS[s.slug]} />
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className="section section--surface" aria-labelledby="projects-title">
        <div className="container">
          <Reveal className="section-head section-head--row">
            <div>
              <h2 className="h2" id="projects-title">{t.home.projectsTitle}</h2>
              <p className="lead">{t.home.projectsSub}</p>
            </div>
            <Segmented
              label={t.filters.country}
              value={country}
              onChange={setCountry}
              options={[
                { value: "all" as const, label: t.filters.all },
                ...(["eg", "qa", "sa"] as Country[])
                  .filter((c) => (data?.projects ?? []).some((p) => p.country === c))
                  .map((c) => ({ value: c, label: t.filters[c] })),
              ]}
            />
          </Reveal>
          {!data && error ? (
            <div className="empty">
              <p>{t.projects.loadError}</p>
              <button className="btn btn--outline" onClick={reload}>↻</button>
            </div>
          ) : !data ? (
            <ProjectGridSkeleton />
          ) : (
            <div className="grid grid--3">
              {featured.map((p) => (
                <ProjectCard key={p.id} p={p} />
              ))}
            </div>
          )}
          <div style={{ marginTop: 48 }}>
            <Link to={lp("/projects")} className="link">{t.home.allProjects}</Link>
          </div>
        </div>
      </section>

      <HowWeWork />
      <ClientWall />
    </>
  );
}
