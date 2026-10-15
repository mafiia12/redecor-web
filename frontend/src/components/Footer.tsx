import { Link } from "react-router-dom";
import { SOCIAL } from "../config";
import { isRealNumber, pick, useData, useLang, waDigits } from "../lib/context";
import { SitePhoto } from "./Photo";

export function Footer() {
  const { t, lp, lang } = useLang();
  const { data } = useData();
  const offices = data?.offices ?? [];
  const real = (v: string) => !!v && !v.includes("[");
  const unique = (xs: string[]) => [...new Set(xs.filter(real))];

  const locations = offices.map((o) => pick(o, "address", lang)).filter(real);
  const emails = unique(offices.map((o) => o.email));
  const phones = unique(offices.map((o) => o.phone));
  const socials = Object.entries(SOCIAL).filter(([, url]) => url);
  const nav = [
    [t.nav.services, lp("/services/fitout")],
    [t.nav.projects, lp("/projects")],
    [t.nav.about, lp("/about")],
    [t.nav.clients, lp("/#clients")],
    [t.nav.contact, lp("/contact")],
  ];

  return (
    <footer className="footer" data-dark>
      <div className="footer__split">
        <div className="footer__left">
          <SitePhoto slot="footer-bg" ratio="16/9" alt="" sizes="(min-width:900px) 66vw, 100vw" />
          <h2 className="footer__name">{t.brand}</h2>
          <div className="footer__cols">
            <div>
              <h3>{t.footer.location}</h3>
              {(locations.length ? locations : [t.brand]).slice(0, 2).map((l) => (
                <p key={l} style={{ marginBottom: 12 }}>{l}</p>
              ))}
            </div>
            <div>
              <h3>{t.footer.message}</h3>
              {emails.map((e) => (
                <p key={e}><a href={`mailto:${e}`}>{e}</a></p>
              ))}
            </div>
            <div>
              <h3>{t.footer.contact}</h3>
              {phones.map((n) => (
                <p key={n} dir="ltr" style={{ textAlign: lang === "ar" ? "right" : "left" }}>
                  {isRealNumber(n) ? <a href={`tel:+${waDigits(n)}`}>{n}</a> : n}
                </p>
              ))}
            </div>
          </div>
        </div>
        <div className="footer__right">
          <h3>{t.footer.follow}</h3>
          <ul className="footer__social-list" aria-label={t.footer.social}>
            {socials.map(([name, url]) => (
              <li key={name}>
                <a href={url} target="_blank" rel="noopener noreferrer">{name}</a>
              </li>
            ))}
          </ul>
        </div>
      </div>
      <div className="footer__sub">
        <div className="container footer__bottom" style={{ justifyContent: "space-between", flexWrap: "wrap", gap: "12px 24px" }}>
          <nav aria-label="Footer" style={{ display: "flex", flexWrap: "wrap", gap: "8px 24px" }}>
            {nav.map(([label, to]) => (
              <Link key={to} to={to}>{label}</Link>
            ))}
          </nav>
          <span style={{ display: "flex", flexWrap: "wrap", gap: "8px 24px", alignItems: "center" }}>
            <span style={{ color: "var(--faint-dark)", fontSize: 14 }}>{t.footer.copyright}</span>
            <Link to={lp("/privacy")}>{t.footer.privacy}</Link>
            <Link to="/admin">{t.footer.staff}</Link>
          </span>
        </div>
      </div>
    </footer>
  );
}
