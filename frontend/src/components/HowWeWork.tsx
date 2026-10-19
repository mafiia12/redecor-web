import { useLang } from "../lib/context";
import { useMode } from "../lib/theme";
import { SitePhoto } from "./Photo";
import { Reveal } from "./Reveal";
import { SectionHead } from "./SectionHead";

/** Three fixed steps side by side. Each step shows its photo (admin slot how-we-work-N) when one is uploaded. */
export function HowWeWork({ index = "04" }: { index?: string }) {
  const { t } = useLang();
  const steps = t.how.steps;
  const dark = useMode() === "dark";
  return (
    <section className={`section steps-band${dark ? " section--dark" : " section--surface"}`} data-dark={dark || undefined} aria-labelledby="how-title">
      <div className="container">
        <SectionHead id="how-title" index={index} eyebrow={t.eyebrow.how} title={t.how.title} sub={t.how.sub} />
        <ol className="steps">
          {steps.map(([title, text], i) => (
            <Reveal as="li" key={i} delay={i * 60} className="steps__item">
                <SitePhoto slot={`how-we-work-${i + 1}`} ratio="4/3" alt={title} sizes="(min-width:900px) 380px, 100vw" />
                <div className="steps__head">
                  <span className="steps__num">{String(i + 1).padStart(2, "0")}</span>
                  <span className="steps__bar" aria-hidden="true" />
                </div>
                <h3 className="steps__title">{title}</h3>
                <p className="steps__text">{text}</p>
            </Reveal>
          ))}
        </ol>
      </div>
    </section>
  );
}
