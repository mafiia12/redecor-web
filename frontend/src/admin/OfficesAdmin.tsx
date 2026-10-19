import { useEffect, useState } from "react";
import type { Office } from "../lib/api";
import { api, errorText, json, useLoad } from "./api";

function OfficeForm({ o }: { o: Office }) {
  const [v, setV] = useState(o);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  useEffect(() => setV(o), [o]);
  const f = (k: keyof Office, label: string, extra: { area?: boolean; rtl?: boolean; ltr?: boolean } = {}) => (
    <label className="f">
      {label}
      {extra.area ? (
        <textarea className="textarea" dir={extra.rtl ? "rtl" : undefined} value={v[k]} onChange={(e) => setV({ ...v, [k]: e.target.value })} />
      ) : (
        <input className="input" dir={extra.rtl ? "rtl" : extra.ltr ? "ltr" : undefined} value={v[k]} onChange={(e) => setV({ ...v, [k]: e.target.value })} />
      )}
    </label>
  );
  async function save() {
    try {
      const { country, ...body } = v;
      await api(`/offices/${country}`, json("PUT", body));
      setMsg({ ok: true, text: "Saved." });
    } catch (e) {
      setMsg({ ok: false, text: errorText(e) });
    }
  }
  return (
    <div className="adm-card" style={{ marginBottom: 20 }}>
      <h2 style={{ marginTop: 0 }}>{o.country === "eg" ? "Egypt office" : "Qatar office"}</h2>
      {msg && <div className={`adm-msg${msg.ok ? "" : " err"}`}>{msg.text}</div>}
      <div className="adm-grid two">
        {f("address_en", "Address (English)", { area: true })}
        {f("address_ar", "Address (Arabic)", { area: true, rtl: true })}
        {f("phone", "Phone (international format, e.g. +20 100 000 0000)", { ltr: true })}
        {f("whatsapp", "WhatsApp number (leave empty to use the phone)", { ltr: true })}
        {f("email", "Email", { ltr: true })}
        {f("maps_url", "Google Maps link (optional)", { ltr: true })}
        {f("hours_en", "Hours (English)")}
        {f("hours_ar", "Hours (Arabic)", { rtl: true })}
      </div>
      <div style={{ marginTop: 16 }}><button className="btn" onClick={save}>Save</button></div>
    </div>
  );
}

export default function OfficesAdmin() {
  const { data, error } = useLoad<Office[]>("/offices");
  return (
    <>
      <h1>Offices</h1>
      <p className="caption" style={{ marginBottom: 16 }}>Values in [brackets] are placeholders. Real phone numbers turn the WhatsApp button, footer and contact page into live links.</p>
      {error && <div className="adm-msg err">{error}</div>}
      {(data ?? []).map((o) => <OfficeForm key={o.country} o={o} />)}
    </>
  );
}
