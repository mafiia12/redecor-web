import { Fragment, useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, downloadFile, errorText, multipart, useLoad } from "./api";

/* ---------- Bulk photo upload (dry-run first) ---------- */
interface PlanRow {
  file: string;
  project_slug: string;
  project: string;
  order: number | null;
  kind: string;
  cover: boolean;
  quality: string;
  action: "create" | "skip-duplicate" | "reject";
  reason: string;
}
interface Plan {
  token?: string;
  rows: PlanRow[];
  summary: Record<string, number>;
  backup?: string;
}

function PlanTable({ plan }: { plan: Plan }) {
  return (
    <>
      <p>
        <span className="adm-tag ok">create {plan.summary.create}</span>{" "}
        <span className="adm-tag">skip-duplicate {plan.summary["skip-duplicate"]}</span>{" "}
        <span className="adm-tag warn">reject {plan.summary.reject}</span>
      </p>
      <table className="adm-table adm-table--compact">
        <thead><tr><th>File</th><th>Project</th><th>Order</th><th>Kind</th><th>Cover</th><th>Quality</th><th>Action</th><th>Reason</th></tr></thead>
        <tbody>
          {plan.rows.map((r) => (
            <tr key={r.file}>
              <td>{r.file}</td>
              <td>{r.project}</td>
              <td>{r.order ?? ""}</td>
              <td>{r.kind}</td>
              <td>{r.cover ? "yes" : ""}</td>
              <td>{r.quality}</td>
              <td><span className={`adm-tag ${r.action === "create" ? "ok" : r.action === "reject" ? "warn" : ""}`}>{r.action}</span></td>
              <td>{r.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

export function BulkImagesAdmin() {
  const [files, setFiles] = useState<File[]>([]);
  const [mapping, setMapping] = useState<File | null>(null);
  const [override, setOverride] = useState(false);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [done, setDone] = useState<Plan | null>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function dryRun(e: FormEvent) {
    e.preventDefault();
    setErr("");
    setDone(null);
    setBusy(true);
    try {
      setPlan(await api<Plan>("/bulk-images/plan", multipart("POST", { override_quality: override }, { files, mapping })));
    } catch (x) {
      setErr(errorText(x));
    } finally {
      setBusy(false);
    }
  }
  async function apply() {
    if (!plan?.token) return;
    setBusy(true);
    try {
      setDone(await api<Plan>("/bulk-images/apply", multipart("POST", { token: plan.token, override_quality: override })));
      setPlan(null);
    } catch (x) {
      setErr(errorText(x));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h1>Bulk photo upload</h1>
      <p className="caption">
        Name files <code>project-slug__01__executed.jpg</code> or <code>project-slug__02__render__cover.jpg</code>, or add a CSV mapping
        (<button className="btn btn--sm btn--outline" type="button" onClick={() => downloadFile("/bulk-images/mapping-template", "image-mapping-template.csv")}>template</button>).
        A zip of photos works too. Step 1 is a dry run: nothing is saved until you confirm. Details: docs/CONTENT_GUIDE.md.
      </p>
      {err && <div className="adm-msg err">{err}</div>}
      <form className="adm-card" onSubmit={dryRun}>
        <div className="adm-grid two">
          <label className="f">Photos or .zip<input type="file" multiple accept="image/jpeg,image/png,image/webp,.zip,application/zip" onChange={(e) => setFiles(Array.from(e.target.files ?? []))} /></label>
          <label className="f">CSV mapping (optional)<input type="file" accept=".csv,text/csv" onChange={(e) => setMapping(e.target.files?.[0] ?? null)} /></label>
        </div>
        <label className="adm-check" style={{ marginTop: 12 }}><input type="checkbox" checked={override} onChange={(e) => setOverride(e.target.checked)} /> Accept below-standard photos (recorded with your name)</label>
        <div style={{ marginTop: 12 }}><button className="btn" disabled={busy || !files.length}>{busy ? "Checking…" : "1. Dry run"}</button></div>
      </form>
      {plan && (
        <div className="adm-card" style={{ marginTop: 16 }}>
          <h2 style={{ marginTop: 0 }}>Dry run: nothing has been saved</h2>
          <PlanTable plan={plan} />
          <div className="adm-row" style={{ marginTop: 12 }}>
            <button className="btn" disabled={busy || !plan.summary.create} onClick={apply}>2. Confirm: add {plan.summary.create} photo(s)</button>
            <button className="btn btn--outline" onClick={() => setPlan(null)}>Cancel</button>
            <span className="caption">The database is backed up automatically before anything is added.</span>
          </div>
        </div>
      )}
      {done && (
        <div className="adm-card" style={{ marginTop: 16 }}>
          <h2 style={{ marginTop: 0 }}>Done</h2>
          <div className="adm-msg">Added {done.summary.create} photo(s). Backup made first: {done.backup || "n/a"}.</div>
          <PlanTable plan={done} />
        </div>
      )}
    </>
  );
}

/* ---------- Content readiness ---------- */
interface ReadyRow {
  type: "project" | "client";
  id: number;
  slug: string;
  name: string;
  image_count: number;
  title_en?: boolean;
  title_ar?: boolean;
  description_en?: boolean;
  description_ar?: boolean;
  cover_image?: boolean;
  every_image_has_kind?: boolean;
  alt_text_en_ar?: boolean;
  logo?: boolean;
  approved: boolean;
  approval_status: string;
  published: boolean;
  missing: number;
  missing_items: string;
  ready: boolean;
}
interface Readiness {
  rows: ReadyRow[];
  summary: { projects_ready: number; projects: number; clients_ready: number; clients: number };
}
const Mark = ({ ok }: { ok?: boolean }) => <span className={ok ? "adm-ok" : "adm-no"}>{ok ? "✓" : "✗"}</span>;

export function ReadinessAdmin() {
  const { data, error } = useLoad<Readiness>("/readiness");
  const [onlyNotReady, setOnlyNotReady] = useState(false);
  const [sortMissing, setSortMissing] = useState(true);
  const [err, setErr] = useState("");
  const rows = useMemo(() => {
    let r = (data?.rows ?? []).filter((x) => !onlyNotReady || !x.ready);
    if (sortMissing) r = [...r].sort((a, b) => b.missing - a.missing);
    return r;
  }, [data, onlyNotReady, sortMissing]);
  const projects = rows.filter((r) => r.type === "project");
  const clients = rows.filter((r) => r.type === "client");
  const exp = (fmt: "csv" | "xlsx") => downloadFile(`/readiness?format=${fmt}`, `content-readiness.${fmt}`).catch((x) => setErr(errorText(x)));

  return (
    <>
      <div className="adm-bar">
        <h1>Content readiness</h1>
        <div className="adm-row">
          <button className="btn btn--sm btn--outline" onClick={() => exp("csv")}>Export CSV</button>
          <button className="btn btn--sm btn--outline" onClick={() => exp("xlsx")}>Export Excel</button>
        </div>
      </div>
      {(error || err) && <div className="adm-msg err">{error || err}</div>}
      {data && (
        <p className="adm-summary">
          <b>{data.summary.projects_ready} of {data.summary.projects}</b> projects ready · <b>{data.summary.clients_ready} of {data.summary.clients}</b> client logos ready
        </p>
      )}
      <div className="adm-row" style={{ marginBottom: 12 }}>
        <label className="adm-check"><input type="checkbox" checked={onlyNotReady} onChange={(e) => setOnlyNotReady(e.target.checked)} /> Only not ready</label>
        <label className="adm-check"><input type="checkbox" checked={sortMissing} onChange={(e) => setSortMissing(e.target.checked)} /> Most missing first</label>
      </div>
      <h2>Projects</h2>
      <table className="adm-table adm-table--compact">
        <thead><tr><th>Project</th><th>AR title</th><th>AR desc.</th><th>EN title</th><th>EN desc.</th><th>Cover</th><th>Images</th><th>All labelled</th><th>Alt EN/AR</th><th>Approval</th><th>Published</th><th>Ready</th></tr></thead>
        <tbody>
          {projects.map((r) => (
            <tr key={r.id}>
              <td><Link to={`/admin/projects/${r.id}`}>{r.name}</Link><div className="caption">{r.missing ? `${r.missing} missing` : "complete"}</div></td>
              <td><Mark ok={r.title_ar} /></td><td><Mark ok={r.description_ar} /></td><td><Mark ok={r.title_en} /></td><td><Mark ok={r.description_en} /></td>
              <td><Mark ok={r.cover_image} /></td><td>{r.image_count}</td><td><Mark ok={r.every_image_has_kind} /></td><td><Mark ok={r.alt_text_en_ar} /></td>
              <td><span className={`adm-tag ${r.approved ? "ok" : "warn"}`}>{r.approval_status === "none" ? "not recorded" : r.approval_status}</span></td>
              <td>{r.published ? "yes" : "draft"}</td>
              <td><span className={`adm-tag ${r.ready ? "ok" : "warn"}`}>{r.ready ? "Ready" : "Not ready"}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
      <h2>Client logos</h2>
      <table className="adm-table adm-table--compact">
        <thead><tr><th>Client</th><th>Logo</th><th>Approval</th><th>Published</th><th>Ready</th></tr></thead>
        <tbody>
          {clients.map((r) => (
            <Fragment key={r.id}>
              <tr>
                <td><Link to="/admin/clients">{r.name}</Link></td>
                <td><Mark ok={r.logo} /></td>
                <td><span className={`adm-tag ${r.approved ? "ok" : "warn"}`}>{r.approval_status === "none" ? "not recorded" : r.approval_status}</span></td>
                <td>{r.published ? "yes" : "no"}</td>
                <td><span className={`adm-tag ${r.ready ? "ok" : "warn"}`}>{r.ready ? "Ready" : "Not ready"}</span></td>
              </tr>
            </Fragment>
          ))}
        </tbody>
      </table>
    </>
  );
}

/* ---------- Project import from Excel / CSV / JSON (dry-run first) ---------- */
interface ImportRow {
  row: number;
  slug: string;
  title_en: string;
  action: "create" | "update" | "skip" | "error";
  errors: string[];
  notes: string[];
}
interface ImportResult {
  rows: ImportRow[];
  summary: Record<string, number>;
  backup?: string;
}
interface ImportLogRow {
  at: string;
  user: string;
  kind: string;
  filename: string;
  created: number;
  updated: number;
  skipped: number;
  errors: number;
  backup: string;
}
const IMPORT_TAG: Record<string, string> = { create: "ok", update: "ok", skip: "", error: "warn" };

function ImportTable({ res }: { res: ImportResult }) {
  return (
    <>
      <p>
        {(["create", "update", "skip", "error"] as const).map((k) => (
          <Fragment key={k}><span className={`adm-tag ${IMPORT_TAG[k]}`}>{k} {res.summary[k] ?? 0}</span>{" "}</Fragment>
        ))}
      </p>
      <table className="adm-table adm-table--compact">
        <thead><tr><th>Row</th><th>Slug</th><th>Title</th><th>Action</th><th>Problems / notes</th></tr></thead>
        <tbody>
          {res.rows.map((r) => (
            <tr key={r.row}>
              <td>{r.row}</td>
              <td>{r.slug}</td>
              <td>{r.title_en}</td>
              <td><span className={`adm-tag ${IMPORT_TAG[r.action]}`}>{r.action}</span></td>
              <td>{r.errors.length ? <span className="adm-no">{r.errors.join(" · ")}</span> : r.notes.join(" · ")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

export function ImportAdmin() {
  const [file, setFile] = useState<File | null>(null);
  const [update, setUpdate] = useState(false);
  const [plan, setPlan] = useState<ImportResult | null>(null);
  const [done, setDone] = useState<ImportResult | null>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const log = useLoad<ImportLogRow[]>("/import/log");

  async function run(step: "plan" | "apply") {
    if (!file) return;
    setErr("");
    setBusy(true);
    try {
      const res = await api<ImportResult>(`/import/${step}`, multipart("POST", { update_existing: update }, { file }));
      if (step === "plan") {
        setPlan(res);
        setDone(null);
      } else {
        setDone(res);
        setPlan(null);
        log.reload();
      }
    } catch (x) {
      setErr(errorText(x));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h1>Import projects</h1>
      <p className="caption">
        Fill the Excel template (one project per row; the Instructions sheet explains every column), or upload a CSV (UTF-8) or the JSON portfolio manifest.
        New projects are created as <b>drafts</b>. Step 1 is a dry run that lists every problem by row and column; nothing is saved until you confirm.
      </p>
      <p><button className="btn btn--sm btn--outline" type="button" onClick={() => downloadFile("/import/template", "project-import-template.xlsx").catch((x) => setErr(errorText(x)))}>Download Excel template</button></p>
      <form className="adm-card" onSubmit={(e) => { e.preventDefault(); run("plan"); }}>
        <label className="f">File (.xlsx, .csv or .json)<input type="file" accept=".xlsx,.csv,.json,text/csv,application/json" onChange={(e) => { setFile(e.target.files?.[0] ?? null); setPlan(null); setDone(null); }} /></label>
        <label className="adm-check" style={{ marginTop: 12 }}><input type="checkbox" checked={update} onChange={(e) => { setUpdate(e.target.checked); setPlan(null); }} /> Update existing projects (same slug): only the filled cells change</label>
        <div style={{ marginTop: 12 }}><button className="btn" disabled={busy || !file}>{busy && !plan ? "Checking…" : "1. Dry run"}</button></div>
      </form>
      {err && <div className="adm-msg err" role="alert">{err}</div>}
      {plan && (
        <div className="adm-card" style={{ marginTop: 16 }}>
          <h2 style={{ marginTop: 0 }}>Dry run: nothing has been saved</h2>
          <ImportTable res={plan} />
          <div className="adm-row" style={{ marginTop: 12 }}>
            <button className="btn" disabled={busy || !(plan.summary.create + plan.summary.update)} onClick={() => run("apply")}>
              2. Confirm: create {plan.summary.create}, update {plan.summary.update}
            </button>
            <button className="btn btn--outline" onClick={() => setPlan(null)}>Cancel</button>
            <span className="caption">Rows with errors are left out. The database is backed up automatically first.</span>
          </div>
        </div>
      )}
      {done && (
        <div className="adm-card" style={{ marginTop: 16 }}>
          <h2 style={{ marginTop: 0 }}>Done</h2>
          <div className="adm-msg">Created {done.summary.create}, updated {done.summary.update}. Backup made first: {done.backup || "n/a"}. <Link to="/admin/readiness">Check readiness</Link></div>
          <ImportTable res={done} />
        </div>
      )}
      {log.data && log.data.length > 0 && (
        <div className="adm-card" style={{ marginTop: 16 }}>
          <h2 style={{ marginTop: 0 }}>Import log</h2>
          <table className="adm-table adm-table--compact">
            <thead><tr><th>When</th><th>Who</th><th>What</th><th>File</th><th>Created</th><th>Updated</th><th>Skipped</th><th>Errors</th><th>Backup</th></tr></thead>
            <tbody>
              {log.data.map((l, i) => (
                <tr key={i}><td>{new Date(l.at).toLocaleString("en-GB")}</td><td>{l.user}</td><td>{l.kind}</td><td>{l.filename}</td><td>{l.created}</td><td>{l.updated}</td><td>{l.skipped}</td><td>{l.errors}</td><td>{l.backup}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
