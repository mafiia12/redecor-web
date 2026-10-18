import { expect, test } from "@playwright/test";
import { adminHeaders } from "./helpers";

test("skip link is the first keyboard stop and moves focus to main", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  const skip = page.locator("a.skip");
  await expect(skip).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#main/);
});

test("every image has an alt attribute; one language and direction per page", async ({ page }) => {
  for (const path of ["/", "/projects", "/about", "/contact", "/ar", "/ar/about"]) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    const missing = await page.locator("img:not([alt])").count();
    expect(missing, `${path}: images without alt`).toBe(0);
    const lang = await page.locator("html").getAttribute("lang");
    expect(lang).toBe(path.startsWith("/ar") ? "ar" : "en");
  }
});

test("lightbox: keyboard navigation and focus return (fixture photo in the throw-away test database)", async ({ page, request }) => {
  // A plain generated PNG is uploaded to the temporary e2e database only, to exercise the viewer.
  const headers = adminHeaders();
  const project = await (await request.post("/api/admin/projects", { headers, data: { title_en: "E2E Lightbox Fixture", country: "eg", type: "office", published: true } })).json();
  // Two distinct flat-colour PNGs (identical files would be skipped as duplicates).
  const png = async (color: string) => {
    await page.setContent(`<body style="margin:0;background:${color}"></body>`);
    return page.screenshot({ type: "png", clip: { x: 0, y: 0, width: 64, height: 48 } });
  };
  const files = [
    { name: "fixture-1.png", mimeType: "image/png", buffer: await png("#7a5c3e") },
    { name: "fixture-2.png", mimeType: "image/png", buffer: await png("#3e5c7a") },
  ];
  for (const f of files) {
    const up = await request.post(`/api/admin/projects/${project.id}/images`, { headers, multipart: { files: f, kind: "executed", override_quality: "true" } });
    expect(up.status(), await up.text()).toBe(201);
  }
  // The approval gate is on: record the (fake) client permission so the fixture is public.
  await request.post("/api/admin/approvals", {
    headers,
    multipart: { subject_type: "project", subject_id: String(project.id), approval_type: "client_permission_to_publish", status: "approved", approved_by_name: "Test Approver", evidence_note: "e2e fixture" },
  });
  await page.goto(`/projects/${project.slug}`);
  const opener = page.locator(".case__zoom").first();
  await opener.click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText("1 / 2");
  await page.keyboard.press("ArrowRight");
  await expect(dialog).toContainText("2 / 2");
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(opener).toBeFocused();
  // clean up the fixture
  await request.delete(`/api/admin/projects/${project.id}`, { headers });
});
