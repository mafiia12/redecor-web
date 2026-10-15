import { Link } from "react-router-dom";
import { useLang } from "../lib/context";
import { Reveal } from "./Reveal";
import { openWhatsApp } from "./WhatsApp";

export function CtaBand({ title, sub }: { title?: string; sub?: string }) {
  const { t, lp } = useLang();
  return (
    <section className="section section--dark" data-dark>
      <Reveal className="container stack center" >
        <div className="stack center" style={{ gap: 40 }}>
          <div className="stack center" style={{ gap: 20 }}>
            <h2 className="h2">{title ?? t.cta2.title}</h2>
            <p className="lead" style={{ maxWidth: 640 }}>{sub ?? t.cta2.sub}</p>
          </div>
          <div className="btn-row center btn-row--stack">
            <Link to={lp("/contact")} className="btn">
              {t.cta}
            </Link>
            <button type="button" className="btn btn--outline" onClick={openWhatsApp}>
              {t.cta2.wa}
            </button>
          </div>
        </div>
      </Reveal>
    </section>
  );
}
