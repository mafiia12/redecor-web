import { useState, type ChangeEvent, type FormEvent } from "react";
import {
  api,
  can,
  errorText,
  form,
  json,
  setToken,
  useLoad,
  useMe,
  type AdminDocument,
  type AdminTestimonial,
  type AdminUser,
  type Role,
} from "./api";

type Msg = { ok: boolean; text: string } | null;
const Note = ({ msg }: { msg: Msg }) => (msg ? <div className={`adm-msg${msg.ok ? "" : " err"}`} role="status">{msg.text}</div> : null);

/* ---------- Status & analytics ---------- */
interface SystemInfo {
  environment: string;
  smtp_configured: boolean;
  notify_to: string[];
  notifications: Record<string, number>;
  alerts_configured: boolean;
  test_content_visible: boolean;
  demo_seed: boolean;
}
interface Analytics {
  days: number;
  totals: Record<string, number>;
  top_projects: { path: string; views: number }[];
  languages: Record<string, number>;
}
const EVENT_LABELS: Record<string, string> = {
  page_view: "Page views",
  project_view: "Project page views",
  service_view: "Service page views",
  cta_click: "Consultation button clicks",
  whatsapp_open: "WhatsApp button opened",
  whatsapp_click: "WhatsApp chats started",
  enquiry_submit: "Enquiry form submits",
  enquiry_success: "Enquiries sent",
  profile_download: "Company profile downloads",
  language_switch: "Language switches",
  theme_switch: "Theme switches",
};

export function SystemAdmin() {
  const me = useMe();
  const sys = useLoad<SystemInfo>("/system");
  const [days, setDays] = useState(30);
  const stats = useLoad<Analytics>(`/analytics?days=${days}`);
  const [msg, setMsg] = useState<Msg>(null);
  const [busy, setBusy] = useState(false);

  async function testEmail() {
    setBusy(true);
    setMsg(null);
    try {
      const r = await api<{ sent_to: string[] }>("/system/test-email", { method: "POST" });
      setMsg({ ok: true, text: `Test e-mail accepted by the mail server for ${r.sent_to.join(", ")}. Check the inbox.` });
    } catch (e) {
      setMsg({ ok: false, text: errorText(e) });
    } finally {
      setBusy(false);
    }
  }

  const s = sys.data;
  return (
    <>
      <h1>Status &amp; analytics</h1>
      <Note msg={msg} />
      {s && (
        <div className="adm-card" style={{ marginBottom: 24 }}>
          <table className="adm-kv">
            <tbody>
              <tr><th>Environment</th><td>{s.environment}</td></tr>
              <tr>
                <th>Enquiry e-mails</th>
                <td>
                  {s.smtp_configured ? <span className="adm-tag ok">Configured → {s.notify_to.join(", ")}</span> : <span className="adm-tag warn">Not configured: enquiries are saved here but no e-mail is sent</span>}
                  {can(me, "admin") && s.smtp_configured && <button className="btn btn--sm btn--outline" style={{ marginInlineStart: 12 }} disabled={busy} onClick={testEmail}>Send test e-mail</button>}
                </td>
              </tr>
              <tr><th>Notifications</th><td>{Object.entries(s.notifications).map(([k, v]) => <span key={k} className={`adm-tag ${k === "sent" ? "ok" : k === "failed" ? "warn" : ""}`} style={{ marginInlineEnd: 6 }}>{k}: {v}</span>)}</td></tr>
              <tr><th>Alerts webhook</th><td>{s.alerts_configured ? "Configured" : "Not configured"}</td></tr>
              {(s.test_content_visible || s.demo_seed) && <tr><th>Warning</th><td><span className="adm-tag warn">Test / demo content is enabled on this server</span></td></tr>}
            </tbody>
          </table>
        </div>
      )}

      <div className="adm-bar">
        <h2 style={{ margin: 0 }}>Visitor actions</h2>
        <select className="select" style={{ width: 160 }} value={days} onChange={(e) => setDays(Number(e.target.value))} aria-label="Period">
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
          <option value={365}>Last 12 months</option>
        </select>
      </div>
      <p className="caption">Anonymous counts only: no cookies, no IP addresses, no personal data. Visitors with “Do Not Track” are not counted.</p>
      {stats.data && (
        <div className="adm-grid" style={{ marginTop: 12 }}>
          {Object.entries(EVENT_LABELS).map(([k, label]) => (
            <div className="adm-card adm-stat" key={k}>
              <span className="caption">{label}</span>
              <strong>{(stats.data!.totals[k] ?? 0).toLocaleString()}</strong>
            </div>
          ))}
        </div>
      )}
      {stats.data && stats.data.top_projects.length > 0 && (
        <>
          <h2>Most viewed projects</h2>
          <table className="adm-table">
            <thead><tr><th>Page</th><th>Views</th></tr></thead>
            <tbody>{stats.data.top_projects.map((r) => <tr key={r.path}><td>{r.path}</td><td>{r.views}</td></tr>)}</tbody>
          </table>
        </>
      )}
    </>
  );
}

/* ---------- Users (admin only) ---------- */
export function UsersAdmin() {
  const me = useMe();
  const { data, error, reload } = useLoad<AdminUser[]>("/users");
  const [v, setV] = useState({ email: "", role: "editor" as Role, password: "" });
  const [msg, setMsg] = useState<Msg>(null);

  async function add(e: FormEvent) {
    e.preventDefault();
    setMsg(null);
    try {
      await api("/users", json("POST", v));
      setV({ email: "", role: "editor", password: "" });
      setMsg({ ok: true, text: "User created. Share the password privately (not by WhatsApp group or e-mail chain)." });
      reload();
    } catch (x) {
      setMsg({ ok: false, text: errorText(x) });
    }
  }
  async function setRole(u: AdminUser, role: Role) {
    try {
      await api(`/users/${u.id}`, json("PATCH", { role }));
      reload();
    } catch (x) {
      setMsg({ ok: false, text: errorText(x) });
    }
  }
  async function remove(u: AdminUser) {
    if (!confirm(`Remove ${u.email}? They will no longer be able to sign in.`)) return;
    try {
      await api(`/users/${u.id}`, { method: "DELETE" });
      reload();
    } catch (x) {
      setMsg({ ok: false, text: errorText(x) });
    }
  }

  if (!can(me, "admin")) return <p>Only administrators can manage users.</p>;
  return (
    <>
      <h1>Users</h1>
      <p className="caption">Admin: everything incl. users and office details · Editor: projects, clients, images, enquiries · Viewer: read-only (no enquiries).</p>
      <Note msg={msg || (error ? { ok: false, text: error } : null)} />
      <table className="adm-table" style={{ marginBottom: 24 }}>
        <thead><tr><th>E-mail</th><th>Role</th><th></th></tr></thead>
        <tbody>
          {(data ?? []).map((u) => (
            <tr key={u.id}>
              <td>{u.email}{u.email === me.email && " (you)"}</td>
              <td>
                <select className="select" style={{ width: 130 }} value={u.role} onChange={(e) => setRole(u, e.target.value as Role)} aria-label={`Role of ${u.email}`}>
                  <option value="admin">Admin</option>
                  <option value="editor">Editor</option>
                  <option value="viewer">Viewer</option>
                </select>
              </td>
              <td>{u.email !== me.email && <button className="btn btn--danger btn--sm" onClick={() => remove(u)}>Remove</button>}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <form className="adm-card" onSubmit={add}>
        <h2 style={{ marginTop: 0 }}>Add a user</h2>
        <div className="adm-grid">
          <label className="f">E-mail<input className="input" type="email" required value={v.email} onChange={(e) => setV({ ...v, email: e.target.value })} /></label>
          <label className="f">Role<select className="select" value={v.role} onChange={(e) => setV({ ...v, role: e.target.value as Role })}><option value="editor">Editor</option><option value="viewer">Viewer</option><option value="admin">Admin</option></select></label>
          <label className="f">Temporary password (12+ characters)<input className="input" type="password" autoComplete="new-password" required minLength={12} value={v.password} onChange={(e) => setV({ ...v, password: e.target.value })} /></label>
        </div>
        <button className="btn" style={{ marginTop: 16 }}>Create user</button>
      </form>
    </>
  );
}

/* ---------- My account ---------- */
export function AccountAdmin() {
  const me = useMe();
  const [v, setV] = useState({ current_password: "", new_password: "", repeat: "" });
  const [msg, setMsg] = useState<Msg>(null);
  async function submit(e: FormEvent) {
    e.preventDefault();
    if (v.new_password !== v.repeat) return setMsg({ ok: false, text: "The two new passwords do not match." });
    try {
      const r = await api<{ token: string }>("/me/password", json("POST", { current_password: v.current_password, new_password: v.new_password }));
      setToken(r.token);
      setV({ current_password: "", new_password: "", repeat: "" });
      setMsg({ ok: true, text: "Password changed. Other devices were signed out." });
    } catch (x) {
      setMsg({ ok: false, text: errorText(x) });
    }
  }
  return (
    <>
      <h1>My account</h1>
      <p>{me.email} · {me.role}</p>
      <Note msg={msg} />
      <form className="adm-card" onSubmit={submit} style={{ maxWidth: 480, display: "flex", flexDirection: "column", gap: 12 }}>
        <h2 style={{ margin: 0 }}>Change password</h2>
        <label className="f">Current password<input className="input" type="password" autoComplete="current-password" required value={v.current_password} onChange={(e) => setV({ ...v, current_password: e.target.value })} /></label>
        <label className="f">New password (12+ characters, letters and numbers or symbols)<input className="input" type="password" autoComplete="new-password" required minLength={12} value={v.new_password} onChange={(e) => setV({ ...v, new_password: e.target.value })} /></label>
        <label className="f">Repeat new password<input className="input" type="password" autoComplete="new-password" required value={v.repeat} onChange={(e) => setV({ ...v, repeat: e.target.value })} /></label>
        <button className="btn">Change password</button>
      </form>
    </>
  );
}

/* ---------- Testimonials ---------- */
const BLANK_T: Omit<AdminTestimonial, "id"> = { quote_en: "", quote_ar: "", author: "", role_en: "", role_ar: "", company: "", approval_note: "", approved: false, published: false, sort_order: 0 };

export function TestimonialsAdmin() {
  const me = useMe();
  const { data, reload } = useLoad<AdminTestimonial[]>("/testimonials");
  const [edit, setEdit] = useState<(Omit<AdminTestimonial, "id"> & { id?: number }) | null>(null);
  const [msg, setMsg] = useState<Msg>(null);
  async function save(e: FormEvent) {
    e.preventDefault();
    if (!edit) return;
    try {
      if (edit.id) await api(`/testimonials/${edit.id}`, json("PUT", edit));
      else await api("/testimonials", json("POST", edit));
      setEdit(null);
      setMsg({ ok: true, text: "Saved." });
      reload();
    } catch (x) {
      setMsg({ ok: false, text: errorText(x) });
    }
  }
  async function remove(t: AdminTestimonial) {
    if (!confirm(`Delete the testimonial from ${t.author}?`)) return;
    await api(`/testimonials/${t.id}`, { method: "DELETE" }).catch((x) => setMsg({ ok: false, text: errorText(x) }));
    reload();
  }
  const set = <K extends keyof typeof BLANK_T>(k: K, v: (typeof BLANK_T)[K]) => setEdit((s) => (s ? { ...s, [k]: v } : s));
  return (
    <>
      <div className="adm-bar">
        <h1>Testimonials</h1>
        {can(me, "editor") && <button className="btn" onClick={() => setEdit({ ...BLANK_T })}>Add testimonial</button>}
      </div>
      <p className="caption">Only real quotes, with the client's written permission. A testimonial appears on the site only when “Client approved” and “Published” are both ticked. With none published, the section stays hidden.</p>
      <Note msg={msg} />
      {edit && (
        <form className="adm-card" onSubmit={save} style={{ marginBottom: 20 }}>
          <div className="adm-grid two">
            <label className="f">Quote (English)<textarea className="textarea" value={edit.quote_en} onChange={(e) => set("quote_en", e.target.value)} /></label>
            <label className="f">Quote (Arabic)<textarea className="textarea" dir="rtl" value={edit.quote_ar} onChange={(e) => set("quote_ar", e.target.value)} /></label>
            <label className="f">Person *<input className="input" required value={edit.author} onChange={(e) => set("author", e.target.value)} /></label>
            <label className="f">Company<input className="input" value={edit.company} onChange={(e) => set("company", e.target.value)} /></label>
            <label className="f">Role (English)<input className="input" value={edit.role_en} onChange={(e) => set("role_en", e.target.value)} /></label>
            <label className="f">Role (Arabic)<input className="input" dir="rtl" value={edit.role_ar} onChange={(e) => set("role_ar", e.target.value)} /></label>
            <label className="f">How was it approved? (e.g. “E-mail from client, 2 Nov 2026”)<input className="input" value={edit.approval_note} onChange={(e) => set("approval_note", e.target.value)} /></label>
          </div>
          <div className="adm-row" style={{ marginTop: 12, gap: 20 }}>
            <label className="adm-check"><input type="checkbox" checked={edit.approved} onChange={(e) => set("approved", e.target.checked)} /> Client approved publication</label>
            <label className="adm-check"><input type="checkbox" checked={edit.published} onChange={(e) => set("published", e.target.checked)} /> Published</label>
          </div>
          <div className="adm-row" style={{ marginTop: 16 }}>
            <button className="btn">Save</button>
            <button type="button" className="btn btn--outline" onClick={() => setEdit(null)}>Cancel</button>
          </div>
        </form>
      )}
      {data && data.length === 0 && !edit && <p className="caption">No testimonials yet.</p>}
      {(data ?? []).map((t) => (
        <article key={t.id} className="adm-card" style={{ marginBottom: 12 }}>
          <div className="adm-bar" style={{ marginBottom: 6 }}>
            <strong>{t.author}{t.company && `, ${t.company}`}</strong>
            <div className="adm-row">
              <span className={`adm-tag ${t.approved ? "ok" : "warn"}`}>{t.approved ? "Approved" : "Not approved"}</span>
              <span className={`adm-tag ${t.published && t.approved ? "ok" : "warn"}`}>{t.published && t.approved ? "On the site" : "Hidden"}</span>
              {can(me, "editor") && <button className="btn btn--sm btn--outline" onClick={() => setEdit(t)}>Edit</button>}
              {can(me, "editor") && <button className="btn btn--sm btn--danger" onClick={() => remove(t)}>Delete</button>}
            </div>
          </div>
          <p style={{ margin: 0 }}>{t.quote_en || t.quote_ar}</p>
        </article>
      ))}
    </>
  );
}

/* ---------- Documents (company profile PDF) ---------- */
export function DocumentsAdmin() {
  const me = useMe();
  const { data, reload } = useLoad<AdminDocument[]>("/documents");
  const [msg, setMsg] = useState<Msg>(null);
  const [busy, setBusy] = useState(false);
  async function upload(d: AdminDocument, e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setBusy(true);
    try {
      await api(`/documents/${d.slot}`, { ...form("PUT", { file }) });
      setMsg({ ok: true, text: "Uploaded. Check the file, then click Publish to show the download link on the site." });
      reload();
    } catch (x) {
      setMsg({ ok: false, text: errorText(x) });
    } finally {
      setBusy(false);
    }
  }
  async function publish(d: AdminDocument, published: boolean) {
    await api(`/documents/${d.slot}?published=${published}`, { method: "PATCH" }).catch((x) => setMsg({ ok: false, text: errorText(x) }));
    reload();
  }
  async function remove(d: AdminDocument) {
    if (!confirm(`Delete ${d.filename}?`)) return;
    await api(`/documents/${d.slot}`, { method: "DELETE" }).catch((x) => setMsg({ ok: false, text: errorText(x) }));
    reload();
  }
  return (
    <>
      <h1>Documents</h1>
      <p className="caption">PDF up to 25 MB. A new upload starts hidden; publish it when it is the approved version.</p>
      <Note msg={msg} />
      {(data ?? []).map((d) => (
        <div key={d.slot} className="adm-card">
          <div className="adm-bar" style={{ marginBottom: 8 }}>
            <strong>{d.label}</strong>
            {d.filename && <span className={`adm-tag ${d.published ? "ok" : "warn"}`}>{d.published ? "On the site" : "Hidden"}</span>}
          </div>
          {d.filename ? (
            <p style={{ margin: "0 0 12px" }}><a href={d.url} target="_blank" rel="noreferrer">{d.filename}</a> · {(d.size / 1048576).toFixed(1)} MB</p>
          ) : (
            <p className="caption">No file yet.</p>
          )}
          {can(me, "editor") && (
            <div className="adm-row">
              <input type="file" accept="application/pdf" onChange={(e) => upload(d, e)} disabled={busy} aria-label={`Upload ${d.label}`} />
              {d.filename && <button className="btn btn--sm" onClick={() => publish(d, !d.published)}>{d.published ? "Unpublish" : "Publish"}</button>}
              {d.filename && <button className="btn btn--sm btn--danger" onClick={() => remove(d)}>Delete</button>}
            </div>
          )}
        </div>
      ))}
    </>
  );
}
