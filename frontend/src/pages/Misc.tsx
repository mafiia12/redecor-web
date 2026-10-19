import { useLang, usePageMeta } from "../lib/context";

export default function Privacy() {
  const { t } = useLang();
  usePageMeta(`${t.privacy.title} | ${t.brand}`);
  return (
    <section className="page-head">
      <div className="container">
        <h1 className="display">{t.privacy.title}</h1>
        <p className="prose">{t.privacy.body}</p>
      </div>
    </section>
  );
}
