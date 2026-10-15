import { Link } from "react-router-dom";
import { SOCIAL } from "../config";
import { pick, useData, useLang } from "../lib/context";

const ICONS: Record<string, string> = {
  LinkedIn: "M6 3h12a3 3 0 0 1 3 3v12a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3V6a3 3 0 0 1 3-3z M8 10.5v6 M8 7.6v.1 M11.5 16.5v-6 M11.5 13.2c0-1.6 1.1-2.7 2.5-2.7s2.5 1.1 2.5 2.7v3.3",
  Facebook: "M15.5 3.5H14a3.5 3.5 0 0 0-3.5 3.5v13.5 M7.5 10.5h7.5",
  Instagram: "M7 3h10a4 4 0 0 1 4 4v10a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V7a4 4 0 0 1 4-4z M12 8.25a3.75 3.75 0 1 0 0 7.5a3.75 3.75 0 1 0 0-7.5z M17.3 6.6v.1",
  TikTok: "M13.5 3v11.25a3.75 3.75 0 1 1-3.75-3.75 M13.5 3c.4 2.6 2.4 4.6 5 4.9",
};

export function Footer() {
  const { t, lp, lang } = useLang();
  const { office } = useData();
  const nav = [
    [t.nav.services, lp("/services/fitout")],
    [t.nav.projects, lp("/projects")],
    [t.nav.about, lp("/about")],
    [t.nav.clients, lp("/#clients")],
    [t.nav.contact, lp("/contact")],
  ];
  const socials = Object.entries(SOCIAL).filter(([, url]) => url);

  return (
    <footer className="footer" data-dark>
      <div className="container">
        <div className="footer__grid">
          <div className="footer__brand">
            <img src="/logo-light.svg" alt={t.brand} width={68} height={40} loading="lazy" />
            <p>{t.footer.tagline}</p>
            {socials.length > 0 && (
              <div className="footer__social" aria-label={t.footer.social}>
                {socials.map(([name, url]) => (
                  <a key={name} href={url} target="_blank" rel="noopener noreferrer" aria-label={name}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d={ICONS[name]} />
                    </svg>
                  </a>
                ))}
              </div>
            )}
          </div>
          <div>
            <h3>{t.footer.explore}</h3>
            <ul>
              {nav.map(([label, to]) => (
                <li key={to}>
                  <Link to={to}>{label}</Link>
                </li>
              ))}
            </ul>
          </div>
          {(["eg", "qa"] as const).map((c) => {
            const o = office(c);
            return (
              <div key={c}>
                <h3>{c === "eg" ? t.footer.egypt : t.footer.qatar}</h3>
                {o && (
                  <address>
                    <span style={{ whiteSpace: "pre-line" }}>{pick(o, "address", lang)}</span>
                    <br />
                    <span className="ltr">{o.phone}</span>
                    <br />
                    <span className="ltr">{o.email}</span>
                  </address>
                )}
              </div>
            );
          })}
        </div>
        <div className="footer__bottom">
          <span>{t.footer.copyright}</span>
          <span style={{ display: "flex", gap: 24 }}>
            <Link to={lp("/privacy")}>{t.footer.privacy}</Link>
            <Link to="/admin">{t.footer.staff}</Link>
          </span>
        </div>
      </div>
    </footer>
  );
}
