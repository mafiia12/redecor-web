import { EnquiryForm } from "../components/EnquiryForm";
import { OfficeCard } from "../components/OfficeCard";
import { Reveal } from "../components/Reveal";
import { useData, useLang, usePageMeta } from "../lib/context";

export default function Contact() {
  const { t } = useLang();
  const { data } = useData();
  usePageMeta(`${t.contact.kicker} | ${t.brand}`, t.contact.sub);
  return (
    <>
      <section className="page-head">
        <div className="container">
          <span className="kicker">{t.contact.kicker}</span>
          <h1 className="display">{t.contact.title}</h1>
          <p className="lead">{t.contact.sub}</p>
        </div>
      </section>
      <section className="section section--tight-top">
        <div className="container contact-grid">
          <div className="contact-grid__form">
            <Reveal className="stack">
              <h2 className="h2">{t.contact.formTitle}</h2>
              <p className="lead" style={{ marginTop: 16 }}>{t.contact.formSub}</p>
            </Reveal>
            <EnquiryForm />
          </div>
          <aside className="contact-grid__offices">
            {(data?.offices ?? []).map((o) => (
              <OfficeCard key={o.country} office={o} />
            ))}
          </aside>
        </div>
      </section>
    </>
  );
}
