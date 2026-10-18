import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { ApiError, request, type Img } from "../lib/api";

const KEY = "redecor:admin-token";
export const getToken = () => {
  try {
    return sessionStorage.getItem(KEY);
  } catch {
    return null;
  }
};
export const setToken = (t: string | null) => {
  try {
    if (t) sessionStorage.setItem(KEY, t);
    else sessionStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
};

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  try {
    return await request<T>(`/api/admin${path}`, init, getToken());
  } catch (e) {
    if (e instanceof ApiError && e.status === 401 && !path.startsWith("/login")) {
      setToken(null);
      window.location.assign("/admin/login");
    }
    throw e;
  }
}

export const json = (method: string, body: unknown): RequestInit => ({ method, body: JSON.stringify(body) });
export const form = (method: string, files: Record<string, File | File[]>): RequestInit => {
  const fd = new FormData();
  for (const [k, v] of Object.entries(files)) (Array.isArray(v) ? v : [v]).forEach((f) => fd.append(k, f));
  return { method, body: fd };
};

/** multipart body with plain fields and files */
export const multipart = (method: string, fields: Record<string, string | boolean | number>, files: Record<string, File | File[] | null | undefined> = {}): RequestInit => {
  const fd = new FormData();
  for (const [k, v] of Object.entries(fields)) fd.append(k, String(v));
  for (const [k, v] of Object.entries(files)) if (v) (Array.isArray(v) ? v : [v]).forEach((f) => fd.append(k, f));
  return { method, body: fd };
};

/** Download an admin-only file (export, attachment) with the session token, then save it. */
export async function downloadFile(path: string, fallbackName: string) {
  const res = await fetch(`/api/admin${path}`, { headers: { Authorization: `Bearer ${getToken() ?? ""}` } });
  if (!res.ok) throw new ApiError(res.status, (await res.json().catch(() => ({}))).detail ?? res.statusText);
  const cd = res.headers.get("content-disposition") ?? "";
  const m = cd.match(/filename\*=UTF-8''([^;]+)/i) ?? cd.match(/filename="?([^";]+)"?/i);
  const name = m ? decodeURIComponent(m[1]) : fallbackName;
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

export function errorText(e: unknown): string {
  if (e instanceof ApiError) {
    if (Array.isArray(e.detail)) return e.detail.map((d: { loc?: string[]; msg?: string }) => `${d.loc?.slice(1).join(".")}: ${d.msg}`).join("; ");
    return String(e.detail);
  }
  return "Network error";
}

export function useLoad<T>(path: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const reload = useCallback(() => {
    api<T>(path).then(setData).catch((e) => setError(errorText(e)));
  }, [path]);
  useEffect(reload, [reload]);
  return { data, error, reload, setData };
}

export interface AdminImage {
  id: number;
  is_cover: boolean;
  is_render: boolean;
  full_bleed: boolean;
  layout: "full" | "half";
  caption_en: string;
  caption_ar: string;
  sort_order: number;
  image: Img;
  kind: "render" | "executed" | null;
  alt_en: string;
  alt_ar: string;
  focal_x: number | null;
  focal_y: number | null;
  quality_warnings: string;
  quality_override_by: string;
}
export interface AdminProject {
  id: number;
  slug: string;
  title_en: string;
  title_ar: string;
  summary_en: string;
  summary_ar: string;
  city_en: string;
  city_ar: string;
  country: "eg" | "qa" | "sa";
  type: "residential" | "hospitality" | "retail" | "office" | "industrial" | "healthcare" | "public" | "education" | "landscape";
  year: number | null;
  area_m2: number | null;
  scope_en: string;
  scope_ar: string;
  tagline_en: string;
  tagline_ar: string;
  story_en: string;
  story_ar: string;
  details_en: string;
  details_ar: string;
  client_name: string;
  logo: Img | null;
  is_render: boolean;
  featured: boolean;
  published: boolean;
  sort_order: number;
  cover: Img | null;
  images: AdminImage[];
  completeness: number;
  missing: string[];
  is_public: boolean;
  block_reasons: string[];
  images_without_kind: number;
}
export interface AdminClient {
  id: number;
  name: string;
  url: string;
  published: boolean;
  sort_order: number;
  logo: Img | null;
  approval_status: string;
  is_public: boolean;
  block_reasons: string[];
}
export interface AdminSlot {
  slot: string;
  label: string;
  alt_en: string;
  alt_ar: string;
  image: Img | null;
}
export interface AdminEnquiry {
  id: number;
  created_at: string;
  name: string;
  phone: string;
  email: string;
  country: string;
  service: string;
  project_type: string;
  area_m2: number | null;
  message: string;
  contact_method: string;
  lang: string;
  status: "new" | "contacted" | "closed";
  notify_status: string;
  notify_attempts: number;
  notify_error: string;
  notified_at: string | null;
}
export type Role = "admin" | "editor" | "viewer";
export interface Me {
  email: string;
  role: Role;
}
export interface AdminUser {
  id: number;
  email: string;
  role: Role;
  created_at: string;
}
export interface AdminTestimonial {
  id: number;
  quote_en: string;
  quote_ar: string;
  author: string;
  role_en: string;
  role_ar: string;
  company: string;
  approval_note: string;
  approved: boolean;
  published: boolean;
  sort_order: number;
}
export interface AdminDocument {
  slot: string;
  label: string;
  filename: string;
  size: number;
  published: boolean;
  url: string;
}

/** Signed-in user, available to every admin page (the server enforces the same rules). */
export const MeContext = createContext<Me>({ email: "", role: "viewer" });
export const useMe = () => useContext(MeContext);
export const can = (me: Me, need: Role) => ["viewer", "editor", "admin"].indexOf(me.role) >= ["viewer", "editor", "admin"].indexOf(need);
