import { useLang } from "../lib/context";
import { Reveal } from "./Reveal";

/** One large sentence from the owner (dictionary key home.philosophy). Hidden while the text is empty. */
export function Statement() {
  const { t } = useLang();
  const { quote, by } = t.home.philosophy;
  if (!quote.trim()) return null;
  return (
    <section className="section statement" aria-label={by || undefined}>
      <Reveal className="container statement__inner">
        <blockquote className="statement__quote">
          <p>{quote}</p>
          {by && <footer className="statement__by">{by}</footer>}
        </blockquote>
      </Reveal>
    </section>
  );
}
