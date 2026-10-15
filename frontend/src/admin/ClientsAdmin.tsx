import { useState, type ChangeEvent } from "react";
import { api, errorText, form, json, useLoad, type AdminClient } from "./api";

export default function ClientsAdmin() {
  const { data, reload, error } = useLoad<AdminClient[]>("/clients");
  const [name, setName] = useState("");
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
  const add = () => run(async () => { await api("/clients", json("POST", { name: name.trim(), sort_order: (data?.length ?? 0) + 1 })); setName(""); });
  const logo = (c: AdminClient, e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (f) run(() => api(`/clients/${c.id}/logo`, form("POST", { file: f })));
  };

  return (
    <>
      <h1>Clients</h1>
      {(msg || error) && <div className="adm-msg err">{msg || error}</div>}
      <div className="adm-card adm-row" style={{ marginBottom: 20 }}>
        <input className="input" style={{ maxWidth: 320 }} placeholder="Client name" value={name} onChange={(e) => setName(e.target.value)} onKeyDown={(e) => e.key === "Enter" && name.trim() && add()} />
        <button className="btn" onClick={add} disabled={!name.trim()}>Add client</button>
        <span className="caption">Logos: PNG/WebP/JPEG, ideally on a transparent background. They display in grayscale on the site.</span>
      </div>
      <table className="adm-table">
        <thead><tr><th>Logo</th><th>Name</th><th>Website</th><th>Order</th><th>Visible</th><th></th></tr></thead>
        <tbody>
          {(data ?? []).map((c) => (
            <tr key={c.id}>
              <td style={{ width: 150 }}>
                {c.logo && <img src={c.logo.src} alt="" style={{ height: 32, maxWidth: 120, objectFit: "contain", display: "block", marginBottom: 6 }} />}
                <input type="file" accept="image/png,image/jpeg,image/webp" aria-label={`Logo for ${c.name}`} onChange={(e) => logo(c, e)} style={{ width: 130, fontSize: 12 }} />
              </td>
              <td><input className="input" defaultValue={c.name} onBlur={(e) => e.target.value.trim() && e.target.value !== c.name && run(() => api(`/clients/${c.id}`, json("PUT", { ...c, name: e.target.value.trim() })))} /></td>
              <td><input className="input" placeholder="https://…" defaultValue={c.url} onBlur={(e) => e.target.value !== c.url && run(() => api(`/clients/${c.id}`, json("PUT", { ...c, url: e.target.value.trim() })))} /></td>
              <td><input className="input" style={{ width: 70 }} type="number" defaultValue={c.sort_order} onBlur={(e) => Number(e.target.value) !== c.sort_order && run(() => api(`/clients/${c.id}`, json("PUT", { ...c, sort_order: Number(e.target.value) || 0 })))} /></td>
              <td><input type="checkbox" checked={c.published} aria-label="Visible" onChange={(e) => run(() => api(`/clients/${c.id}`, json("PUT", { ...c, published: e.target.checked })))} /></td>
              <td><button className="btn btn--danger btn--sm" onClick={() => confirm(`Delete ${c.name}?`) && run(() => api(`/clients/${c.id}`, { method: "DELETE" }))}>Delete</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
