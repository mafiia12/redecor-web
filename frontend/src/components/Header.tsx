import { useEffect, useRef, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { toggleTheme, useMode } from "../lib/theme";
import { useData, useLang } from "../lib/context";
import type { ProjectType } from "../lib/api";

export function Header() {
  const { t, lp, altPath, lang } = useLang();
  const { data } = useData();
  const present = (["residential", "hospitality", "retail", "office", "industrial", "healthcare", "public", "education", "landscape"] as ProjectType[]).filter((x) => data?.projects.some((p) => p.type === x));
  const { pathname } = useLocation();
  const mode = useMode();
  const [dark, setDark] = useState(false);
  const [hidden, setHidden] = useState(false);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLElement>(null);
  const lastY = useRef(0);
  const openRef = useRef(false);
  openRef.current = open;

  // Hide on scroll down, return on scroll up; switch to the dark style while over a dark section.
  useEffect(() => {
    let raf = 0;
    const update = () => {
      raf = 0;
      const y = window.scrollY;
      if (!openRef.current) {
        if (y > lastY.current + 4 && y > 120) setHidden(true);
        else if (y < lastY.current - 4 || y <= 120) setHidden(false);
      }
      lastY.current = y;
      const els = document.elementsFromPoint(window.innerWidth / 2, 26);
      const behind = els.find((e) => !ref.current?.contains(e) && e !== document.documentElement && e !== document.body);
      setDark(!!behind?.closest("[data-dark]"));
    };
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      if (raf) cancelAnimationFrame(raf);
    };
  }, [pathname]);

  useEffect(() => setOpen(false), [pathname]);

  // Mobile sheet: lock scroll, close on Escape.
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const links = [
    { to: lp("/services/fitout"), label: t.nav.services, match: "/services" },
    { to: lp("/projects"), label: t.nav.projects, match: "/projects" },
    { to: lp("/about"), label: t.nav.about, match: "/about" },
    { to: lp("/#clients"), label: t.nav.clients, match: "#clients" },
    { to: lp("/contact"), label: t.nav.contact, match: "/contact" },
  ];
  const bare = lang === "ar" ? pathname.replace(/^\/ar/, "") : pathname;
  const isActive = (m: string) => !m.startsWith("#") && bare.startsWith(m);
  const theme = (mode === "dark" || dark) && !open ? "dark" : "light";

  return (
    <header ref={ref} className="header" data-theme={theme} data-hidden={hidden && !open}>
      <div className="header__inner">
        <Link to={lp("/")} className="header__logo" aria-label={`${t.brand}, ${lang === "ar" ? "الرئيسية" : "home"}`}>
          <img src={theme === "dark" ? "/logo-light.svg" : "/logo-ink.svg"} alt={t.brand} width={48} height={28} />
        </Link>
        <nav className="header__nav" aria-label="Main">
          {links.map((l) =>
            l.match === "/projects" && present.length > 1 ? (
              <div className="dd" key={l.to}>
                <Link to={l.to} aria-current={isActive(l.match) ? "page" : undefined} aria-haspopup="true">
                  {l.label}
                </Link>
                <div className="dd__menu">
                  <Link to={l.to}>{t.filters.all}</Link>
                  {present.map((x) => (
                    <Link key={x} to={`${l.to}?type=${x}`}>{t.types[x]}</Link>
                  ))}
                </div>
              </div>
            ) : (
              <Link key={l.to} to={l.to} aria-current={isActive(l.match) ? "page" : undefined}>
                {l.label}
              </Link>
            ),
          )}
        </nav>
        <div className="header__actions">
          <Link to={altPath} className="header__lang" hrefLang={lang === "ar" ? "en" : "ar"} lang={lang === "ar" ? "en" : "ar"}>
            {t.langToggle}
          </Link>
          <button type="button" className="header__theme" onClick={toggleTheme} aria-label={mode === "dark" ? t.lightMode : t.darkMode} title={mode === "dark" ? t.lightMode : t.darkMode}>
            {mode === "dark" ? (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><circle cx="12" cy="12" r="4.2" /><path d="M12 2.5v2.2M12 19.3v2.2M2.5 12h2.2M19.3 12h2.2M5.3 5.3l1.6 1.6M17.1 17.1l1.6 1.6M5.3 18.7l1.6-1.6M17.1 6.9l1.6-1.6" /></svg>
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M20.5 14.2A8.5 8.5 0 0 1 9.8 3.5a8.5 8.5 0 1 0 10.7 10.7z" /></svg>
            )}
          </button>
          <Link to={lp("/contact")} className="btn btn--sm header__cta">
            {t.cta}
          </Link>
          <button
            className="header__burger"
            aria-label={open ? t.close : t.menu}
            aria-expanded={open}
            aria-controls="menu-sheet"
            onClick={() => setOpen((v) => !v)}
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round">
              {open ? <path d="M4 4l12 12M16 4L4 16" /> : <path d="M3 6h14M3 14h14" />}
            </svg>
          </button>
        </div>
      </div>
      {open && (
        <div id="menu-sheet" className="menu-sheet" role="dialog" aria-modal="true" aria-label={t.menu}>
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} className="menu-link">
              {l.label}
            </NavLink>
          ))}
          {present.length > 1 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: "8px 16px", padding: "4px 0 8px" }}>
              {present.map((x) => (
                <Link key={x} to={`${lp("/projects")}?type=${x}`} style={{ color: "var(--muted)", fontSize: 16 }}>{t.types[x]}</Link>
              ))}
            </div>
          )}
          <div className="menu-foot">
            <Link to={lp("/contact")} className="btn">
              {t.cta}
            </Link>
            <Link to={altPath} className="menu-lang" lang={lang === "ar" ? "en" : "ar"}>
              {t.langToggle}
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
