import { expect, test, type Page } from "@playwright/test";
import { ADMIN } from "./global-setup";

async function login(page: Page) {
  await page.goto("/admin/login");
  await page.getByLabel("Email").fill(ADMIN.email);
  await page.getByLabel("Password").fill(ADMIN.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Projects" })).toBeVisible();
}

/** A generated test image (flat colour, no real photography): a screenshot of a coloured page. */
async function testImage(page: Page, w: number, h: number, color: string) {
  const ctx = await page.context().browser()!.newContext({ viewport: { width: w, height: h } });
  const p = await ctx.newPage();
  await p.setContent(`<body style="margin:0;background:${color}"></body>`);
  const buffer = await p.screenshot({ type: "png" });
  await ctx.close();
  return buffer;
}

test.describe.configure({ mode: "serial" });

test("bulk photos: dry run saves nothing, confirm adds them, focal point reaches the public card", async ({ page }) => {
  await login(page);
  const slug = "e2e-family-villa";
  const before = await (await page.request.get(`/api/projects/${slug}`)).json();
  expect(before.gallery).toHaveLength(0);

  await page.goto("/admin/bulk-images");
  await page.getByLabel("Photos or .zip").setInputFiles([
    { name: `${slug}__01__executed__cover.png`, mimeType: "image/png", buffer: await testImage(page, 2600, 1700, "#7a5c3e") },
    { name: `${slug}__02__render.png`, mimeType: "image/png", buffer: await testImage(page, 1800, 1200, "#3e5c7a") },
    { name: "random-name.png", mimeType: "image/png", buffer: await testImage(page, 1800, 1200, "#5c7a3e") },
  ]);
  await page.getByRole("button", { name: "1. Dry run" }).click();
  await expect(page.getByRole("heading", { name: "Dry run: nothing has been saved" })).toBeVisible();
  await expect(page.getByText("name does not follow")).toBeVisible();
  expect((await (await page.request.get(`/api/projects/${slug}`)).json()).gallery).toHaveLength(0);

  await page.getByRole("button", { name: "2. Confirm: add 2 photo(s)" }).click();
  await expect(page.getByText("Added 2 photo(s).")).toBeVisible();
  const after = await (await page.request.get(`/api/projects/${slug}`)).json();
  expect(after.gallery.map((g: { kind: string }) => g.kind)).toEqual(["executed", "render"]);

  // Focal point: click near the top-left of the cover in the project editor.
  await page.goto(`/admin/projects/${after.id}`);
  const focal = page.locator(".adm-focal").first();
  await expect(focal.locator("img")).toBeVisible();
  await expect.poll(async () => (await focal.boundingBox())?.height ?? 0).toBeGreaterThan(20);
  const box = (await focal.boundingBox())!;
  await focal.click({ position: { x: box.width * 0.2, y: box.height * 0.3 } });
  await expect(page.locator(".adm-focal__hint").first()).toContainText("20% / 30%");
  await expect.poll(async () => (await (await page.request.get(`/api/projects/${slug}`)).json()).cover.fx).toBe(0.2);
  await page.goto(`/projects/${slug}`);
  await expect(page.locator(".case img").first()).toHaveAttribute("style", /object-position: 20% 30%/);
});

test("approval gate: a published project appears only after its permission is recorded", async ({ page }) => {
  await login(page);
  await page.getByRole("link", { name: "New project" }).click();
  await page.getByLabel("Title (English) *").fill("E2E Gate Project");
  await page.getByRole("button", { name: "Create project" }).click();
  await page.getByLabel("Published").check();
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByText("Saved.")).toBeVisible();
  const url = "/projects/e2e-gate-project";
  expect((await page.request.get(url)).status()).toBe(404);
  await expect(page.getByText(/Not visible publicly because:.*permission/i)).toBeVisible();

  await page.getByRole("button", { name: "Record approval status" }).click();
  await page.getByLabel("Given by (name) *").fill("Test Approver");
  await page.getByLabel(/How it was given/).fill("e-mail (test)");
  await page.getByRole("button", { name: "Save record" }).click();
  await expect(page.locator(".adm-approvals .adm-tag.ok").first()).toBeVisible();
  expect((await page.request.get(url)).status()).toBe(200);
});

test("import: CSV dry run lists problems, confirm creates drafts only", async ({ page }) => {
  await login(page);
  await page.goto("/admin/import");
  const csv = "slug,title_en,country,type\ntest-project-import-1,Test Project Import 1,eg,office\n,,xx,castle\n";
  await page.getByLabel("File (.xlsx, .csv or .json)").setInputFiles({ name: "projects.csv", mimeType: "text/csv", buffer: Buffer.from("﻿" + csv) });
  await page.getByRole("button", { name: "1. Dry run" }).click();
  await expect(page.getByRole("heading", { name: "Dry run: nothing has been saved" })).toBeVisible();
  await expect(page.getByText(/country: Input should be/)).toBeVisible();
  await page.getByRole("button", { name: "2. Confirm: create 1, update 0" }).click();
  await expect(page.getByText(/Created 1, updated 0/)).toBeVisible();
  // reuse the signed-in session (another login could hit the login rate limit)
  const token = await page.evaluate(() => sessionStorage.getItem("redecor:admin-token"));
  const list = await (await page.request.get("/api/admin/projects", { headers: { Authorization: `Bearer ${token}` } })).json();
  const p = list.find((x: { slug: string }) => x.slug === "test-project-import-1");
  expect(p.published).toBe(false);
});
