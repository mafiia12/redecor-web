import type { CSSProperties } from "react";
import { useData, useLang } from "../lib/context";
import { Reveal } from "./Reveal";
import { SectionHead } from "./SectionHead";

/** Columns that divide the logo count evenly, so the last row is never half empty. */
function columns(n: number) {
  for (const c of [6, 5, 4]) if (n % c === 0) return c;
  return n < 4 ? Math.max(n, 1) : 4;
}

export function ClientWall() {
  const { t } = useLang();
  const { data } = useData();
  const clients = (data?.clients ?? []).filter((c) => c.logo);
  if (data && clients.length === 0) return null;

  return (
    <section className="section section--paper" id="clients" aria-labelledby="clients-title">
      <div className="container">
        <SectionHead id="clients-title" index="05" eyebrow={t.eyebrow.clients} title={t.clients.title} sub={t.clients.sub} />
        <Reveal>
          <ul className="logos" style={{ "--cols": columns(clients.length) } as CSSProperties}>
            {clients.map((c) => {
              const img = <img src={c.logo!.src} srcSet={c.logo!.srcset} sizes="160px" alt={c.name} loading="lazy" width={c.logo!.width} height={c.logo!.height} />;
              return (
                <li key={c.id} className="logos__cell" title={c.name}>
                  {c.url ? <a href={c.url} target="_blank" rel="noopener noreferrer" aria-label={c.name}>{img}</a> : img}
                </li>
              );
            })}
          </ul>
        </Reveal>
      </div>
    </section>
  );
}
