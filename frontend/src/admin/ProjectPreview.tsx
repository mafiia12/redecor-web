import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { LangProvider } from "../lib/context";
import type { ProjectDetail } from "../lib/api";
import { ProjectView } from "../pages/ProjectDetail";
import { api, errorText } from "./api";

/** Draft preview: the real project page component, fed by the admin API (works for unpublished projects). */
export default function ProjectPreview() {
  const { id } = useParams();
  const [p, setP] = useState<ProjectDetail | null>(null);
  const [err, setErr] = useState("");
  const [lang, setLang] = useState<"en" | "ar">("en");
  useEffect(() => {
    api<ProjectDetail>(`/projects/${id}/preview`).then(setP).catch((e) => setErr(errorText(e)));
  }, [id]);
  return (
    <>
      <div className="adm-bar">
        <h1>Preview</h1>
        <div className="adm-row">
          <button className="btn btn--sm btn--outline" onClick={() => setLang(lang === "en" ? "ar" : "en")}>{lang === "en" ? "عربي" : "English"}</button>
          <Link className="btn btn--sm" to={`/admin/projects/${id}`}>Back to editing</Link>
        </div>
      </div>
      <p className="caption">This is how the page will look once published. Draft pages are not visible to the public.</p>
      {err && <div className="adm-msg err">{err}</div>}
      {p && (
        <div className="adm-preview" dir={lang === "ar" ? "rtl" : "ltr"} lang={lang}>
          <LangProvider lang={lang} syncDocument={false}>
            <ProjectView p={p} preview />
          </LangProvider>
        </div>
      )}
    </>
  );
}
