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
