import { expect, test } from "@playwright/test";
import { oneH1, watchErrors } from "./helpers";

test.describe("public site", () => {
  test("home: identity, sections, no errors", async ({ page }) => {
    const done = watchErrors(page);
    await page.goto("/");
    await expect(page).toHaveTitle(/RE DECOR & MORE/);
    await oneH1(page);
    await expect(page.locator("h1")).toContainText("Spaces, finished");
    await expect(page.locator(".svc__row")).toHaveCount(4);
    await expect(page.locator(".tile--type").first()).toBeVisible(); // text-only projects render as typographic tiles
    await expect(page.locator(".photo__empty")).toHaveCount(0); // never grey placeholder boxes
    await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
    done();
  });

  test("publication rules: drafts and test projects are never listed", async ({ page }) => {
    await page.goto("/projects");
    await expect(page.getByText("E2E Office Fit-out")).toBeVisible();
    await expect(page.getByText("E2E Family Villa")).toBeVisible();
    await expect(page.getByText("E2E Hidden Draft")).toHaveCount(0);
    await expect(page.getByText("E2E Test Sample")).toHaveCount(0);
    const r = await page.goto("/projects/test-project-e2e");
    expect(r?.status()).toBe(404);
  });

  test("projects: filter and search", async ({ page }) => {
    await page.goto("/projects");
    await page.getByRole("group", { name: "Project type" }).getByRole("button", { name: "Hospitality" }).click();
    await expect(page.locator(".tile")).toHaveCount(1);
    await expect(page).toHaveURL(/type=hospitality/);
    await page.goto("/projects");
    const search = page.getByPlaceholder("Name, city or type");
    if (await search.count()) {
      await search.fill("villa");
      await expect(page.locator(".tile")).toHaveCount(1);
    }
  });

  test("project page: facts, server-side head, prev/next, contextual CTA", async ({ page, request }) => {
    const html = await (await request.get("/projects/e2e-office-fit-out")).text();
    expect(html).toContain("<title>E2E Office Fit-out | RE DECOR &amp; MORE</title>");
    expect(html).toContain('rel="canonical"');
    await page.goto("/projects/e2e-office-fit-out");
    await oneH1(page);
    await expect(page.locator(".case__facts")).toContainText("New Cairo");
    await expect(page.locator(".case__pn-link--next")).toContainText("E2E Coastal Restaurant");
    await page.getByRole("link", { name: "Ask about this project" }).click();
    await expect(page).toHaveURL(/\/contact\?about=/);
    await expect(page.locator("#f-message")).toHaveValue(/About: E2E Office Fit-out/);
  });

  test("services: page and related work", async ({ page }) => {
    await page.goto("/services/fitout");
    await oneH1(page);
    await expect(page.locator("#related .tile").first()).toBeVisible();
  });

  test("unknown page returns 404 with a helpful page", async ({ page }) => {
    const r = await page.goto("/this-does-not-exist");
    expect(r?.status()).toBe(404);
    await expect(page.getByRole("link", { name: /home/i }).first()).toBeVisible();
  });

  test("language switch to Arabic and back", async ({ page }) => {
    await page.goto("/about");
    await page.getByRole("link", { name: "عربي" }).first().click();
    await expect(page).toHaveURL(/\/ar\/about/);
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    await expect(page.locator("html")).toHaveAttribute("lang", "ar");
    // unverified figure ("3 regional bases") is not shown
    await expect(page.locator(".stats > div")).toHaveCount(2);
    await page.getByRole("link", { name: "English" }).first().click();
    await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
  });

  test("theme toggle persists", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    await page.getByRole("button", { name: "Switch to light mode" }).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  });

  test("offices: placeholder Qatar office is hidden, no Qatar label on the Egyptian number", async ({ page }) => {
    // capture the WhatsApp link instead of leaving the site
    await page.addInitScript(() => {
      (window as unknown as { __opened: string[] }).__opened = [];
      window.open = ((u: string) => ((window as unknown as { __opened: string[] }).__opened.push(u), null)) as typeof window.open;
    });
    await page.goto("/projects/e2e-family-villa");
    await page.locator(".wa__fab").click();
    // Egypt and Qatar share one number, so there is one destination and no "Qatar" label on an Egyptian number
    const opened = await page.evaluate(() => (window as unknown as { __opened: string[] }).__opened);
    expect(opened).toHaveLength(1);
    expect(opened[0]).toMatch(/^https:\/\/wa\.me\/201006602371\?text=/);
    expect(decodeURIComponent(opened[0])).toContain("E2E Family Villa"); // context-aware message
    await page.goto("/contact");
    await expect(page.locator(".office")).toHaveCount(1);
    await expect(page.locator(".office")).not.toContainText("[");
  });
});
