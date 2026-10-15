import { api, errorText, json, useLoad, type AdminEnquiry } from "./api";
import { useState } from "react";

export default function EnquiriesAdmin() {
  const { data, error, setData } = useLoad<AdminEnquiry[]>("/enquiries");
  const [msg, setMsg] = useState("");

  async function setStatus(e: AdminEnquiry, status: AdminEnquiry["status"]) {
    try {
      const u = await api<AdminEnquiry>(`/enquiries/${e.id}`, json("PATCH", { status }));
      setData((d) => d?.map((x) => (x.id === u.id ? u : x)) ?? d);
    } catch (x) {
      setMsg(errorText(x));
    }
  }
  const fmt = (s: string) => new Date(s).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" });

  return (
    <>
      <h1>Enquiries</h1>
      {(msg || error) && <div className="adm-msg err">{msg || error}</div>}
      {data && data.length === 0 && <p className="caption">No enquiries yet.</p>}
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {(data ?? []).map((e) => (
          <article className="adm-card" key={e.id}>
            <div className="adm-bar" style={{ marginBottom: 8 }}>
              <strong>{e.name}</strong>
              <div className="adm-row">
                <span className="caption">{fmt(e.created_at)}</span>
                <select className="select" style={{ width: 140 }} value={e.status} aria-label="Status" onChange={(ev) => setStatus(e, ev.target.value as AdminEnquiry["status"])}>
                  <option value="new">New</option>
                  <option value="contacted">Contacted</option>
                  <option value="closed">Closed</option>
                </select>
              </div>
            </div>
            <div className="adm-row" style={{ gap: 16, marginBottom: 8 }}>
              <a href={`tel:${e.phone.replace(/\s/g, "")}`} dir="ltr">{e.phone}</a>
              {e.email && <a href={`mailto:${e.email}`}>{e.email}</a>}
              <span className="adm-tag">{e.country.toUpperCase()}</span>
              <span className="adm-tag">{e.service}</span>
              {e.project_type && <span className="adm-tag">{e.project_type}</span>}
              {e.area_m2 != null && <span className="adm-tag">{e.area_m2} m²</span>}
              <span className="adm-tag">prefers {e.contact_method}</span>
              <span className="adm-tag">{e.lang}</span>
            </div>
            {e.message && <p style={{ whiteSpace: "pre-wrap", margin: 0 }}>{e.message}</p>}
          </article>
        ))}
      </div>
    </>
  );
}
