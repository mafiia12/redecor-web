import { OfficeCard } from "../components/OfficeCard";
import { HowWeWork } from "../components/HowWeWork";
import { SitePhoto } from "../components/Photo";
import { Reveal } from "../components/Reveal";
import { SHOW_TEAM, TEAM } from "../content";
import { useData, useLang, usePageMeta } from "../lib/context";

export default function About() {
  const { t, lang } = useLang();
  const { data } = useData();
  usePageMeta(`${t.about.title} | ${t.brand}`, t.about.sub);
  return (
    <>
      <section className="about-hero">
        <div className="about-hero__text">
          <h1 className="about-hero__title">
            {t.about.name}
            <span>{t.about.label}</span>
          </h1>
          <h2 className="about-hero__sub">{t.about.sub}</h2>
          <p>
            {t.about.p1[0]}
            <strong style={{ color: "var(--ink)" }}>{t.about.p1[1]}</strong>
            {t.about.p1[2]}
          </p>
          <p>{t.about.p2}</p>
          <p className="about-hero__closing">{t.about.closing}</p>
        </div>
        <div className="about-hero__img">
          <SitePhoto hideIfEmpty slot="about-hero" ratio="4/5" priority alt={t.about.title} sizes="(min-width:900px) 45vw, 100vw" />
        </div>
      </section>
      <section className="section section--surface" aria-label={t.about.title}>
        <div className="container">
          <Reveal>
            <dl className="stats">
              {t.about.stats.map(([n, label]) => (
                <div key={label}>
                  <dd className="stats__n">{n}</dd>
                  <dt className="stats__l">{label}</dt>
                </div>
              ))}
            </dl>
          </Reveal>
        </div>
      </section>
      <section className="section">
        <div className="container grid grid--2" style={{ gap: 48 }}>
          <Reveal className="stack" >
            <span className="kicker">{t.about.vision}</span>
            <p className="h3 h3--xl" style={{ marginTop: 16 }}>{t.about.visionText}</p>
          </Reveal>
          <Reveal className="stack" delay={80}>
            <span className="kicker">{t.about.mission}</span>
            <p className="h3 h3--xl" style={{ marginTop: 16 }}>{t.about.missionText}</p>
          </Reveal>
        </div>
      </section>
      <HowWeWork />
      {SHOW_TEAM && (
        <section className="section section--surface">
          <div className="container">
            <Reveal className="section-head">
              <h2 className="h2">{t.about.team}</h2>
            </Reveal>
            <ul className="team">
              {TEAM.map((m) => (
                <li key={m.name.en}>
                  <strong>{m.name[lang]}</strong>
                  <span>{m.title[lang]}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}
      <section className="section">
        <div className="container">
          <Reveal className="section-head">
            <h2 className="h2">{t.about.offices}</h2>
            <p className="lead">{t.about.officesSub}</p>
          </Reveal>
          <div className="grid grid--2" style={{ gap: 24 }}>
            {(data?.offices ?? []).map((o) => (
              <OfficeCard key={o.country} office={o} />
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
