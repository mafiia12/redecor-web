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

export function LangProvider({ lang, children }: { lang: Lang; children: ReactNode }) {
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
    document.documentElement.lang = lang;
    document.documentElement.dir = value.dir;
  }, [lang, value.dir]);

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
export const waLink = (n: string) => `https://wa.me/${waDigits(n)}`;

export function usePageMeta(title: string, description?: string) {
  useEffect(() => {
    document.title = title;
    if (description) {
      document.querySelector('meta[name="description"]')?.setAttribute("content", description);
    }
  }, [title, description]);
}
