import { useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { track } from "../lib/analytics";
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
  useEffect(() => track("page_view", pathname), [pathname]);
  // Primary calls to action carry data-track="cta"; one listener counts them all.
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      const el = (e.target as HTMLElement | null)?.closest?.("[data-track]");
      const kind = el?.getAttribute("data-track");
      if (kind === "cta") track("cta_click");
      else if (kind === "profile") track("profile_download");
    };
    document.addEventListener("click", onClick);
    return () => document.removeEventListener("click", onClick);
  }, []);
  return null;
}

export function Layout({ cta = true }: { cta?: boolean }) {
  const { t } = useLang();
  const { pathname } = useLocation();
  const onContact = /\/contact\/?$/.test(pathname);
  return (
    <>
      <a className="skip" href="#main">
        {t.skip}
      </a>
      <ScrollManager />
      <Header />
      <main id="main">
        <Outlet />
        {cta && !onContact && <CtaBand />}
      </main>
      <Footer />
      <ScrollTop />
      <WhatsApp />
    </>
  );
}
