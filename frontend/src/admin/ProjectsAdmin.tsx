import { useEffect, useState, type ChangeEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Approvals } from "./Approvals";
import { api, can, errorText, form, json, multipart, type AdminImage, type AdminProject, useLoad, useMe } from "./api";

export function ProjectsAdmin() {
  const me = useMe();
  const { data, error, reload } = useLoad<AdminProject[]>("/projects");
  const [q, setQ] = useState("");
  const [show, setShow] = useState<"all" | "public" | "hidden">("all");
  const [order, setOrder] = useState<number[] | null>(null);
  const [msg, setMsg] = useState("");
  const list = data ?? [];
  const byId = new Map(list.map((p) => [p.id, p]));
  const ids = order ?? list.map((p) => p.id);
  const rows = ids
    .map((id) => byId.get(id)!)
    .filter(Boolean)
    .filter((p) => show === "all" || (show === "public" ? p.is_public : !p.is_public))
    .filter((p) => !q || `${p.title_en} ${p.title_ar} ${p.city_en} ${p.slug}`.toLowerCase().includes(q.toLowerCase()));
  const move = (id: number, d: number) => {
    const next = [...ids];
    const i = next.indexOf(id);
    const j = i + d;
    if (j < 0 || j >= next.length) return;
    [next[i], next[j]] = [next[j], next[i]];
    setOrder(next);
  };
  async function saveOrder() {
    try {
      await api("/projects-order", json("PUT", { ids }));
      setOrder(null);
      setMsg("Order saved.");
      reload();
    } catch (e) {
      setMsg(errorText(e));
    }
  }
  const editor = can(me, "editor");
  return (
    <>
      <div className="adm-bar">
        <h1>Projects</h1>
        {editor && <Link className="btn" to="/admin/projects/new">New project</Link>}
      </div>
      {(error || msg) && <div className={`adm-msg${error ? " err" : ""}`}>{error || msg}</div>}
      <div className="adm-row" style={{ marginBottom: 12 }}>
        <input className="input" style={{ maxWidth: 280 }} placeholder="Search title, city or slug" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search projects" />
        <select className="select" style={{ width: 170 }} value={show} onChange={(e) => setShow(e.target.value as typeof show)} aria-label="Show">
          <option value="all">All ({list.length})</option>
          <option value="public">On the site ({list.filter((p) => p.is_public).length})</option>
          <option value="hidden">Hidden ({list.filter((p) => !p.is_public).length})</option>
        </select>
        {order && editor && (
          <>
            <button className="btn btn--sm" onClick={saveOrder}>Save order</button>
            <button className="btn btn--sm btn--outline" onClick={() => setOrder(null)}>Discard</button>
          </>
        )}
      </div>
      <table className="adm-table">
        <thead><tr><th></th><th>Title</th><th>Country</th><th>Type</th><th>Photos</th><th>Complete</th><th>Status</th>{editor && <th>Order</th>}</tr></thead>
        <tbody>
          {rows.map((p) => (
            <tr key={p.id}>
              <td>{p.cover ? <img className="adm-thumb" src={p.cover.src} alt="" /> : <span className="adm-thumb" />}</td>
              <td><Link to={`/admin/projects/${p.id}`}>{p.title_en}</Link><div className="caption">{p.slug}</div></td>
              <td>{p.country.toUpperCase()}</td>
              <td>{p.type}</td>
              <td>{p.images.length}</td>
              <td title={p.missing.length ? `Missing: ${p.missing.join(", ")}` : "Complete"}>
                <span className="adm-meter"><span style={{ width: `${p.completeness}%` }} /></span> {p.completeness}%
              </td>
              <td>
                <span className={`adm-tag ${p.is_public ? "ok" : "warn"}`}>{p.is_public ? "On the site" : p.published ? "Hidden (test/placeholder)" : "Draft"}</span>
              </td>
              {editor && (
                <td className="adm-row" style={{ gap: 4 }}>
                  <button className="btn btn--sm btn--outline" onClick={() => move(p.id, -1)} aria-label={`Move ${p.title_en} up`} disabled={!!q || show !== "all"}>↑</button>
                  <button className="btn btn--sm btn--outline" onClick={() => move(p.id, 1)} aria-label={`Move ${p.title_en} down`} disabled={!!q || show !== "all"}>↓</button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

const EMPTY: Omit<AdminProject, "id" | "slug" | "cover" | "images" | "logo" | "completeness" | "missing" | "is_public" | "block_reasons" | "images_without_kind"> = {
  title_en: "", title_ar: "", summary_en: "", summary_ar: "", city_en: "", city_ar: "", country: "eg", type: "residential",
  year: null, area_m2: null, scope_en: "", scope_ar: "", tagline_en: "", tagline_ar: "", details_en: "", details_ar: "", story_en: "", story_ar: "", client_name: "", is_render: false, featured: true, published: false, sort_order: 0,
};

export function ProjectEdit() {
  const { id } = useParams();
  const isNew = id === "new";
  const nav = useNavigate();
  const [p, setP] = useState<AdminProject | null>(null);
  const [v, setV] = useState({ ...EMPTY });
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [upKind, setUpKind] = useState<"" | "render" | "executed">("");
  const [upOverride, setUpOverride] = useState(false);

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
    if (!p) return;
    const typed = prompt(`Delete "${p.title_en}" and all its photos? This cannot be undone.\n\nType the project title to confirm:`);
    if (typed?.trim() !== p.title_en.trim()) return;
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
      await api(`/projects/${p.id}/images`, multipart("POST", { ...(upKind ? { kind: upKind } : {}), override_quality: upOverride }, { files }));
      setP(await api<AdminProject>(`/projects/${p.id}`));
      setMsg({ ok: true, text: `${files.length} photo(s) uploaded.` });
    } catch (x) {
      setMsg({ ok: false, text: errorText(x) });
    } finally {
      setBusy(false);
    }
  }

  async function patchCover(img: AdminImage) {
    try {
      await api(`/project-images/${img.id}`, json("PATCH", { is_cover: true, override_quality: upOverride }));
      await refresh();
    } catch (x) {
      setMsg({ ok: false, text: errorText(x) });
    }
  }

  async function uploadLogo(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || !p) return;
    setBusy(true);
    try {
      setP(await api<AdminProject>(`/projects/${p.id}/logo`, form("POST", { file })));
      setMsg({ ok: true, text: "Logo uploaded." });
    } catch (x) {
      setMsg({ ok: false, text: errorText(x) });
    } finally {
      setBusy(false);
    }
  }
  async function removeLogo() {
    if (!p) return;
    try {
      await api(`/projects/${p.id}/logo`, { method: "DELETE" });
      setP(await api<AdminProject>(`/projects/${p.id}`));
    } catch (x) {
      setMsg({ ok: false, text: errorText(x) });
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
        <div className="adm-row">
          {p && <Link className="btn btn--sm btn--outline" to={`/admin/projects/${p.id}/preview`}>Preview</Link>}
          {p && p.is_public && <a className="btn btn--sm btn--outline" href={`/projects/${p.slug}`} target="_blank" rel="noreferrer">View live ↗</a>}
          <Link to="/admin/projects">← All projects</Link>
        </div>
      </div>
      {p && (
        <p className="caption" style={{ marginTop: -8 }}>
          {p.is_public ? "Visible on the site." : p.published ? "Published but hidden (test project or [placeholder] text)." : "Draft: only visible here and in Preview."}{" "}
          {p.missing.length > 0 && <>Still missing: {p.missing.join(", ")}. Photos are optional; a text-only page is fine.</>}
        </p>
      )}
      {p && p.block_reasons.length > 0 && (
        <div className="adm-msg err" role="status">Not visible publicly because: {p.block_reasons.join(" · ")}</div>
      )}
      {msg && <div className={`adm-msg${msg.ok ? "" : " err"}`} role="status">{msg.text}</div>}

      <div className="adm-card">
        <div className="adm-grid two">
          <label className="f">Title (English) *<input className="input" value={v.title_en} onChange={(e) => set("title_en", e.target.value)} /></label>
          <label className="f">Title (Arabic)<input className="input" dir="rtl" value={v.title_ar} onChange={(e) => set("title_ar", e.target.value)} /></label>
          <label className="f">City (English)<input className="input" value={v.city_en} onChange={(e) => set("city_en", e.target.value)} /></label>
          <label className="f">City (Arabic)<input className="input" dir="rtl" value={v.city_ar} onChange={(e) => set("city_ar", e.target.value)} /></label>
          <label className="f">Country<select className="select" value={v.country} onChange={(e) => set("country", e.target.value as "eg" | "qa" | "sa")}><option value="eg">Egypt</option><option value="qa">Qatar</option><option value="sa">Saudi Arabia</option></select></label>
          <label className="f">Type<select className="select" value={v.type} onChange={(e) => set("type", e.target.value as typeof v.type)}>{["residential", "hospitality", "retail", "office", "industrial", "healthcare", "public", "education", "landscape"].map((x) => <option key={x}>{x}</option>)}</select></label>
          <label className="f">Year<input className="input" type="number" value={v.year ?? ""} onChange={(e) => set("year", num(e.target.value))} /></label>
          <label className="f">Area (m²)<input className="input" type="number" value={v.area_m2 ?? ""} onChange={(e) => set("area_m2", num(e.target.value))} /></label>
          <label className="f">Scope (English)<input className="input" value={v.scope_en} onChange={(e) => set("scope_en", e.target.value)} /></label>
          <label className="f">Scope (Arabic)<input className="input" dir="rtl" value={v.scope_ar} onChange={(e) => set("scope_ar", e.target.value)} /></label>
          <label className="f">Summary (English)<textarea className="textarea" value={v.summary_en} onChange={(e) => set("summary_en", e.target.value)} /></label>
          <label className="f">Summary (Arabic)<textarea className="textarea" dir="rtl" value={v.summary_ar} onChange={(e) => set("summary_ar", e.target.value)} /></label>
          <label className="f">Client name<input className="input" value={v.client_name} onChange={(e) => set("client_name", e.target.value)} /></label>
          <span />
          <label className="f">Tagline (English)<input className="input" value={v.tagline_en} onChange={(e) => set("tagline_en", e.target.value)} /></label>
          <label className="f">Tagline (Arabic)<input className="input" dir="rtl" value={v.tagline_ar} onChange={(e) => set("tagline_ar", e.target.value)} /></label>
          <label className="f">Details (English) — one per line, “Label: Value” (Client: …, Area: …, Status: …)<textarea className="textarea" rows={5} value={v.details_en} onChange={(e) => set("details_en", e.target.value)} /></label>
          <label className="f">Details (Arabic)<textarea className="textarea" rows={5} dir="rtl" value={v.details_ar} onChange={(e) => set("details_ar", e.target.value)} /></label>
          <label className="f">Story (English) — start a section with “## Heading”, blank line between paragraphs<textarea className="textarea" rows={8} value={v.story_en} onChange={(e) => set("story_en", e.target.value)} /></label>
          <label className="f">Story (Arabic)<textarea className="textarea" rows={8} dir="rtl" value={v.story_ar} onChange={(e) => set("story_ar", e.target.value)} /></label>
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
          <h2>Client logo (white banner under the title)</h2>
          <div className="adm-drop">
            {p.logo && <img src={p.logo.src} alt="" style={{ maxHeight: 56, background: "#fff", padding: 8, marginBottom: 12, display: "block" }} />}
            <input type="file" accept="image/jpeg,image/png,image/webp" onChange={uploadLogo} disabled={busy} aria-label="Upload client logo" />
            {p.logo && <button className="btn btn--danger btn--sm" style={{ marginInlineStart: 12 }} onClick={removeLogo}>Remove logo</button>}
          </div>
          <h2>Approvals</h2>
          <Approvals subjectType="project" subjectId={p.id} onChange={refresh} />
          <h2>Photos</h2>
          <div className="adm-drop">
            <p style={{ margin: "0 0 12px" }}>
              JPEG, PNG or WebP up to 15 MB each, long edge at least 1600 px (2400 px for the cover). The first photo becomes the cover.
              Every photo must be labelled <b>Render</b> or <b>Executed</b> before the project can be published. Many photos at once: <Link to="/admin/bulk-images">Bulk upload</Link>.
            </p>
            <div className="adm-row" style={{ justifyContent: "center", marginBottom: 10 }}>
              <label className="adm-check">Label for these photos
                <select className="select" style={{ height: 32 }} value={upKind} onChange={(e) => setUpKind(e.target.value as typeof upKind)}>
                  <option value="">Choose later</option><option value="executed">Executed (real photo)</option><option value="render">Render (visualization)</option>
                </select>
              </label>
              <label className="adm-check"><input type="checkbox" checked={upOverride} onChange={(e) => setUpOverride(e.target.checked)} /> Accept below standard (recorded with your name)</label>
            </div>
            <input type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={upload} disabled={busy} aria-label="Upload photos" />
          </div>
          <div className="adm-imgs" style={{ marginTop: 16 }}>
            {p.images.map((img) => (
              <div className={`adm-img${img.kind ? "" : " adm-img--missing"}`} key={img.id}>
                <FocalPicker img={img} onPick={(x, y) => patch(img, { focal_x: x, focal_y: y })} />
                <div className="body">
                  <label className="f">Label (required)
                    <select className="select" value={img.kind ?? ""} onChange={(e) => e.target.value && patch(img, { kind: e.target.value as "render" | "executed" })} aria-invalid={!img.kind}>
                      <option value="" disabled>Choose: Render or Executed</option>
                      <option value="executed">Executed (real photo)</option>
                      <option value="render">Render (visualization)</option>
                    </select>
                  </label>
                  {img.quality_warnings && <p className="caption adm-warn">⚠ {img.quality_warnings}{img.quality_override_by && ` · accepted by ${img.quality_override_by}`}</p>}
                  <div className="adm-row">
                    <label className="adm-check"><input type="radio" name="cover" checked={img.is_cover} onChange={() => patchCover(img)} /> Cover</label>
                    <label className="adm-check"><select className="select" style={{ height: 32 }} value={img.layout} onChange={(e) => patch(img, { layout: e.target.value as "full" | "half" })}><option value="full">Full row</option><option value="half">Half (pairs)</option></select></label>
                    <label className="adm-check"><input type="checkbox" checked={img.full_bleed} onChange={(e) => patch(img, { full_bleed: e.target.checked })} /> Full-bleed</label>
                  </div>
                  <CaptionField img={img} onSave={patch} />
                  <AltField img={img} onSave={patch} />
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

function AltField({ img, onSave }: { img: AdminImage; onSave: (i: AdminImage, b: Partial<AdminImage>) => void }) {
  const [en, setEn] = useState(img.alt_en);
  const [ar, setAr] = useState(img.alt_ar);
  const dirty = en !== img.alt_en || ar !== img.alt_ar;
  return (
    <>
      <input className="input" placeholder="Alt text for screen readers (English)" value={en} onChange={(e) => setEn(e.target.value)} onBlur={() => dirty && onSave(img, { alt_en: en, alt_ar: ar })} />
      <input className="input" dir="rtl" placeholder="Alt text (Arabic)" value={ar} onChange={(e) => setAr(e.target.value)} onBlur={() => dirty && onSave(img, { alt_en: en, alt_ar: ar })} />
    </>
  );
}

/** Click the photo to set the focal point used when cards and covers crop it. */
function FocalPicker({ img, onPick }: { img: AdminImage; onPick: (x: number, y: number) => void }) {
  const x = img.focal_x ?? 0.5;
  const y = img.focal_y ?? 0.5;
  return (
    <div
      className="adm-focal"
      title="Click to set the focal point (what must stay visible when the photo is cropped)"
      onClick={(e) => {
        const r = e.currentTarget.getBoundingClientRect();
        onPick(Math.round(((e.clientX - r.left) / r.width) * 100) / 100, Math.round(((e.clientY - r.top) / r.height) * 100) / 100);
      }}
    >
      <img src={img.image.src} alt="" style={{ objectPosition: `${x * 100}% ${y * 100}%` }} />
      <span className="adm-focal__dot" style={{ left: `${x * 100}%`, top: `${y * 100}%` }} aria-hidden="true" />
      <span className="adm-focal__hint">Focal point {Math.round(x * 100)}% / {Math.round(y * 100)}%</span>
    </div>
  );
}
