import { useEffect, useState } from "react";
import { useLang } from "../lib/context";

export function ScrollTop() {
  const { t } = useLang();
  const [on, setOn] = useState(false);
  useEffect(() => {
    const f = () => setOn(window.scrollY > 700);
    f();
    window.addEventListener("scroll", f, { passive: true });
    return () => window.removeEventListener("scroll", f);
  }, []);
  return (
    <button type="button" className={`totop${on ? " is-on" : ""}`} aria-label={t.home.top} tabIndex={on ? 0 : -1} onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M12 19V5M6 11l6-6 6 6" /></svg>
    </button>
  );
}
