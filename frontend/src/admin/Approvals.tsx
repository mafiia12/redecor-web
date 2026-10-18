import { useState, type FormEvent } from "react";
import { api, can, errorText, multipart, downloadFile, useLoad, useMe } from "./api";

interface ApprovalRow {
  id: number;
  approval_type: string;
  status: string;
  approved_by_name: string;
  approver_organization: string;
  approval_date: string | null;
  evidence_note: string;
  has_evidence: boolean;
  evidence_filename: string;
  recorded_by: string;
  created_at: string;
}
interface Register {
  required_type: string;
  current: string;
  history: ApprovalRow[];
}

const TYPES = [
  ["client_permission_to_publish", "Client permission to publish"],
  ["logo_usage_permission", "Logo usage permission"],
  ["photo_rights", "Photo rights"],
] as const;
const TAG: Record<string, string> = { approved: "ok", pending: "", rejected: "warn", revoked: "warn", none: "warn" };

/** Append-only approvals register for one project or client: full history + "record a new status". */
export function Approvals({ subjectType, subjectId, onChange }: { subjectType: "project" | "client"; subjectId: number; onChange?: () => void }) {
  const me = useMe();
  const { data, reload } = useLoad<Register>(`/approvals?subject_type=${subjectType}&subject_id=${subjectId}`);
  const [open, setOpen] = useState(false);
  const [msg, setMsg] = useState("");
  const required = data?.required_type ?? (subjectType === "project" ? "client_permission_to_publish" : "logo_usage_permission");
  const [v, setV] = useState({ approval_type: required, status: "approved", approved_by_name: "", approver_organization: "", approval_date: "", evidence_note: "" });
  const [file, setFile] = useState<File | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setMsg("");
    try {
      await api("/approvals", multipart("POST", { ...v, subject_type: subjectType, subject_id: subjectId }, { evidence: file }));
      setOpen(false);
      setFile(null);
      reload();
      onChange?.();
    } catch (x) {
      setMsg(errorText(x));
    }
  }
  const label = (t: string) => TYPES.find(([k]) => k === t)?.[1] ?? t;

  return (
    <div className="adm-card adm-approvals">
      <div className="adm-bar" style={{ marginBottom: 8 }}>
        <strong>Approvals</strong>
        <span className={`adm-tag ${TAG[data?.current ?? "none"]}`}>
          {label(required)}: {data?.current === "none" ? "not recorded" : data?.current}
        </span>
      </div>
      <p className="caption" style={{ margin: "0 0 10px" }}>
        The public site shows this item only when its newest “{label(required)}” record is <b>approved</b>. Records are never edited or deleted: a change of status adds a new line.
      </p>
      {data && data.history.length > 0 && (
        <table className="adm-table" style={{ marginBottom: 12 }}>
          <thead><tr><th>Date recorded</th><th>Type</th><th>Status</th><th>Given by</th><th>How</th><th>Recorded by</th><th>Evidence</th></tr></thead>
          <tbody>
            {data.history.map((h) => (
              <tr key={h.id}>
                <td>{new Date(h.created_at).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" })}</td>
                <td>{label(h.approval_type)}</td>
                <td><span className={`adm-tag ${TAG[h.status]}`}>{h.status}</span></td>
                <td>{[h.approved_by_name, h.approver_organization].filter(Boolean).join(", ")}{h.approval_date && ` (${h.approval_date})`}</td>
                <td>{h.evidence_note}</td>
                <td>{h.recorded_by}</td>
                <td>{h.has_evidence && <button className="btn btn--sm btn--outline" onClick={() => downloadFile(`/approvals/${h.id}/evidence`, "evidence").catch((x) => setMsg(errorText(x)))}>Download</button>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {msg && <div className="adm-msg err">{msg}</div>}
      {can(me, "editor") && !open && <button className="btn btn--sm" onClick={() => setOpen(true)}>Record approval status</button>}
      {open && (
        <form onSubmit={submit} className="adm-grid" style={{ marginTop: 8 }}>
          <label className="f">Type<select className="select" value={v.approval_type} onChange={(e) => setV({ ...v, approval_type: e.target.value })}>{TYPES.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></label>
          <label className="f">Status<select className="select" value={v.status} onChange={(e) => setV({ ...v, status: e.target.value })}><option value="approved">Approved</option><option value="pending">Pending</option><option value="rejected">Rejected</option><option value="revoked">Revoked</option></select></label>
          <label className="f">Given by (name){v.status === "approved" && " *"}<input className="input" value={v.approved_by_name} onChange={(e) => setV({ ...v, approved_by_name: e.target.value })} /></label>
          <label className="f">Organization<input className="input" value={v.approver_organization} onChange={(e) => setV({ ...v, approver_organization: e.target.value })} /></label>
          <label className="f">Date given<input className="input" type="date" value={v.approval_date} onChange={(e) => setV({ ...v, approval_date: e.target.value })} /></label>
          <label className="f">How it was given (e-mail, letter, verbal…){v.status === "approved" && " *"}<input className="input" value={v.evidence_note} onChange={(e) => setV({ ...v, evidence_note: e.target.value })} /></label>
          <label className="f">Evidence file (optional, PDF/JPG/PNG…)<input type="file" onChange={(e) => setFile(e.target.files?.[0] ?? null)} /></label>
          <div className="adm-row" style={{ alignSelf: "end" }}>
            <button className="btn btn--sm">Save record</button>
            <button type="button" className="btn btn--sm btn--outline" onClick={() => setOpen(false)}>Cancel</button>
          </div>
        </form>
      )}
    </div>
  );
}
