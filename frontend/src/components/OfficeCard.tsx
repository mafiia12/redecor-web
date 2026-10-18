import type { Office } from "../lib/api";
import { isRealNumber, pick, useLang, waDigits, waLink } from "../lib/context";

export function OfficeCard({ office }: { office: Office }) {
  const { t, lang } = useLang();
  const address = pick(office, "address", lang);
  const hours = pick(office, "hours", lang);
  const wa = office.whatsapp || office.phone;
  const maps =
    office.maps_url ||
    (address && !address.includes("[")
      ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address.replace(/\n/g, ", "))}`
      : "");
  const ok = (v: string) => !!v && !v.includes("[");
  const rows: [string, React.ReactNode, string][] = [
    [t.office.rows[0], address, address],
    [t.office.rows[1], isRealNumber(office.phone) ? <a className="ltr" href={`tel:+${waDigits(office.phone)}`}>{office.phone}</a> : <span className="ltr">{office.phone}</span>, office.phone],
    [t.office.rows[2], isRealNumber(wa) ? <a className="ltr" href={waLink(wa)} target="_blank" rel="noopener noreferrer">{wa}</a> : <span className="ltr">{wa}</span>, wa],
    [t.office.rows[3], office.email.includes("@") && !office.email.includes("[") ? <a className="ltr" href={`mailto:${office.email}`}>{office.email}</a> : <span className="ltr">{office.email}</span>, office.email],
    [t.office.rows[4], hours, hours],
  ];
  return (
    <section className="office" aria-label={t.countries[office.country]}>
      <div className="stack" style={{ gap: 8 }}>
        <span className="kicker">{t.office.kicker}</span>
        <h3 className="h3 h3--xl">{t.countries[office.country]}</h3>
      </div>
      <dl>
        {rows.filter(([, , raw]) => ok(raw)).map(([label, value]) => (
          <div key={label} style={{ display: "contents" }}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      {maps && (
        <a className="link" href={maps} target="_blank" rel="noopener noreferrer">
          {t.office.maps}
        </a>
      )}
    </section>
  );
}
