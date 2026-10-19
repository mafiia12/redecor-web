import { useLang } from "../lib/context";
import { SectionHead } from "./SectionHead";

/** Questions and answers from the owner (dictionary key faq.items). Native <details>: keyboard and
 *  screen-reader friendly with no script. Hidden while there are no items. */
export function Faq({ index }: { index?: string }) {
  const { t } = useLang();
  const items = t.faq.items.filter(([q, a]) => q.trim() && a.trim());
  if (!items.length) return null;
  return (
    <section className="section" aria-labelledby="faq-title">
      <div className="container">
        <SectionHead id="faq-title" index={index} eyebrow={t.faq.eyebrow} title={t.faq.title} sub={t.faq.sub || undefined} />
        <div className="faq">
          {items.map(([q, a], i) => (
            <details key={i} className="faq__item">
              <summary className="faq__q">
                <span>{q}</span>
                <span className="faq__icon" aria-hidden="true" />
              </summary>
              <div className="faq__a">
                {a.split(/\n{2,}/).map((para, j) => <p key={j}>{para}</p>)}
              </div>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
