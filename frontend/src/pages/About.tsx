import { OfficeCard } from "../components/OfficeCard";
import { HowWeWork } from "../components/HowWeWork";
import { SitePhoto } from "../components/Photo";
import { Reveal } from "../components/Reveal";
import { useData, useLang, usePageMeta } from "../lib/context";

export default function About() {
  const { t } = useLang();
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
        <SitePhoto slot="about-hero" ratio="16/9" priority hint="About: team reviewing finishes on site" alt={t.about.title} sizes="(min-width:1440px) 1440px, 100vw" />
      </div>
      <section className="section">
        <div className="container">
          <Reveal className="section-head">
            <h2 className="h2">{t.about.story}</h2>
          </Reveal>
          <Reveal className="prose">
            {t.about.paras.map((p, i) => (
              <p key={i}>{p}</p>
            ))}
          </Reveal>
        </div>
      </section>
      <HowWeWork />
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
