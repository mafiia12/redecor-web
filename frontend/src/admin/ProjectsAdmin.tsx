import { useEffect, useState, type ChangeEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, errorText, form, json, type AdminImage, type AdminProject, useLoad } from "./api";

export function ProjectsAdmin() {
  const { data, error } = useLoad<AdminProject[]>("/projects");
  return (
    <>
      <div className="adm-bar">
        <h1>Projects</h1>
        <Link className="btn" to="/admin/projects/new">New project</Link>
      </div>
      {error && <div className="adm-msg err">{error}</div>}
      <table className="adm-table">
        <thead><tr><th></th><th>Title</th><th>Country</th><th>Type</th><th>Photos</th><th>Status</th></tr></thead>
        <tbody>
          {(data ?? []).map((p) => (
            <tr key={p.id}>
              <td>{p.cover ? <img className="adm-thumb" src={p.cover.src} alt="" /> : <span className="adm-thumb" />}</td>
              <td><Link to={`/admin/projects/${p.id}`}>{p.title_en}</Link></td>
              <td>{p.country.toUpperCase()}</td>
              <td>{p.type}</td>
              <td>{p.images.length}</td>
              <td><span className={`adm-tag ${p.published ? "ok" : "warn"}`}>{p.published ? "Published" : "Hidden"}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

const EMPTY: Omit<AdminProject, "id" | "slug" | "cover" | "images"> = {
  title_en: "", title_ar: "", summary_en: "", summary_ar: "", city_en: "", city_ar: "", country: "eg", type: "residential",
  year: null, area_m2: null, scope_en: "", scope_ar: "", is_render: false, featured: true, published: true, sort_order: 0,
};

export function ProjectEdit() {
  const { id } = useParams();
  const isNew = id === "new";
  const nav = useNavigate();
  const [p, setP] = useState<AdminProject | null>(null);
  const [v, setV] = useState({ ...EMPTY });
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (isNew) return;
    api<AdminProject>(`/projects/${id}`).then((d) => { setP(d); setV(d); }).catch((e) => setMsg({ ok: false, text: errorText(e) }));
  }, [id, isNew]);

  const set = <K extends keyof typeof EMPTY>(k: K, val: (typeof EMPTY)[K]) => setV((s) => ({ ...s, [k]: val }));
  const num = (s: string) => (s === "" ? null : Number(s));

  async function save() {
    setBusy(true);
    setMsg(null);
    try {
      const body = { ...v, slug: p?.slug };
      if (isNew) {
        const created = await api<AdminProject>("/projects", json("POST", body));
        nav(`/admin/projects/${created.id}`, { replace: true });
      } else {
        const d = await api<AdminProject>(`/projects/${id}`, json("PUT", body));
        setP(d);
        setMsg({ ok: true, text: "Saved." });
      }
    } catch (e) {
      setMsg({ ok: false, text: errorText(e) });
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!p || !confirm(`Delete "${p.title_en}" and all its photos? This cannot be undone.`)) return;
    try {
      await api(`/projects/${p.id}`, { method: "DELETE" });
      nav("/admin/projects");
    } catch (e) {
      setMsg({ ok: false, text: errorText(e) });
    }
  }

  async function upload(e: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []);
    e.target.value = "";
    if (!files.length || !p) return;
    setBusy(true);
    setMsg(null);
    try {
      await api(`/projects/${p.id}/images`, form("POST", { files }));
      setP(await api<AdminProject>(`/projects/${p.id}`));
      setMsg({ ok: true, text: `${files.length} photo(s) uploaded.` });
    } catch (x) {
      setMsg({ ok: false, text: errorText(x) });
    } finally {
      setBusy(false);
    }
  }

  const refresh = async () => p && setP(await api<AdminProject>(`/projects/${p.id}`));
  const patch = async (img: AdminImage, body: Partial<AdminImage>) => {
    try {
      await api(`/project-images/${img.id}`, json("PATCH", body));
      await refresh();
    } catch (x) {
      setMsg({ ok: false, text: errorText(x) });
    }
  };
  const del = async (img: AdminImage) => {
    if (!confirm("Delete this photo?")) return;
    try {
      await api(`/project-images/${img.id}`, { method: "DELETE" });
      await refresh();
    } catch (x) {
      setMsg({ ok: false, text: errorText(x) });
    }
  };

  return (
    <>
      <div className="adm-bar">
        <h1>{isNew ? "New project" : v.title_en || "Project"}</h1>
        <Link to="/admin/projects">← All projects</Link>
      </div>
      {msg && <div className={`adm-msg${msg.ok ? "" : " err"}`} role="status">{msg.text}</div>}

      <div className="adm-card">
        <div className="adm-grid two">
          <label className="f">Title (English) *<input className="input" value={v.title_en} onChange={(e) => set("title_en", e.target.value)} /></label>
          <label className="f">Title (Arabic)<input className="input" dir="rtl" value={v.title_ar} onChange={(e) => set("title_ar", e.target.value)} /></label>
          <label className="f">City (English)<input className="input" value={v.city_en} onChange={(e) => set("city_en", e.target.value)} /></label>
          <label className="f">City (Arabic)<input className="input" dir="rtl" value={v.city_ar} onChange={(e) => set("city_ar", e.target.value)} /></label>
          <label className="f">Country<select className="select" value={v.country} onChange={(e) => set("country", e.target.value as "eg" | "qa" | "sa")}><option value="eg">Egypt</option><option value="qa">Qatar</option><option value="sa">Saudi Arabia</option></select></label>
          <label className="f">Type<select className="select" value={v.type} onChange={(e) => set("type", e.target.value as typeof v.type)}>{["residential", "hospitality", "retail", "office", "industrial", "healthcare", "public", "education"].map((x) => <option key={x}>{x}</option>)}</select></label>
          <label className="f">Year<input className="input" type="number" value={v.year ?? ""} onChange={(e) => set("year", num(e.target.value))} /></label>
          <label className="f">Area (m²)<input className="input" type="number" value={v.area_m2 ?? ""} onChange={(e) => set("area_m2", num(e.target.value))} /></label>
          <label className="f">Scope (English)<input className="input" value={v.scope_en} onChange={(e) => set("scope_en", e.target.value)} /></label>
          <label className="f">Scope (Arabic)<input className="input" dir="rtl" value={v.scope_ar} onChange={(e) => set("scope_ar", e.target.value)} /></label>
          <label className="f">Summary (English)<textarea className="textarea" value={v.summary_en} onChange={(e) => set("summary_en", e.target.value)} /></label>
          <label className="f">Summary (Arabic)<textarea className="textarea" dir="rtl" value={v.summary_ar} onChange={(e) => set("summary_ar", e.target.value)} /></label>
          <label className="f">Display order (lower first)<input className="input" type="number" value={v.sort_order} onChange={(e) => set("sort_order", Number(e.target.value) || 0)} /></label>
        </div>
        <div className="adm-row" style={{ marginTop: 16, gap: 20 }}>
          <label className="adm-check"><input type="checkbox" checked={v.published} onChange={(e) => set("published", e.target.checked)} /> Published</label>
          <label className="adm-check"><input type="checkbox" checked={v.featured} onChange={(e) => set("featured", e.target.checked)} /> Show on Home</label>
          <label className="adm-check"><input type="checkbox" checked={v.is_render} onChange={(e) => set("is_render", e.target.checked)} /> Whole project is a design visualization (render)</label>
        </div>
        <div className="adm-row" style={{ marginTop: 20 }}>
          <button className="btn" onClick={save} disabled={busy || !v.title_en.trim()}>{busy ? "Saving…" : isNew ? "Create project" : "Save changes"}</button>
          {!isNew && <button className="btn btn--danger" onClick={remove}>Delete project</button>}
        </div>
      </div>

      {!isNew && p && (
        <>
          <h2>Photos</h2>
          <div className="adm-drop">
            <p style={{ margin: "0 0 12px" }}>JPEG, PNG or WebP up to 15 MB each. The first photo becomes the cover. Responsive sizes are generated automatically.</p>
            <input type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={upload} disabled={busy} aria-label="Upload photos" />
          </div>
          <div className="adm-imgs" style={{ marginTop: 16 }}>
            {p.images.map((img) => (
              <div className="adm-img" key={img.id}>
                <img src={img.image.src} alt="" />
                <div className="body">
                  <div className="adm-row">
                    <label className="adm-check"><input type="radio" name="cover" checked={img.is_cover} onChange={() => patch(img, { is_cover: true })} /> Cover</label>
                    <label className="adm-check"><input type="checkbox" checked={img.is_render} onChange={(e) => patch(img, { is_render: e.target.checked })} /> Render</label>
                    <label className="adm-check"><input type="checkbox" checked={img.full_bleed} onChange={(e) => patch(img, { full_bleed: e.target.checked })} /> Full-bleed</label>
                  </div>
                  <CaptionField img={img} onSave={patch} />
                  <div className="adm-row" style={{ justifyContent: "space-between" }}>
                    <label className="adm-check">Order <input className="input" style={{ width: 64, height: 32 }} type="number" defaultValue={img.sort_order} onBlur={(e) => Number(e.target.value) !== img.sort_order && patch(img, { sort_order: Number(e.target.value) || 0 })} /></label>
                    <button className="btn btn--danger btn--sm" onClick={() => del(img)}>Delete</button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </>
  );
}

function CaptionField({ img, onSave }: { img: AdminImage; onSave: (i: AdminImage, b: Partial<AdminImage>) => void }) {
  const [en, setEn] = useState(img.caption_en);
  const [ar, setAr] = useState(img.caption_ar);
  const dirty = en !== img.caption_en || ar !== img.caption_ar;
  return (
    <>
      <input className="input" placeholder="Caption (English)" value={en} onChange={(e) => setEn(e.target.value)} onBlur={() => dirty && onSave(img, { caption_en: en, caption_ar: ar })} />
      <input className="input" dir="rtl" placeholder="التعليق (عربي)" value={ar} onChange={(e) => setAr(e.target.value)} onBlur={() => dirty && onSave(img, { caption_en: en, caption_ar: ar })} />
    </>
  );
}
