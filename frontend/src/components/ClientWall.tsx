import { useData, useLang } from "../lib/context";
import { Reveal } from "./Reveal";

export function ClientWall() {
  const { t } = useLang();
  const { data } = useData();
  const clients = data?.clients ?? [];
  if (data && clients.length === 0) return null;

  return (
    <section className="section" id="clients" aria-labelledby="clients-title">
      <div className="container">
        <Reveal className="section-head">
          <h2 className="h2" id="clients-title">{t.clients.title}</h2>
          <p className="lead">{t.clients.sub}</p>
        </Reveal>
        <Reveal>
          <ul className="clients" style={{ listStyle: "none", margin: 0, padding: 0 }}>
            {clients.map((c) => (
              <li key={c.id} className="client">
                {c.logo ? (
                  c.url ? (
                    <a href={c.url} target="_blank" rel="noopener noreferrer" aria-label={c.name}>
                      <img src={c.logo.src} srcSet={c.logo.srcset} sizes="136px" alt={c.name} loading="lazy" width={c.logo.width} height={c.logo.height} />
                    </a>
                  ) : (
                    <img src={c.logo.src} srcSet={c.logo.srcset} sizes="136px" alt={c.name} loading="lazy" width={c.logo.width} height={c.logo.height} />
                  )
                ) : (
                  <span className="client__ph">{t.clients.logo}</span>
                )}
              </li>
            ))}
          </ul>
        </Reveal>
      </div>
    </section>
  );
}
