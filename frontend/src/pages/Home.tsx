import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ProjectGridSkeleton } from "../components/Cards";
import { SectionHead } from "../components/SectionHead";
import { Segmented } from "../components/Filters";
import { ClientWall } from "../components/ClientWall";
import { Testimonials } from "../components/Testimonials";
import { Divisions } from "../components/Divisions";
import { HowWeWork } from "../components/HowWeWork";
import { SitePhoto } from "../components/Photo";
import { ProjectStrip } from "../components/ProjectStrip";
import { ProjectCollection } from "../components/ProjectIndex";
import { Statement } from "../components/Statement";
import { Faq } from "../components/Faq";
import { useData, useLang, usePageMeta } from "../lib/context";
import type { Country } from "../lib/api";
import { useHeroScale } from "../lib/hooks";
import { useMode } from "../lib/theme";
import { services } from "../i18n";

export default function Home() {
  const { t, lp, lang } = useLang();
  const { data, error, reload } = useData();
  const [country, setCountry] = useState<"all" | Country>("all");
  const heroRef = useHeroScale<HTMLDivElement>();
  const dark = useMode() === "dark";
  const hasHeroImg = !!data?.site_images["home-hero"];
  usePageMeta(t.home.title, t.home.description);

  const strip = useMemo(() => (data?.projects ?? []).filter((p) => p.featured && p.cover).slice(0, 8), [data]);

  const featured = useMemo(() => {
    const all = (data?.projects ?? []).filter((p) => p.featured);
    return all.filter((p) => country === "all" || p.country === country).slice(0, 6);
  }, [data, country]);

  return (
    <>
      {strip.length >= 3 && <ProjectStrip projects={strip} />}
      <section className={`lead-hero${strip.length >= 3 ? " lead-hero--after-strip" : ""}${hasHeroImg ? " lead-hero--img" : ""}`} data-dark={dark || hasHeroImg || undefined}>
        {hasHeroImg && (
          <div className="lead-hero__bg" ref={heroRef}>
            <SitePhoto slot="home-hero" ratio="16/9" priority alt={t.home.heroAlt} sizes="100vw" />
          </div>
        )}
        <div className="container lead-hero__inner">
          <img className="lead-hero__logo" src={dark || hasHeroImg ? "/logo-light.svg" : "/logo-ink.svg"} alt={t.brand} width={420} height={240} />
          <div className="lead-hero__bottom">
            <h1 className="lead-hero__h1">{t.home.h1}</h1>
            <div className="lead-hero__row">
              <p>{t.home.sub}</p>
              <div className="lead-hero__ctas">
                <Link to={lp("/contact")} className="btn" data-track="cta">{t.cta}</Link>
                <Link to={lp("/projects")} className="btn btn--quiet">{t.home.ourWork}</Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="section" aria-labelledby="services-title">
        <div className="container">
          <SectionHead id="services-title" index="01" eyebrow={t.eyebrow.services} title={t.home.servicesTitle} sub={t.home.servicesSub} />
          <ul className="svc">
            {services[lang].map((s, i) => (
              <li key={s.slug}>
                <Link to={lp(`/services/${s.slug}`)} className="svc__row">
                  <span className="svc__n">{String(i + 1).padStart(2, "0")}</span>
                  <span className="svc__title">{s.title}</span>
                  <span className="svc__text">{s.text}</span>
                  <span className="svc__thumb"><SitePhoto slot={`service-${s.slug}`} ratio="4/3" alt="" sizes="160px" /></span>
                  <span className="svc__arrow" aria-hidden="true">→</span>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {!(data && data.projects.length === 0) && (
      <section className="section section--surface" aria-labelledby="projects-title">
        <div className="container">
          <SectionHead
            id="projects-title"
            index="02"
            eyebrow={t.eyebrow.projects}
            title={t.home.projectsTitle}
            sub={t.home.projectsSub}
            aside={new Set((data?.projects ?? []).map((p) => p.country)).size > 1 && <Segmented
              label={t.filters.country}
              value={country}
              onChange={setCountry}
              options={[
                { value: "all" as const, label: t.filters.all },
                ...(["eg", "qa", "sa"] as Country[])
                  .filter((c) => (data?.projects ?? []).some((p) => p.country === c))
                  .map((c) => ({ value: c, label: t.filters[c] })),
              ]}
            />}
          />
          {!data && error ? (
            <div className="empty">
              <p>{t.projects.loadError}</p>
              <button className="btn btn--outline" onClick={reload}>↻</button>
            </div>
          ) : !data ? (
            <ProjectGridSkeleton />
          ) : (
            <ProjectCollection projects={featured} />
          )}
          <div style={{ marginTop: 48 }}>
            <Link to={lp("/projects")} className="link">{t.home.allProjects}</Link>
          </div>
        </div>
      </section>
      )}

      <Statement />
      <Divisions />
      <HowWeWork />
      <ClientWall />
      <Testimonials />
      <Faq />
    </>
  );
}
