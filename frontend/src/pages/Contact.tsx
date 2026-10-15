import { EnquiryForm } from "../components/EnquiryForm";
import { OfficeCard } from "../components/OfficeCard";
import { Reveal } from "../components/Reveal";
import { useData, useLang, usePageMeta } from "../lib/context";

export default function Contact() {
  const { t } = useLang();
  const { data } = useData();
  usePageMeta(`${t.contact.title} | ${t.brand}`, t.contact.sub);
  return (
    <>
      <section className="page-head">
        <div className="container">
          <h1 className="display">{t.contact.title}</h1>
          <p className="lead">{t.contact.sub}</p>
        </div>
      </section>
      <section className="section section--tight-top" style={{ paddingBottom: 80 }}>
        <div className="container">
          <div className="grid grid--2" style={{ gap: 24 }}>
            {(data?.offices ?? []).map((o) => (
              <OfficeCard key={o.country} office={o} />
            ))}
          </div>
        </div>
      </section>
      <section className="section section--tight-top" style={{ paddingBottom: "var(--section-y)" }}>
        <div className="container stack" style={{ gap: 40 }}>
          <Reveal className="stack" >
            <h2 className="h2">{t.contact.formTitle}</h2>
            <p className="lead" style={{ marginTop: 16 }}>{t.contact.formSub}</p>
          </Reveal>
          <EnquiryForm />
        </div>
      </section>
    </>
  );
}
