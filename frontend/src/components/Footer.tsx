import { Link } from "react-router-dom";
import { SOCIAL } from "../config";
import { services } from "../i18n";
import { isRealNumber, pick, useData, useLang, waDigits } from "../lib/context";
import { openWhatsApp } from "./WhatsApp";

const real = (v?: string) => !!v && !v.includes("[");

export function Footer() {
  const { t, lp, lang } = useLang();
  const { data } = useData();
  const offices = data?.offices ?? [];
  const eg = offices.find((o) => o.country === "eg") ?? offices[0];
  const address = eg ? pick(eg, "address", lang) : "";
  const email = offices.map((o) => o.email).find(real);
  const phone = offices.map((o) => o.phone).find(real);
  const maps = offices.map((o) => o.maps_url).find(real);
  const socials = Object.entries(SOCIAL).filter(([, url]) => url);
  const company = [
    [t.nav.projects, lp("/projects")],
    [t.nav.about, lp("/about")],
    [t.nav.clients, lp("/#clients")],
    [t.nav.contact, lp("/contact")],
  ];

  return (
    <footer className="ft" data-dark>
      <div className="container">
        <div className="ft__top">
          <div className="ft__brand">
            <img src="/logo-light.svg" alt={t.brand} width={150} height={86} loading="lazy" />
            <p className="ft__statement">{t.footer.statement}</p>
            <p className="ft__tag">{t.footer.tagline}</p>
          </div>

          <nav className="ft__col" aria-label={t.footer.services}>
            <h3>{t.footer.services}</h3>
            <ul>
              {services[lang].map((s) => (
                <li key={s.slug}><Link to={lp(`/services/${s.slug}`)}>{s.title}</Link></li>
              ))}
            </ul>
          </nav>

          <nav className="ft__col" aria-label={t.footer.company}>
            <h3>{t.footer.company}</h3>
            <ul>
              {company.map(([label, to]) => (
                <li key={to}><Link to={to}>{label}</Link></li>
              ))}
            </ul>
          </nav>

          <div className="ft__col">
            <h3>{t.footer.contact}</h3>
            <ul>
              {real(address) && <li className="ft__addr">{address}</li>}
              {email && <li><a href={`mailto:${email}`}>{email}</a></li>}
              {phone && (
                <li dir="ltr" className="ft__ltr">
                  {isRealNumber(phone) ? <a href={`tel:+${waDigits(phone)}`}>{phone}</a> : phone}
                </li>
              )}
              <li><button type="button" className="ft__link" onClick={openWhatsApp}>{t.footer.whatsapp}</button></li>
              {maps && <li><a href={maps} target="_blank" rel="noopener noreferrer">{t.footer.directions} ↗</a></li>}
            </ul>
          </div>

          {socials.length > 0 && (
            <div className="ft__col">
              <h3>{t.footer.follow}</h3>
              <ul aria-label={t.footer.social}>
                {socials.map(([name, url]) => (
                  <li key={name}><a href={url} target="_blank" rel="noopener noreferrer">{name} ↗</a></li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="ft__bottom">
          <span>{t.footer.copyright}</span>
          <span className="ft__legal">
            <Link to={lp("/privacy")}>{t.footer.privacy}</Link>
            <Link to="/admin">{t.footer.staff}</Link>
          </span>
        </div>
      </div>
    </footer>
  );
}
