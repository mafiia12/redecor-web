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
      <section className="page-head">
        <div className="container">
          <h1 className="display">{t.about.title}</h1>
          <p className="lead">{t.about.sub}</p>
        </div>
      </section>
      <div className="cover ratio-mobile-45">
        <SitePhoto hideIfEmpty slot="about-hero" ratio="16/9" priority hint="About: team reviewing finishes on site" alt={t.about.title} sizes="(min-width:1440px) 1440px, 100vw" />
      </div>
      <section className="section">
        <div className="container">
          <Reveal className="prose">
            <p>
              {t.about.p1[0]}
              <strong>{t.about.p1[1]}</strong>
              {t.about.p1[2]}
            </p>
            <p>{t.about.p2}</p>
            <p className="h3" style={{ color: "var(--accent)", marginTop: 16 }}>{t.about.closing}</p>
          </Reveal>
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
