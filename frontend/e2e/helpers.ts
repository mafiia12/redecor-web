import { expect, type Page } from "@playwright/test";

/** Fails the test on any uncaught page error or console error (ignores aborted beacons). */
export function watchErrors(page: Page) {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("console", (m) => {
    if (m.type() === "error" && !/net::ERR_ABORTED|Failed to load resource: the server responded with a status of 404/.test(m.text())) errors.push(m.text());
  });
  return () => expect(errors, errors.join("\n")).toEqual([]);
}

export async function noHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(1);
}

export async function oneH1(page: Page) {
  await expect(page.locator("h1")).toHaveCount(1);
}

/** The admin token from global-setup (one login per run, so tests never trip the login rate limit). */
export function adminToken() {
  const t = process.env.E2E_ADMIN_TOKEN;
  if (!t) throw new Error("E2E_ADMIN_TOKEN missing: global-setup did not run");
  return t;
}
export const adminHeaders = () => ({ Authorization: `Bearer ${adminToken()}` });

/** Open the admin already signed in (the sign-in form itself is tested in admin.spec.ts). */
export async function signIn(page: Page, path = "/admin/projects") {
  await page.addInitScript((t) => sessionStorage.setItem("redecor:admin-token", t), adminToken());
  await page.goto(path);
}
