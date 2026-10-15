import { useState, type ChangeEvent } from "react";
import { api, errorText, form, json, useLoad, type AdminSlot } from "./api";

export default function SiteImagesAdmin() {
  const { data, reload, error } = useLoad<AdminSlot[]>("/site-images");
  const [msg, setMsg] = useState("");

  const run = async (fn: () => Promise<unknown>) => {
    setMsg("");
    try {
      await fn();
      reload();
    } catch (e) {
      setMsg(errorText(e));
    }
  };
  const upload = (s: AdminSlot, e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (f) run(() => api(`/site-images/${s.slot}`, form("PUT", { file: f })));
  };

  return (
    <>
      <h1>Site images</h1>
      <p className="caption" style={{ marginBottom: 16 }}>Hero, service and “How we work” photos. Empty slots show a neutral placeholder on the site until a photo is added.</p>
      {(msg || error) && <div className="adm-msg err">{msg || error}</div>}
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {(data ?? []).map((s) => (
          <div className="adm-card adm-slot" key={s.slot}>
            <div className="prev">{s.image ? <img src={s.image.src} alt="" /> : "No image"}</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <strong>{s.label}</strong>
              <code style={{ fontSize: 12, color: "var(--muted)" }}>{s.slot}</code>
              <input type="file" accept="image/jpeg,image/png,image/webp" aria-label={`Upload ${s.label}`} onChange={(e) => upload(s, e)} />
              {s.image && (
                <>
                  <div className="adm-grid two">
                    <input className="input" placeholder="Alt text (English)" defaultValue={s.alt_en} onBlur={(e) => run(() => api(`/site-images/${s.slot}`, json("PATCH", { alt_en: e.target.value, alt_ar: s.alt_ar })))} />
                    <input className="input" dir="rtl" placeholder="النص البديل (عربي)" defaultValue={s.alt_ar} onBlur={(e) => run(() => api(`/site-images/${s.slot}`, json("PATCH", { alt_en: s.alt_en, alt_ar: e.target.value })))} />
                  </div>
                  <div><button className="btn btn--danger btn--sm" onClick={() => confirm("Remove this image?") && run(() => api(`/site-images/${s.slot}`, { method: "DELETE" }))}>Remove</button></div>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
