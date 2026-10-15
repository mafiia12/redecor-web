export interface Img {
  src: string;
  srcset: string;
  width: number;
  height: number;
  color: string;
}
export type Country = "eg" | "qa";
export type ProjectType = "residential" | "hospitality" | "retail" | "office";

export interface ProjectCard {
  id: number;
  slug: string;
  title_en: string;
  title_ar: string;
  city_en: string;
  city_ar: string;
  country: Country;
  type: ProjectType;
  year: number | null;
  is_render: boolean;
  featured: boolean;
  cover: Img | null;
}
export interface GalleryImage {
  id: number;
  is_cover: boolean;
  is_render: boolean;
  full_bleed: boolean;
  caption_en: string;
  caption_ar: string;
  sort_order: number;
  image: Img;
}
export interface ProjectDetail extends ProjectCard {
  summary_en: string;
  summary_ar: string;
  area_m2: number | null;
  scope_en: string;
  scope_ar: string;
  gallery: GalleryImage[];
  related: ProjectCard[];
}
export interface Client {
  id: number;
  name: string;
  url: string;
  logo: Img | null;
}
export interface Office {
  country: Country;
  address_en: string;
  address_ar: string;
  phone: string;
  whatsapp: string;
  email: string;
  hours_en: string;
  hours_ar: string;
  maps_url: string;
}
export interface SiteImage {
  slot: string;
  alt_en: string;
  alt_ar: string;
  image: Img;
}
export interface Bootstrap {
  offices: Office[];
  site_images: Record<string, SiteImage>;
  clients: Client[];
  projects: ProjectCard[];
}

export class ApiError extends Error {
  constructor(public status: number, public detail: unknown) {
    super(typeof detail === "string" ? detail : `Request failed (${status})`);
  }
}

export async function request<T>(url: string, init: RequestInit = {}, token?: string | null): Promise<T> {
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(url, { ...init, headers });
  if (res.status === 204) return undefined as T;
  let data: unknown = null;
  try {
    data = await res.json();
  } catch {
    /* non-JSON body */
  }
  if (!res.ok) {
    const detail = (data as { detail?: unknown } | null)?.detail ?? res.statusText;
    throw new ApiError(res.status, detail);
  }
  return data as T;
}

const CACHE_KEY = "redecor:bootstrap:v1";

/** Last successful payload, so repeat visits paint instantly (and still revalidate). */
export function cachedBootstrap(): Bootstrap | null {
  try {
    const raw = sessionStorage.getItem(CACHE_KEY);
    return raw ? (JSON.parse(raw) as Bootstrap) : null;
  } catch {
    return null;
  }
}

let inflight: Promise<Bootstrap> | null = null;
export function loadBootstrap(): Promise<Bootstrap> {
  inflight ??= request<Bootstrap>("/api/bootstrap")
    .then((d) => {
      try {
        sessionStorage.setItem(CACHE_KEY, JSON.stringify(d));
      } catch {
        /* storage full or blocked */
      }
      return d;
    })
    .finally(() => {
      inflight = null;
    });
  return inflight;
}

export const getProject = (slug: string) => request<ProjectDetail>(`/api/projects/${encodeURIComponent(slug)}`);

export interface EnquiryPayload {
  name: string;
  phone: string;
  email: string;
  country: Country;
  service: string;
  project_type: string;
  area_m2: number | null;
  message: string;
  contact_method: string;
  lang: "en" | "ar";
  consent: boolean;
  website: string;
}
export const sendEnquiry = (p: EnquiryPayload) =>
  request<{ ok: true }>("/api/enquiries", { method: "POST", body: JSON.stringify(p) });
