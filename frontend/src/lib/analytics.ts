/** Privacy-friendly first-party analytics: anonymous counters (event + page + language), no cookies,
 *  no identifiers, no third parties. Disabled when the visitor's browser sends "Do Not Track" / GPC. */

export type EventName =
  | "page_view"
  | "project_view"
  | "service_view"
  | "cta_click"
  | "whatsapp_open"
  | "whatsapp_click"
  | "enquiry_submit"
  | "enquiry_success"
  | "profile_download"
  | "language_switch"
  | "theme_switch";

const optedOut = () => {
  const n = navigator as Navigator & { globalPrivacyControl?: boolean };
  return n.doNotTrack === "1" || n.globalPrivacyControl === true || location.pathname.startsWith("/admin");
};

export function track(name: EventName, path: string = location.pathname) {
  try {
    if (optedOut()) return;
    const lang = document.documentElement.lang === "ar" ? "ar" : "en";
    const body = JSON.stringify({ name, path: path.split("?")[0], lang });
    const blob = new Blob([body], { type: "application/json" });
    if (!navigator.sendBeacon?.("/api/events", blob)) {
      fetch("/api/events", { method: "POST", body, headers: { "Content-Type": "application/json" }, keepalive: true }).catch(() => undefined);
    }
  } catch {
    /* analytics must never break the page */
  }
}
