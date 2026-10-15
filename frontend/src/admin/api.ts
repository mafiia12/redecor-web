import { useCallback, useEffect, useState } from "react";
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
  caption_en: string;
  caption_ar: string;
  sort_order: number;
  image: Img;
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
  is_render: boolean;
  featured: boolean;
  published: boolean;
  sort_order: number;
  cover: Img | null;
  images: AdminImage[];
}
export interface AdminClient {
  id: number;
  name: string;
  url: string;
  published: boolean;
  sort_order: number;
  logo: Img | null;
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
}
