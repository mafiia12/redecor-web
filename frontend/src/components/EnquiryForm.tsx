import { useRef, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { track } from "../lib/analytics";
import { ApiError, sendEnquiry, sendEnquiryWithFiles, type Country } from "../lib/api";
import { useData, useLang } from "../lib/context";

type Field = "name" | "phone" | "email" | "country" | "service" | "area" | "consent";
interface Values {
  name: string;
  code: string;
  phone: string;
  email: string;
  country: "" | Country;
  service: string;
  type: string;
  area: string;
  message: string;
  method: string;
  consent: boolean;
  website: string;
}
const ALLOWED = ["pdf", "dwg", "dxf", "xlsx", "xls", "docx", "jpg", "jpeg", "png", "zip"];
const ACCEPT = ALLOWED.map((x) => `.${x}`).join(",");
const MB = 1024 * 1024;
const ext = (name: string) => name.toLowerCase().split(".").pop() ?? "";

const BLANK: Values = { name: "", code: "+20", phone: "", email: "", country: "", service: "", type: "", area: "", message: "", method: "whatsapp", consent: false, website: "" };

function validate(v: Values): Partial<Record<Field, true>> {
  const e: Partial<Record<Field, true>> = {};
  if (v.name.trim().length < 2) e.name = true;
  const digits = v.phone.replace(/\D/g, "");
  if (digits.length < 6 || digits.length > 14 || !/^[\d\s\-()]+$/.test(v.phone)) e.phone = true;
  if (v.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.email.trim())) e.email = true;
  if (!v.country) e.country = true;
  if (!v.service) e.service = true;
  if (v.area && !(Number(v.area) >= 0 && Number(v.area) <= 1_000_000)) e.area = true;
  if (!v.consent) e.consent = true;
  return e;
}

export function EnquiryForm() {
  const { t, lang, lp } = useLang();
  const f = t.form;
  const [params] = useSearchParams();
  // Arriving from a project or service page (?about=…&ref=/projects/x): keep that context with the enquiry.
  const about = (params.get("about") ?? "").slice(0, 160);
  const ref = /^\/[a-z0-9\-/]*$/.test(params.get("ref") ?? "") ? params.get("ref")! : "";
  const [v, setV] = useState<Values>(() => ({ ...BLANK, message: about ? `${f.aboutPrefix} ${about}\n` : "" }));
  const started = useRef(Date.now());
  const [errs, setErrs] = useState<Partial<Record<Field, true>>>({});
  const [codeTouched, setCodeTouched] = useState(false);
  const [state, setState] = useState<"idle" | "sending" | "done">("idle");
  const [serverError, setServerError] = useState("");
  const form = useRef<HTMLFormElement>(null);
  const hasErrors = Object.keys(errs).length > 0;
  const { data } = useData();
  const limits = data?.attachments ?? { max_files: 3, max_file_mb: 15, max_total_mb: 30 };
  const [files, setFiles] = useState<File[]>([]);
  const [fileErr, setFileErr] = useState("");
  const [loaded, setLoaded] = useState<number | null>(null); // bytes uploaded so far while sending

  function addFiles(list: FileList | null) {
    if (!list) return;
    const next = [...files];
    let problem = "";
    for (const file of Array.from(list)) {
      if (next.some((x) => x.name === file.name && x.size === file.size)) continue;
      if (!ALLOWED.includes(ext(file.name)) || file.size === 0) problem ||= f.files.type(file.name);
      else if (file.size > limits.max_file_mb * MB) problem ||= f.files.tooLarge(file.name, limits.max_file_mb);
      else if (next.length >= limits.max_files) problem ||= f.files.tooMany(limits.max_files);
      else if (next.reduce((n, x) => n + x.size, 0) + file.size > limits.max_total_mb * MB) problem ||= f.files.total(limits.max_total_mb);
      else next.push(file);
    }
    setFiles(next);
    setFileErr(problem);
  }
  /** Server-side refusal of a file (content check, limits) as a friendly, translated message. */
  function fileProblem(err: ApiError): string {
    const d = (err.detail ?? {}) as { code?: string; file?: string; max?: number; max_mb?: number };
    if (d.code === "file_type") return f.files.type(d.file ?? "");
    if (d.code === "file_too_large") return f.files.tooLarge(d.file ?? "", d.max_mb ?? limits.max_file_mb);
    if (d.code === "too_many_files") return f.files.tooMany(d.max ?? limits.max_files);
    if (d.code === "total_too_large" || err.status === 413) return f.files.total(limits.max_total_mb);
    return "";
  }
  const totalSize = files.reduce((n, x) => n + x.size, 0);
  const fileProgress = (i: number) => {
    if (loaded === null || !totalSize) return 0;
    const before = files.slice(0, i).reduce((n, x) => n + x.size, 0);
    return Math.max(0, Math.min(1, (loaded - before) / files[i].size));
  };

  const set = <K extends keyof Values>(k: K, val: Values[K]) => {
    const next = { ...v, [k]: val };
    if (k === "country" && !codeTouched) next.code = val === "qa" ? "+974" : val === "sa" ? "+966" : "+20";
    setV(next);
    // Errors clear as each field is fixed.
    if (hasErrors) setErrs(validate(next));
  };

  const focusFirst = (e: Partial<Record<Field, true>>) => {
    const first = (["name", "phone", "email", "country", "service", "area", "consent"] as Field[]).find((k) => e[k]);
    if (first) form.current?.querySelector<HTMLElement>(`[name="${first}"]`)?.focus();
  };

  async function onSubmit(ev: FormEvent) {
    ev.preventDefault();
    if (state === "sending") return;
    const e = validate(v);
    setErrs(e);
    setServerError("");
    if (Object.keys(e).length) {
      focusFirst(e);
      return;
    }
    setState("sending");
    track("enquiry_submit");
    const payload = {
        name: v.name.trim(),
        phone: `${v.code} ${v.phone.trim()}`,
        email: v.email.trim(),
        country: v.country as Country,
        service: v.service,
        project_type: v.type,
        area_m2: v.area ? Number(v.area) : null,
        message: v.message.trim(),
        contact_method: v.method,
        lang,
        consent: v.consent,
        website: v.website,
        elapsed_ms: Date.now() - started.current,
        source: ref,
    };
    try {
      if (files.length) {
        setLoaded(0);
        // the request also carries the form fields: scale progress to the files' share of it
        await sendEnquiryWithFiles(payload, files, (done, all) => setLoaded((done / all) * totalSize));
      } else await sendEnquiry(payload);
      setLoaded(null);
      setFiles([]);
      track("enquiry_success");
      setState("done");
      window.scrollTo({ top: form.current ? form.current.getBoundingClientRect().top + window.scrollY - 140 : 0, behavior: "smooth" });
    } catch (err) {
      setState("idle");
      setLoaded(null);
      const fp = err instanceof ApiError ? fileProblem(err) : "";
      if (fp) {
        setFileErr(fp);
        setServerError(fp);
      } else if (err instanceof ApiError && err.status === 429) setServerError(f.tooMany);
      else if (err instanceof ApiError && err.status === 422) {
        const bad: Partial<Record<Field, true>> = {};
        const list = Array.isArray(err.detail) ? (err.detail as { loc?: string[] }[]) : [];
        for (const d of list) {
          const key = d.loc?.[d.loc.length - 1];
          if (key === "project_type") continue;
          if (key && ["name", "phone", "email", "country", "service", "consent"].includes(key)) bad[key as Field] = true;
          if (key === "area_m2") bad.area = true;
        }
        setErrs(bad);
        focusFirst(bad);
      } else setServerError(f.network);
    }
  }

  if (state === "done") {
    return (
      <div className="success fade-in" role="status">
        <h3>{f.okTitle}</h3>
        <p className="lead">{f.ok(f.methods[v.method].toLowerCase())}</p>
        <button
          type="button"
          className="btn btn--outline"
          onClick={() => {
            setV(BLANK);
            setFiles([]);
            setFileErr("");
            setErrs({});
            setCodeTouched(false);
            setState("idle");
          }}
        >
          {f.again}
        </button>
      </div>
    );
  }

  const bad = (k: Field) => (errs[k] ? true : undefined);
  const errMsg = (k: Field) => errs[k] && <span className="err" id={`err-${k}`}>{f.errors[k]}</span>;
  const desc = (k: Field) => (errs[k] ? `err-${k}` : undefined);

  return (
    <form ref={form} className="form" onSubmit={onSubmit} noValidate aria-busy={state === "sending"}>
      {(hasErrors || serverError) && (
        <div className="alert full" role="alert">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" style={{ flex: "none" }} aria-hidden="true">
            <circle cx="10" cy="10" r="8" />
            <path d="M10 6v5M10 13.6v.1" strokeLinecap="round" />
          </svg>
          <span>{serverError || f.summary}</span>
        </div>
      )}

      <div className="field">
        <label htmlFor="f-name">{f.name}</label>
        <input id="f-name" name="name" className="input" autoComplete="name" value={v.name} onChange={(e) => set("name", e.target.value)} aria-invalid={bad("name")} aria-describedby={desc("name")} maxLength={120} />
        {errMsg("name")}
      </div>

      <div className="field">
        <label htmlFor="f-phone">{f.phone}</label>
        <div className="phone">
          <select
            className="select"
            aria-label={f.code}
            value={v.code}
            onChange={(e) => {
              setCodeTouched(true);
              set("code", e.target.value);
            }}
          >
            <option value="+20">+20</option>
            <option value="+974">+974</option>
            <option value="+966">+966</option>
          </select>
          <input id="f-phone" name="phone" type="tel" inputMode="tel" autoComplete="tel-national" className="input ltr-input" placeholder={f.phonePh} value={v.phone} onChange={(e) => set("phone", e.target.value)} aria-invalid={bad("phone")} aria-describedby={desc("phone")} maxLength={30} />
        </div>
        {errMsg("phone")}
      </div>

      <div className="field">
        <label htmlFor="f-email">{f.email}</label>
        <input id="f-email" name="email" type="email" autoComplete="email" className="input ltr-input" placeholder="name@example.com" value={v.email} onChange={(e) => set("email", e.target.value)} aria-invalid={bad("email")} aria-describedby={desc("email")} maxLength={200} />
        {errMsg("email")}
      </div>

      <div className="field">
        <label htmlFor="f-country">{f.country}</label>
        <select id="f-country" name="country" className="select" value={v.country} onChange={(e) => set("country", e.target.value as Values["country"])} aria-invalid={bad("country")} aria-describedby={desc("country")}>
          <option value="">{f.select}</option>
          <option value="eg">{t.countries.eg}</option>
          <option value="qa">{t.countries.qa}</option>
          <option value="sa">{t.countries.sa}</option>
        </select>
        {errMsg("country")}
      </div>

      <div className="field">
        <label htmlFor="f-service">{f.service}</label>
        <select id="f-service" name="service" className="select" value={v.service} onChange={(e) => set("service", e.target.value)} aria-invalid={bad("service")} aria-describedby={desc("service")}>
          <option value="">{f.select}</option>
          {Object.entries(f.services).map(([k, label]) => (
            <option key={k} value={k}>{label}</option>
          ))}
        </select>
        {errMsg("service")}
      </div>

      <div className="field">
        <label htmlFor="f-type">{f.type}</label>
        <select id="f-type" name="type" className="select" value={v.type} onChange={(e) => set("type", e.target.value)}>
          <option value="">{f.select}</option>
          {Object.entries(t.types).map(([k, label]) => (
            <option key={k} value={k}>{label}</option>
          ))}
        </select>
      </div>

      <div className="field">
        <label htmlFor="f-area">{f.area}</label>
        <div style={{ position: "relative" }}>
          <input id="f-area" name="area" type="number" inputMode="decimal" min={0} className="input ltr-input" placeholder={f.areaPh} value={v.area} onChange={(e) => set("area", e.target.value)} aria-invalid={bad("area")} aria-describedby={desc("area")} style={{ paddingRight: 56 }} />
          {/* the number reads left-to-right in both languages, so the unit sits on the physical right */}
          <span className="caption" style={{ position: "absolute", right: 16, top: 16 }}>{f.unit}</span>
        </div>
        {errMsg("area")}
      </div>

      <div className="field full">
        <label htmlFor="f-message">{f.message}</label>
        <textarea id="f-message" className="textarea" placeholder={f.msgPh} value={v.message} onChange={(e) => set("message", e.target.value)} maxLength={4000} />
      </div>

      <div className="field full" role="radiogroup" aria-labelledby="f-method">
        <span className="label" id="f-method">{f.method}</span>
        <div className="radios">
          {Object.entries(f.methods).map(([k, label]) => (
            <label key={k}>
              <input type="radio" name="method" value={k} checked={v.method === k} onChange={() => set("method", k)} />
              <span>{label}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="field full">
        <span className="label" id="f-files-label">{f.files.label}</span>
        <p className="caption" id="f-files-hint" style={{ margin: "0 0 8px" }}>{f.files.hint(limits.max_files, limits.max_file_mb, limits.max_total_mb)} {f.files.privacy}</p>
        <label className={`btn btn--outline btn--sm file-pick${files.length >= limits.max_files || state === "sending" ? " is-disabled" : ""}`}>
          {f.files.add}
          <input
            type="file"
            name="files"
            multiple
            accept={ACCEPT}
            className="sr-only"
            aria-labelledby="f-files-label"
            aria-describedby={fileErr ? "f-files-err f-files-hint" : "f-files-hint"}
            disabled={files.length >= limits.max_files || state === "sending"}
            onChange={(e) => {
              addFiles(e.target.files);
              e.target.value = "";
            }}
          />
        </label>
        {fileErr && <span className="err" id="f-files-err" role="alert">{fileErr}</span>}
        {files.length > 0 && (
          <ul className="file-list">
            {files.map((file, i) => (
              <li key={`${file.name}-${file.size}`}>
                <span className="file-list__name" dir="auto">{file.name}</span>
                <span className="caption">{f.files.size((file.size / MB).toFixed(1))}</span>
                {loaded !== null ? (
                  <progress max={1} value={fileProgress(i)} aria-label={f.files.uploading(Math.round(fileProgress(i) * 100))} />
                ) : (
                  <button type="button" className="file-list__remove" aria-label={f.files.remove(file.name)} onClick={() => { setFiles(files.filter((_, j) => j !== i)); setFileErr(""); }}>
                    ×
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Honeypot: hidden from people and assistive tech; bots fill it in. */}
      <div className="hp" aria-hidden="true">
        <label>
          Website
          <input tabIndex={-1} autoComplete="off" name="website" value={v.website} onChange={(e) => set("website", e.target.value)} />
        </label>
      </div>

      <div className="field full">
        <label className="check">
          <input type="checkbox" name="consent" checked={v.consent} onChange={(e) => set("consent", e.target.checked)} aria-invalid={bad("consent")} aria-describedby={desc("consent")} />
          <span>
            {f.consent} <Link to={lp("/privacy")}>{f.privacy}</Link>
          </span>
        </label>
        {errMsg("consent")}
      </div>

      <div className="full btn-row btn-row--stack">
        <button type="submit" className="btn" disabled={state === "sending"}>
          {state === "sending" ? (loaded !== null && totalSize ? f.files.uploading(Math.round((loaded / totalSize) * 100)) : f.sending) : f.send}
        </button>
        <span className="caption">{f.req}</span>
      </div>
    </form>
  );
}
