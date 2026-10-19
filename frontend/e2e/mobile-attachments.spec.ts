import { expect, test } from "@playwright/test";
import { dict } from "../src/i18n";
import { noHorizontalScroll } from "./helpers";

const ar = dict.ar.form;

test("Arabic quote form on a phone: attach a file and send", async ({ page }) => {
  await page.goto("/ar/contact");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.getByText(ar.files.label)).toBeVisible();
  await page.locator('input[name="files"]').setInputFiles({ name: "boq.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4\n%%EOF\n") });
  await expect(page.getByRole("button", { name: ar.files.remove("boq.pdf") })).toBeVisible();
  const box = await page.getByRole("button", { name: ar.files.remove("boq.pdf") }).boundingBox();
  expect(box!.width).toBeGreaterThanOrEqual(44); // touch target
  await noHorizontalScroll(page);
  await page.locator('input[name="files"]').setInputFiles({ name: "macro.xlsm", mimeType: "application/octet-stream", buffer: Buffer.from("PK") });
  await expect(page.locator("#f-files-err")).toHaveText(ar.files.type("macro.xlsm"));

  await page.locator("#f-name").fill("E2E Arabic Mobile");
  await page.locator("#f-phone").fill("100 111 2222");
  await page.locator("#f-country").selectOption("eg");
  await page.locator("#f-service").selectOption("supply");
  await page.locator('input[name="consent"]').check();
  await page.waitForTimeout(2800);
  await page.getByRole("button", { name: ar.send }).click();
  await expect(page.getByRole("status")).toContainText(ar.okTitle);
});
