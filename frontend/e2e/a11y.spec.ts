import { expect, test } from "@playwright/test";
import { ADMIN } from "./global-setup";

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
  const { token } = await (await request.post("/api/admin/login", { data: ADMIN })).json();
  const headers = { Authorization: `Bearer ${token}` };
  const project = await (await request.post("/api/admin/projects", { headers, data: { title_en: "E2E Lightbox Fixture", country: "eg", type: "office", published: true } })).json();
  const png = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAEAAAAAwCAIAAAAuKetIAAAAUUlEQVR4nO3PQQ0AIBDAMEDm+ReCCB4Nyapg2zOzfnZ0wKsGtAa0BrQGtAa0BrQGtAa0BrQGtAa0BrQGtAa0BrQGtAa0BrQGtAa0BrQGtAa0CxhXAW7GSF1HAAAAAElFTkSuQmCC",
    "base64",
  );
  const files = [1, 2].map((n) => ({ name: `fixture-${n}.png`, mimeType: "image/png", buffer: png }));
  for (const f of files) {
    const up = await request.post(`/api/admin/projects/${project.id}/images`, { headers, multipart: { files: f } });
    expect(up.status(), await up.text()).toBe(201);
  }
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
