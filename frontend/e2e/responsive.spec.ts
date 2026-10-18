import { expect, test } from "@playwright/test";
import { noHorizontalScroll, watchErrors } from "./helpers";

const PAGES = ["/", "/projects", "/projects/e2e-office-fit-out", "/services/fitout", "/about", "/contact", "/ar", "/ar/contact", "/ar/projects"];

for (const path of PAGES) {
  test(`no horizontal scroll and no errors: ${path}`, async ({ page }) => {
    const done = watchErrors(page);
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    await noHorizontalScroll(page);
    done();
  });
}
