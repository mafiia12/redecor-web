import { useRef, useState, type KeyboardEvent } from "react";
import { DIVISIONS, TEAM, type Member } from "../content";
import { useLang } from "../lib/context";
import { SitePhoto } from "./Photo";
import { SectionHead } from "./SectionHead";

/** Side tabs (one per division); the panel shows its render (admin slot division-<id>), scope and the people leading it. */
export function Divisions({ index = "03" }: { index?: string }) {
  const { t, lang } = useLang();
  const [i, setI] = useState(0);
  const tabs = useRef<(HTMLButtonElement | null)[]>([]);
  const d = DIVISIONS[i];
  const leads = d.lead.map((n) => TEAM.find((m) => m.name.en === n)).filter((m): m is Member => !!m);
  const ceo = TEAM[0];

  const onKey = (e: KeyboardEvent) => {
    const step = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 }[e.key];
    if (!step) return;
    e.preventDefault();
    const next = (i + step + DIVISIONS.length) % DIVISIONS.length;
    setI(next);
    tabs.current[next]?.focus();
  };

  return (
    <section className="section" aria-labelledby="div-title">
      <div className="container">
        <SectionHead id="div-title" index={index} eyebrow={t.eyebrow.divisions} title={t.about.divisions} sub={t.about.divisionsSub} />
        <div className="divs">
          <div className="divs__tabs" role="tablist" aria-orientation="vertical" onKeyDown={onKey}>
            {DIVISIONS.map((x, k) => (
              <button
                key={x.id}
                ref={(el) => (tabs.current[k] = el)}
                role="tab"
                id={`div-tab-${x.id}`}
                aria-selected={k === i}
                aria-controls="div-panel"
                tabIndex={k === i ? 0 : -1}
                className={`divs__tab${k === i ? " is-on" : ""}`}
                onClick={() => setI(k)}
              >
                <span className="divs__n">{String(k + 1).padStart(2, "0")}</span>
                <span>{x.name[lang]}</span>
              </button>
            ))}
          </div>

          <div className="divs__panel" id="div-panel" role="tabpanel" aria-labelledby={`div-tab-${d.id}`} key={d.id}>
            <SitePhoto slot={`division-${d.id}`} ratio="16/9" alt={d.name[lang]} className="divs__img" sizes="(min-width:900px) 820px, 100vw" />
            <div className="divs__body">
              <div>
                <h3 className="divs__title">{d.name[lang]}</h3>
                <p className="divs__text">{d.text[lang]}</p>
                <ul className="divs__points">
                  {d.points[lang].map((p) => <li key={p}>{p}</li>)}
                </ul>
              </div>
              <aside className="divs__team" aria-label={t.about.team}>
                <span className="divs__label">{t.about.team}</span>
                {leads.length ? (
                  leads.map((m) => (
                    <p key={m.name.en} className="person">
                      <strong>{m.name[lang]}</strong>
                      <span>{m.title[lang]}</span>
                    </p>
                  ))
                ) : (
                  <p className="divs__soon">{t.about.teamSoon}</p>
                )}
              </aside>
            </div>
          </div>
        </div>

        {ceo && (
          <div className="lead-strip">
            <span className="divs__label">{t.about.leadership}</span>
            <p className="person">
              <strong>{ceo.name[lang]}</strong>
              <span>{ceo.title[lang]}</span>
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
