import { useEffect, useState, type FormEvent } from "react";
import { Navigate, NavLink, Outlet, Route, Routes, useNavigate } from "react-router-dom";
import { api, can, errorText, getToken, json, MeContext, setToken, type Me } from "./api";
import { AccountAdmin, DocumentsAdmin, SystemAdmin, TestimonialsAdmin, UsersAdmin } from "./SystemAdmin";
import ProjectPreview from "./ProjectPreview";
import { BulkImagesAdmin, ImportAdmin, ReadinessAdmin } from "./ContentTools";
import ClientsAdmin from "./ClientsAdmin";
import EnquiriesAdmin from "./EnquiriesAdmin";
import OfficesAdmin from "./OfficesAdmin";
import { ProjectEdit, ProjectsAdmin } from "./ProjectsAdmin";
import SiteImagesAdmin from "./SiteImagesAdmin";
import "./admin.css";

function Login() {
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    document.title = "Staff login | RE DECOR & MORE";
    document.documentElement.lang = "en";
    document.documentElement.dir = "ltr";
  }, []);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      const r = await api<{ token: string }>("/login", json("POST", { email, password }));
      setToken(r.token);
      nav("/admin", { replace: true });
    } catch (x) {
      setErr(errorText(x));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="adm adm-login">
      <form className="adm-card" onSubmit={submit}>
        <img src="/logo-ink.svg" alt="RE DECOR & MORE" height={40} style={{ height: 40, width: "auto", alignSelf: "flex-start" }} />
        <h1 style={{ fontSize: 22, margin: 0 }}>Staff login</h1>
        {err && <div className="adm-msg err" role="alert" style={{ margin: 0 }}>{err}</div>}
        <label className="f">Email<input className="input" type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
        <label className="f">Password<input className="input" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required /></label>
        <button className="btn" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
      </form>
    </div>
  );
}

function Shell() {
  const nav = useNavigate();
  const [me, setMe] = useState<Me | null | false>(null);

  useEffect(() => {
    document.title = "Admin | RE DECOR & MORE";
    document.documentElement.lang = "en";
    document.documentElement.dir = "ltr";
    if (!getToken()) return setMe(false);
    api<Me>("/me").then(setMe).catch(() => setMe(false));
  }, []);

  if (me === null) return null;
  if (!me) return <Navigate to="/admin/login" replace />;

  const link = ({ isActive }: { isActive: boolean }) => (isActive ? "active" : undefined);
  return (
    <MeContext.Provider value={me}>
    <div className="adm adm-shell">
      <aside className="adm-side">
        <img src="/logo-light.svg" alt="RE DECOR & MORE" />
        <NavLink to="/admin/projects" className={link}>Projects</NavLink>
        <NavLink to="/admin/readiness" className={link}>Readiness</NavLink>
        {can(me, "editor") && <NavLink to="/admin/bulk-images" className={link}>Bulk photo upload</NavLink>}
        {can(me, "editor") && <NavLink to="/admin/import" className={link}>Import projects</NavLink>}
        <NavLink to="/admin/clients" className={link}>Clients</NavLink>
        <NavLink to="/admin/images" className={link}>Site images</NavLink>
        <NavLink to="/admin/documents" className={link}>Documents</NavLink>
        <NavLink to="/admin/testimonials" className={link}>Testimonials</NavLink>
        <NavLink to="/admin/offices" className={link}>Offices</NavLink>
        {can(me, "editor") && <NavLink to="/admin/enquiries" className={link}>Enquiries</NavLink>}
        <NavLink to="/admin/system" className={link}>Status &amp; analytics</NavLink>
        {can(me, "admin") && <NavLink to="/admin/users" className={link}>Users</NavLink>}
        <span className="grow" />
        <NavLink to="/admin/account" className={link}>{me.email} · {me.role}</NavLink>
        <a href="/" target="_blank" rel="noreferrer">View site ↗</a>
        <button onClick={() => { setToken(null); nav("/admin/login"); }}>Sign out</button>
      </aside>
      <main className="adm-main">
        {!can(me, "editor") && <div className="adm-msg">Read-only access: you can view everything but not change it.</div>}
        <Outlet />
      </main>
    </div>
    </MeContext.Provider>
  );
}

export default function AdminApp() {
  return (
    <Routes>
      <Route path="login" element={<Login />} />
      <Route element={<Shell />}>
        <Route index element={<Navigate to="projects" replace />} />
        <Route path="projects" element={<ProjectsAdmin />} />
        <Route path="projects/:id" element={<ProjectEdit />} />
        <Route path="clients" element={<ClientsAdmin />} />
        <Route path="images" element={<SiteImagesAdmin />} />
        <Route path="offices" element={<OfficesAdmin />} />
        <Route path="enquiries" element={<EnquiriesAdmin />} />
        <Route path="projects/:id/preview" element={<ProjectPreview />} />
        <Route path="documents" element={<DocumentsAdmin />} />
        <Route path="readiness" element={<ReadinessAdmin />} />
        <Route path="bulk-images" element={<BulkImagesAdmin />} />
        <Route path="import" element={<ImportAdmin />} />
        <Route path="testimonials" element={<TestimonialsAdmin />} />
        <Route path="system" element={<SystemAdmin />} />
        <Route path="users" element={<UsersAdmin />} />
        <Route path="account" element={<AccountAdmin />} />
        <Route path="*" element={<Navigate to="projects" replace />} />
      </Route>
    </Routes>
  );
}
