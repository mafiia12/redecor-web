import { useState } from "react";
import { DIVISIONS, TEAM } from "../content";
import { useLang } from "../lib/context";
import { Reveal } from "./Reveal";

/** Side-tab layout: pick a division on the side, read what it does and who leads it. */
export function Divisions() {
  const { t, lang } = useLang();
  const [i, setI] = useState(0);
  const d = DIVISIONS[i];
  const leads = d.lead.map((n) => TEAM.find((m) => m.name.en === n)).filter((m): m is (typeof TEAM)[number] => !!m);
  const ceo = TEAM[0];
  return (
    <section className="section section--tight" aria-labelledby="div-title">
      <div className="container">
        <Reveal className="section-head">
          <h2 className="h2" id="div-title">{t.about.divisions}</h2>
          <p className="lead">{t.about.divisionsSub}</p>
        </Reveal>
        <div className="divs">
          <div className="divs__tabs" role="tablist" aria-orientation="vertical">
            {DIVISIONS.map((x, k) => (
              <button
                key={x.id}
                role="tab"
                id={`div-tab-${x.id}`}
                aria-selected={k === i}
                aria-controls="div-panel"
                className={`divs__tab${k === i ? " is-on" : ""}`}
                onClick={() => setI(k)}
              >
                <span>{String(k + 1).padStart(2, "0")}</span>
                {x.name[lang]}
              </button>
            ))}
          </div>
          <div className="divs__panel" id="div-panel" role="tabpanel" aria-labelledby={`div-tab-${d.id}`} key={d.id}>
            <h3>{d.name[lang]}</h3>
            <p>{d.text[lang]}</p>
            <ul className="divs__points">
              {d.points[lang].map((p) => <li key={p}>{p}</li>)}
            </ul>
            <div className="divs__team">
              <span className="kicker">{t.about.team}</span>
              {leads.length ? (
                <ul>
                  {leads.map((m) => (
                    <li key={m.name.en}>
                      <strong>{m.name[lang]}</strong>
                      <span>{m.title[lang]}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="divs__soon">{t.about.teamSoon}</p>
              )}
              <p className="divs__ceo">{t.about.leadership}: {ceo.name[lang]}, {ceo.title[lang]}</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
