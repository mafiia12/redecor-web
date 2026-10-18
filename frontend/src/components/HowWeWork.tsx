import { useEffect, useRef, useState } from "react";
import { useData, useLang } from "../lib/context";
import { Reveal } from "./Reveal";
import { SitePhoto } from "./Photo";

export function HowWeWork() {
  const { t } = useLang();
  const site = useData().data;
  const hasImgs = !!site?.site_images["how-we-work-1"];
  const [active, setActive] = useState(0);
  const steps = useRef<(HTMLElement | null)[]>([]);

  // The chapter crossing the middle of the viewport becomes active (desktop sticky image follows it).
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) setActive(Number((e.target as HTMLElement).dataset.i));
        }
      },
      { rootMargin: "-45% 0px -45% 0px" },
    );
    steps.current.forEach((el) => el && io.observe(el));
    return () => io.disconnect();
  }, []);

  const data = t.how.steps;
  return (
    <section className="section section--dark" data-dark aria-labelledby="how-title">
      <div className="container">
        <Reveal className="section-head">
          <h2 className="h2" id="how-title">{t.how.title}</h2>
          <p className="lead">{t.how.sub}</p>
        </Reveal>
        <div className={`how__grid${hasImgs ? "" : " how__grid--text"}`}>
          {hasImgs && <div className="how__sticky" aria-hidden="true">
            <div className="stack-img">
              {data.map(([, , hint], i) => (
                <SitePhoto key={i} slot={`how-we-work-${i + 1}`} hint={hint} ratio="4/5" dark className={i === active ? "is-active" : ""} sizes="(min-width:900px) 560px, 100vw" />
              ))}
            </div>
            <p className="cap">{String(active + 1).padStart(2, "0")} · {data[active][0]}</p>
          </div>}
          <div>
            {data.map(([title, text, hint], i) => (
              <article
                key={i}
                data-i={i}
                ref={(el) => (steps.current[i] = el)}
                className={`how__step${i === active ? " is-active" : ""}`}
              >
                <SitePhoto slot={`how-we-work-${i + 1}`} hint={hint} ratio="4/3" dark alt={title} sizes="100vw" />
                <span className="how__num">{String(i + 1).padStart(2, "0")}</span>
                <h3 className="how__title">{title}</h3>
                <p className="how__text">{text}</p>
              </article>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
