import { useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { useLang } from "../lib/context";
import { CtaBand } from "./CtaBand";
import { Footer } from "./Footer";
import { Header } from "./Header";
import { ScrollTop } from "./ScrollTop";
import { WhatsApp } from "./WhatsApp";

/** Scroll to top on navigation (or to the #anchor when there is one). */
function ScrollManager() {
  const { pathname, hash } = useLocation();
  useEffect(() => {
    if (hash) {
      const el = document.getElementById(hash.slice(1));
      if (el) {
        // wait one frame so lazily rendered sections exist
        requestAnimationFrame(() => el.scrollIntoView());
        return;
      }
    }
    window.scrollTo(0, 0);
  }, [pathname, hash]);
  return null;
}

export function Layout({ cta = true }: { cta?: boolean }) {
  const { t } = useLang();
  return (
    <>
      <a className="skip" href="#main">
        {t.skip}
      </a>
      <ScrollManager />
      <Header />
      <main id="main">
        <Outlet />
        {cta && <CtaBand />}
      </main>
      <Footer />
      <ScrollTop />
      <WhatsApp />
    </>
  );
}
