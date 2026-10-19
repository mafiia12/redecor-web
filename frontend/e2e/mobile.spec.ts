import { expect, test } from "@playwright/test";

test("mobile menu opens, navigates and closes with Escape", async ({ page }) => {
  await page.goto("/");
  const burger = page.getByRole("button", { name: "Menu" });
  await burger.click();
  const sheet = page.getByRole("dialog", { name: "Menu" });
  await expect(sheet).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(sheet).toBeHidden();
  await burger.click();
  await sheet.getByRole("link", { name: "Projects" }).first().click();
  await expect(page).toHaveURL(/\/projects/);
  await expect(page.getByRole("dialog", { name: "Menu" })).toBeHidden();
});

test("Arabic mobile menu", async ({ page }) => {
  await page.goto("/ar");
  await page.getByRole("button", { name: "القائمة" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
});
