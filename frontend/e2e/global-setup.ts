import { request, type FullConfig } from "@playwright/test";

export const ADMIN = { email: "e2e-admin@example.com", password: "E2e-admin-pass-2026" };

/** Text-only sample data (no images): the site must look finished without photography. */
export default async function globalSetup(config: FullConfig) {
  const baseURL = config.projects[0].use.baseURL!;
  const api = await request.newContext({ baseURL });
  const login = await api.post("/api/admin/login", { data: ADMIN });
  const { token } = await login.json();
  // One login for the whole run (the login rate limit is real); tests reuse it via adminToken()/signIn().
  process.env.E2E_ADMIN_TOKEN = token;
  const headers = { Authorization: `Bearer ${token}` };
  const existing = await (await api.get("/api/admin/projects", { headers })).json();
  if (existing.length) return;
  const make = (data: object) => api.post("/api/admin/projects", { headers, data: { country: "eg", published: true, ...data } });
  // The approval gate (ENFORCE_APPROVALS, on by default) hides anything without a recorded permission.
  const approve = async (res: Awaited<ReturnType<typeof make>>) => {
    const { id } = await res.json();
    const r = await api.post("/api/admin/approvals", {
      headers,
      multipart: { subject_type: "project", subject_id: String(id), approval_type: "client_permission_to_publish", status: "approved", approved_by_name: "Test Approver", evidence_note: "e2e fixture (fake data)" },
    });
    if (!r.ok()) throw new Error(`approval fixture failed: ${r.status()} ${await r.text()}`);
  };
  await approve(await make({ title_en: "E2E Office Fit-out", title_ar: "مكتب اختبار", type: "office", city_en: "New Cairo", year: 2025, tagline_en: "Open-plan offices.", summary_en: "Offices for a test client.", scope_en: "Interior fit-out", sort_order: 1 }));
  await approve(await make({ title_en: "E2E Coastal Restaurant", type: "hospitality", city_en: "Hurghada", year: 2024, summary_en: "A restaurant by the sea.", sort_order: 2 }));
  await approve(await make({ title_en: "E2E Family Villa", type: "residential", city_en: "Sheikh Zayed", country: "eg", sort_order: 3 }));
  await make({ title_en: "E2E Hidden Draft", type: "retail", published: false, sort_order: 4 });
  await make({ title_en: "E2E Test Sample", slug: "test-project-e2e", type: "retail", sort_order: 5 });
  await api.put("/api/admin/offices/eg", {
    headers,
    data: { address_en: "14 Abdel Qawy Ahmed St.\nMohandessin, Giza, Egypt", address_ar: "١٤ شارع عبد القوي أحمد", phone: "+20 10 06602371", whatsapp: "+20 10 06602371", email: "info@redecorgroup.com", hours_en: "", hours_ar: "", maps_url: "" },
  });
  await api.put("/api/admin/offices/qa", {
    headers,
    data: { address_en: "[Street, zone]", address_ar: "", phone: "+20 10 06602371", whatsapp: "+20 10 06602371", email: "info@redecorgroup.com", hours_en: "[Days · Hours]", hours_ar: "", maps_url: "" },
  });
  await api.dispose();
}
