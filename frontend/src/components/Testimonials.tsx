import { loc, useData, useLang } from "../lib/context";
import { SectionHead } from "./SectionHead";

/** Client quotes. The server only sends quotes that are published AND whose written approval is recorded;
 *  with none, the section does not render at all. */
export function Testimonials() {
  const { t, lang } = useLang();
  const { data } = useData();
  const items = data?.testimonials ?? [];
  if (!items.length) return null;
  return (
    <section className="section" aria-labelledby="quotes-title">
      <div className="container">
        <SectionHead id="quotes-title" title={t.about.testimonials} />
        <div className="quotes">
          {items.map((q) => {
            const quote = loc(q, "quote", lang);
            const role = loc(q, "role", lang);
            return (
              <figure key={q.id} className="quote">
                <blockquote {...quote.attrs}>{quote.text}</blockquote>
                <figcaption>
                  <strong>{q.author}</strong>
                  <span {...role.attrs}>{[role.text, q.company].filter(Boolean).join(", ")}</span>
                </figcaption>
              </figure>
            );
          })}
        </div>
      </div>
    </section>
  );
}
