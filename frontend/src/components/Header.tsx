import { useEffect, useRef, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { useLang } from "../lib/context";

export function Header() {
  const { t, lp, altPath, lang } = useLang();
  const { pathname } = useLocation();
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
  const theme = dark && !open ? "dark" : "light";

  return (
    <header ref={ref} className="header" data-theme={theme} data-hidden={hidden && !open}>
      <div className="header__inner">
        <Link to={lp("/")} className="header__logo" aria-label={`${t.brand}, ${lang === "ar" ? "الرئيسية" : "home"}`}>
          <img src={theme === "dark" ? "/logo-light.svg" : "/logo-ink.svg"} alt={t.brand} width={48} height={28} />
        </Link>
        <nav className="header__nav" aria-label="Main">
          {links.map((l) => (
            <Link key={l.to} to={l.to} aria-current={isActive(l.match) ? "page" : undefined}>
              {l.label}
            </Link>
          ))}
        </nav>
        <div className="header__actions">
          <Link to={altPath} className="header__lang" hrefLang={lang === "ar" ? "en" : "ar"} lang={lang === "ar" ? "en" : "ar"}>
            {t.langToggle}
          </Link>
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
