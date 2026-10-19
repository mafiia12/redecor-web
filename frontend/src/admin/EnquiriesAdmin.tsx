import { useEffect, useState, type FormEvent } from "react";
import { api, downloadFile, errorText, json, useLoad, type AdminEnquiry, type EnquiryDetail, type EnquiryStatus } from "./api";

const STATUS_LABEL: Record<EnquiryStatus, string> = {
  new: "New",
  contacted: "Contacted",
  quoted: "Quoted",
  won: "Won",
  lost: "Lost",
  spam: "Spam",
  closed: "Closed (old)",
};
const STATUS_TAG: Partial<Record<EnquiryStatus, string>> = { new: "warn", won: "ok", spam: "", lost: "" };
const NOTIFY: Record<string, [string, string]> = {
  sent: ["ok", "E-mailed"],
  failed: ["warn", "E-mail failed"],
  not_configured: ["warn", "E-mail not configured"],
  pending: ["", "E-mail pending"],
  sending: ["", "Sending…"],
  legacy: ["", "Before e-mail alerts"],
};
const SCAN: Record<string, [string, string]> = {
  clean: ["ok", "Scanned: clean"],
  quarantine: ["warn", "Not scanned (scanner off): open with care"],
  error: ["warn", "Scan failed: open with care"],
  infected: ["warn", "Blocked: virus found"],
};
const fmt = (s: string) => new Date(s).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" });
const kb = (n: number) => (n > 1024 * 1024 ? `${(n / 1024 / 1024).toFixed(1)} MB` : `${Math.ceil(n / 1024)} KB`);

interface Filters {
  status: string;
  assignee: string;
  overdue: boolean;
  date_from: string;
  date_to: string;
  lang: string;
  q: string;
}
const NO_FILTERS: Filters = { status: "open", assignee: "", overdue: false, date_from: "", date_to: "", lang: "", q: "" };

function query(f: Filters, format = "json") {
  const p = new URLSearchParams();
  Object.entries(f).forEach(([k, v]) => {
    if (v) p.set(k, String(v));
  });
  if (format !== "json") p.set("format", format);
  return `/enquiries?${p.toString()}`;
}

export default function EnquiriesAdmin() {
  const [filters, setFilters] = useState<Filters>(NO_FILTERS);
  const [applied, setApplied] = useState<Filters>(NO_FILTERS);
  const { data, error, reload, setData } = useLoad<AdminEnquiry[]>(query(applied));
  const people = useLoad<{ id: number; email: string }[]>("/enquiries/assignees");
  const [openId, setOpenId] = useState<number | null>(null);
  const [msg, setMsg] = useState("");
  const [digest, setDigest] = useState<string | null>(null);

  function search(e: FormEvent) {
    e.preventDefault();
    setApplied(filters);
  }
  const replace = (u: AdminEnquiry) => setData((d) => d?.map((x) => (x.id === u.id ? { ...x, ...u } : x)) ?? d);
  async function resend(e: AdminEnquiry) {
    try {
      const u = await api<AdminEnquiry>(`/enquiries/${e.id}/notify`, { method: "POST" });
      replace(u);
      setMsg(u.notify_status === "sent" ? "" : `E-mail not sent: ${u.notify_error || u.notify_status}`);
    } catch (x) {
      setMsg(errorText(x));
    }
  }
  const overdue = (data ?? []).filter((e) => e.overdue).length;

  return (
    <>
      <div className="adm-bar">
        <h1>Enquiries</h1>
        <div className="adm-row">
          <button className="btn btn--sm btn--outline" onClick={() => downloadFile(query(applied, "xlsx"), "enquiries.xlsx").catch((x) => setMsg(errorText(x)))}>Export XLSX</button>
          <button className="btn btn--sm btn--outline" onClick={() => downloadFile(query(applied, "csv"), "enquiries.csv").catch((x) => setMsg(errorText(x)))}>Export CSV</button>
          <button className="btn btn--sm btn--outline" onClick={() => api<{ text: string }>("/enquiries/digest-preview").then((r) => setDigest(r.text)).catch((x) => setMsg(errorText(x)))}>Preview daily digest</button>
        </div>
      </div>
      <p className="caption">Enquiries contain personal data: only admins can see them. Keep them only as long as needed (see docs/SECURITY_REVIEW.md, retention).</p>
      <form className="adm-card adm-filters" onSubmit={search} aria-label="Filter enquiries">
        <label className="f">Status
          <select className="select" value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
            <option value="open">Open (not finished)</option>
            <option value="">All</option>
            {(Object.keys(STATUS_LABEL) as EnquiryStatus[]).map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
          </select>
        </label>
        <label className="f">Assigned to
          <select className="select" value={filters.assignee} onChange={(e) => setFilters({ ...filters, assignee: e.target.value })}>
            <option value="">Anyone</option>
            <option value="me">Me</option>
            <option value="none">Nobody</option>
            {(people.data ?? []).map((p) => <option key={p.id} value={String(p.id)}>{p.email}</option>)}
          </select>
        </label>
        <label className="f">Language
          <select className="select" value={filters.lang} onChange={(e) => setFilters({ ...filters, lang: e.target.value })}>
            <option value="">Both</option>
            <option value="en">English</option>
            <option value="ar">Arabic</option>
          </select>
        </label>
        <label className="f">Received from<input className="input" type="date" value={filters.date_from} onChange={(e) => setFilters({ ...filters, date_from: e.target.value })} /></label>
        <label className="f">to<input className="input" type="date" value={filters.date_to} onChange={(e) => setFilters({ ...filters, date_to: e.target.value })} /></label>
        <label className="f">Search<input className="input" type="search" placeholder="Name, phone, e-mail, message" value={filters.q} onChange={(e) => setFilters({ ...filters, q: e.target.value })} /></label>
        <label className="adm-check"><input type="checkbox" checked={filters.overdue} onChange={(e) => setFilters({ ...filters, overdue: e.target.checked })} /> Overdue follow-up only</label>
        <div className="adm-row">
          <button className="btn btn--sm">Apply</button>
          <button type="button" className="btn btn--sm btn--outline" onClick={() => { setFilters(NO_FILTERS); setApplied(NO_FILTERS); }}>Reset</button>
        </div>
      </form>
      {digest !== null && (
        <div className="adm-card" style={{ marginTop: 12 }}>
          <div className="adm-bar"><strong>Daily digest preview (nothing was sent)</strong><button className="btn btn--sm btn--outline" onClick={() => setDigest(null)}>Close</button></div>
          <pre className="adm-pre">{digest}</pre>
        </div>
      )}
      {(msg || error) && <div className="adm-msg err" role="alert">{msg || error}</div>}
      {data && <p className="caption">{data.length} enquiries{overdue > 0 && <> · <span className="adm-tag warn">{overdue} overdue</span></>}</p>}
      {data && data.length === 0 && <p className="caption">No enquiries match.</p>}
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {(data ?? []).map((e) => (
          <article className={`adm-card${e.overdue ? " adm-card--overdue" : ""}`} key={e.id}>
            <div className="adm-bar" style={{ marginBottom: 8 }}>
              <strong>#{e.id} {e.name}</strong>
              <div className="adm-row">
                {e.overdue && <span className="adm-tag warn">Overdue follow-up</span>}
                <span className={`adm-tag ${STATUS_TAG[e.status] ?? ""}`}>{STATUS_LABEL[e.status]}</span>
                <span className="caption">{fmt(e.created_at)}</span>
                <button className="btn btn--sm btn--outline" aria-expanded={openId === e.id} onClick={() => setOpenId(openId === e.id ? null : e.id)}>{openId === e.id ? "Close" : "Open"}</button>
              </div>
            </div>
            <div className="adm-row" style={{ gap: 12, marginBottom: 8, flexWrap: "wrap" }}>
              <a href={`tel:${e.phone.replace(/\s/g, "")}`} dir="ltr">{e.phone}</a>
              {e.email && <a href={`mailto:${e.email}`}>{e.email}</a>}
              <span className="adm-tag">{e.country.toUpperCase()}</span>
              <span className="adm-tag">{e.service}</span>
              {e.project_type && <span className="adm-tag">{e.project_type}</span>}
              {e.area_m2 != null && <span className="adm-tag">{e.area_m2} m²</span>}
              <span className="adm-tag">prefers {e.contact_method}</span>
              <span className="adm-tag">{e.lang === "ar" ? "Arabic" : "English"}</span>
              {e.attachment_count > 0 && <span className="adm-tag">{e.attachment_count} file{e.attachment_count > 1 ? "s" : ""}</span>}
              <span className="caption">{e.assigned_to ? `Assigned: ${e.assigned_to}` : "Unassigned"}{e.next_follow_up && ` · follow-up ${e.next_follow_up}`}</span>
              {NOTIFY[e.notify_status] && <span className={`adm-tag ${NOTIFY[e.notify_status][0]}`} title={e.notify_error || undefined}>{NOTIFY[e.notify_status][1]}</span>}
              {["failed", "not_configured", "pending"].includes(e.notify_status) && <button className="btn btn--sm btn--outline" onClick={() => resend(e)}>Retry e-mail</button>}
            </div>
            {e.source_page && <p className="caption" style={{ margin: "0 0 6px" }}>Sent from: {e.source_page}</p>}
            {e.message && <p style={{ whiteSpace: "pre-wrap", margin: 0 }}>{e.message}</p>}
            {openId === e.id && <EnquiryPanel id={e.id} people={people.data ?? []} onChange={(u) => { replace(u); reload(); }} />}
          </article>
        ))}
      </div>
    </>
  );
}

function EnquiryPanel({ id, people, onChange }: { id: number; people: { id: number; email: string }[]; onChange: (e: AdminEnquiry) => void }) {
  const { data, setData, error } = useLoad<EnquiryDetail>(`/enquiries/${id}`);
  const [status, setStatus] = useState<EnquiryStatus | "">("");
  const [assignee, setAssignee] = useState("");
  const [follow, setFollow] = useState("");
  const [note, setNote] = useState("");
  const [msg, setMsg] = useState("");
  useEffect(() => {
    if (!data) return;
    setAssignee(data.assigned_to_id ? String(data.assigned_to_id) : "");
    setFollow(data.next_follow_up ?? "");
  }, [data]);
  if (error) return <div className="adm-msg err">{error}</div>;
  if (!data) return <p className="caption">Loading…</p>;

  async function save(e: FormEvent) {
    e.preventDefault();
    if (!data) return;
    const body: Record<string, unknown> = {};
    if (status) body.status = status;
    if (assignee !== (data.assigned_to_id ? String(data.assigned_to_id) : "")) body.assigned_to_id = assignee ? Number(assignee) : null;
    if (follow !== (data.next_follow_up ?? "")) body.next_follow_up = follow || null;
    if (note.trim()) body.note = note.trim();
    if (!Object.keys(body).length) return;
    try {
      const u = await api<EnquiryDetail>(`/enquiries/${id}`, json("PATCH", body));
      setData(u);
      setStatus("");
      setNote("");
      setMsg("Saved.");
      onChange(u);
    } catch (x) {
      setMsg(errorText(x));
    }
  }
  const describe = (ev: EnquiryDetail["events"][number]) =>
    ev.kind === "status" ? `Status ${STATUS_LABEL[ev.from_value as EnquiryStatus] ?? ev.from_value} → ${STATUS_LABEL[ev.to_value as EnquiryStatus] ?? ev.to_value}`
      : ev.kind === "assign" ? `Assigned ${ev.from_value || "nobody"} → ${ev.to_value || "nobody"}`
        : ev.kind === "follow_up" ? `Follow-up ${ev.from_value || "none"} → ${ev.to_value || "none"}`
          : "Note";

  return (
    <div className="adm-panel" style={{ marginTop: 12 }}>
      {data.attachments.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <strong>Files</strong>
          <ul className="adm-files">
            {data.attachments.map((a) => (
              <li key={a.id}>
                <span>{a.original_name}</span> <span className="caption">{a.detected_type.toUpperCase()} · {kb(a.size)}</span>{" "}
                <span className={`adm-tag ${SCAN[a.scan_status]?.[0] ?? ""}`} title={a.scan_detail}>{SCAN[a.scan_status]?.[1] ?? a.scan_status}</span>{" "}
                {a.scan_status !== "infected" && (
                  <button className="btn btn--sm btn--outline" onClick={() => downloadFile(`/enquiries/${id}/attachments/${a.id}`, a.original_name).catch((x) => setMsg(errorText(x)))}>Download</button>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
      <form onSubmit={save} className="adm-grid">
        <label className="f">Change status
          <select className="select" value={status} onChange={(e) => setStatus(e.target.value as EnquiryStatus)}>
            <option value="">Keep: {STATUS_LABEL[data.status]}</option>
            {data.next_statuses.map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
          </select>
        </label>
        <label className="f">Assigned to
          <select className="select" value={assignee} onChange={(e) => setAssignee(e.target.value)}>
            <option value="">Nobody</option>
            {people.map((p) => <option key={p.id} value={String(p.id)}>{p.email}</option>)}
          </select>
        </label>
        <label className="f">Next follow-up<input className="input" type="date" value={follow} onChange={(e) => setFollow(e.target.value)} /></label>
        <label className="f" style={{ gridColumn: "1 / -1" }}>Internal note (never sent to the client)<textarea className="input" rows={2} value={note} onChange={(e) => setNote(e.target.value)} /></label>
        <div className="adm-row"><button className="btn btn--sm">Save</button>{msg && <span className="caption" role="status">{msg}</span>}</div>
      </form>
      <strong style={{ display: "block", marginTop: 12 }}>History</strong>
      {data.events.length === 0 && <p className="caption">No changes yet.</p>}
      <ol className="adm-history">
        {data.events.map((ev) => (
          <li key={ev.id}>
            <span className="caption">{fmt(ev.at)} · {ev.user_email}</span> <b>{describe(ev)}</b>
            {ev.note && <div style={{ whiteSpace: "pre-wrap" }}>{ev.note}</div>}
          </li>
        ))}
      </ol>
    </div>
  );
}
