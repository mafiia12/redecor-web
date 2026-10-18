import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { cachedBootstrap, loadBootstrap, type Bootstrap, type Office } from "./api";
import { dict, type Dict, type Lang } from "../i18n";

/* ---------- language ---------- */
interface LangCtx {
  lang: Lang;
  t: Dict;
  dir: "ltr" | "rtl";
  /** Prefix an internal path with the current language. */
  lp: (path: string) => string;
  /** Same page in the other language. */
  altPath: string;
}
const LangContext = createContext<LangCtx | null>(null);

export function LangProvider({ lang, children, syncDocument = true }: { lang: Lang; children: ReactNode; syncDocument?: boolean }) {
  const { pathname, search, hash } = useLocation();
  const value = useMemo<LangCtx>(() => {
    const bare = lang === "ar" ? pathname.replace(/^\/ar(?=\/|$)/, "") || "/" : pathname;
    const other = lang === "ar" ? bare : `/ar${bare === "/" ? "" : bare}`;
    return {
      lang,
      t: dict[lang],
      dir: lang === "ar" ? "rtl" : "ltr",
      lp: (p: string) => (lang === "ar" ? (p === "/" ? "/ar" : `/ar${p}`) : p),
      altPath: other + search + hash,
    };
  }, [lang, pathname, search, hash]);

  useEffect(() => {
    if (!syncDocument) return;
    document.documentElement.lang = lang;
    document.documentElement.dir = value.dir;
  }, [lang, value.dir, syncDocument]);

  return <LangContext.Provider value={value}>{children}</LangContext.Provider>;
}

export function useLang(): LangCtx {
  const v = useContext(LangContext);
  if (!v) throw new Error("useLang outside LangProvider");
  return v;
}

/** Pick the localized field: title_ar when Arabic and filled in, else title_en. */
export function pick<T extends object>(obj: T, field: string, lang: Lang): string {
  const rec = obj as Record<string, unknown>;
  const ar = rec[`${field}_ar`];
  const en = rec[`${field}_en`];
  return String((lang === "ar" && ar ? ar : en) ?? "");
}

/* ---------- site data (one request) ---------- */
interface DataCtx {
  data: Bootstrap | null;
  error: boolean;
  reload: () => void;
  office: (c: "eg" | "qa") => Office | undefined;
}
const DataContext = createContext<DataCtx | null>(null);

export function DataProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<Bootstrap | null>(() => cachedBootstrap());
  const [error, setError] = useState(false);

  const reload = useCallback(() => {
    setError(false);
    loadBootstrap()
      .then(setData)
      .catch(() => setError(true));
  }, []);
  useEffect(reload, [reload]);

  const value = useMemo<DataCtx>(
    () => ({ data, error: error && !data, reload, office: (c) => data?.offices.find((o) => o.country === c) }),
    [data, error, reload],
  );
  return <DataContext.Provider value={value}>{children}</DataContext.Provider>;
}

export function useData(): DataCtx {
  const v = useContext(DataContext);
  if (!v) throw new Error("useData outside DataProvider");
  return v;
}

/* ---------- helpers ---------- */
export const waDigits = (n: string) => n.replace(/\D/g, "");
/** Only real-looking numbers become links (placeholders like "[+20 XXX]" do not). */
export const isRealNumber = (n: string) => !n.includes("[") && waDigits(n).length >= 8;
export const waLink = (n: string, text?: string) =>
  `https://wa.me/${waDigits(n)}${text ? `?text=${encodeURIComponent(text)}` : ""}`;

/** Localized text plus the attributes it needs: English shown inside the Arabic site is marked lang="en" dir="ltr"
 *  so it reads and aligns correctly (a controlled fallback, never a silent mix). */
export function loc<T extends object>(obj: T, field: string, lang: Lang): { text: string; attrs: { lang?: string; dir?: "ltr" } } {
  const rec = obj as Record<string, unknown>;
  const ar = String(rec[`${field}_ar`] ?? "");
  const en = String(rec[`${field}_en`] ?? "");
  if (lang === "ar" && !ar && en) return { text: en, attrs: { lang: "en", dir: "ltr" } };
  return { text: lang === "ar" ? ar : en, attrs: {} };
}

const filled = (v?: string) => !!v && !v.includes("[");

/** Offices worth showing publicly: the ones with a confirmed address. */
export function visibleOffices(offices: Office[]): Office[] {
  return offices.filter((o) => filled(o.address_en) || filled(o.address_ar));
}

/** WhatsApp destinations: one row per distinct number. Offices that share a number share one row
 *  (so a Qatar label is never shown on an Egyptian number). */
export function whatsappContacts(offices: Office[], names: Record<string, string>): { label: string; num: string }[] {
  const byNum = new Map<string, string[]>();
  for (const o of offices) {
    const num = o.whatsapp || o.phone;
    if (!isRealNumber(num)) continue;
    const key = waDigits(num);
    byNum.set(key, [...(byNum.get(key) ?? []), o.country]);
  }
  return [...byNum.entries()].map(([digits, countries]) => {
    const office = offices.find((o) => waDigits(o.whatsapp || o.phone) === digits)!;
    return { label: countries.map((c) => names[c] ?? c).join(" · "), num: office.whatsapp || office.phone };
  });
}

export function usePageMeta(title: string, description?: string) {
  useEffect(() => {
    document.title = title;
    if (description) {
      document.querySelector('meta[name="description"]')?.setAttribute("content", description);
    }
  }, [title, description]);
}
