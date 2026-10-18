import { expect, test } from "@playwright/test";
import { ADMIN } from "./global-setup";

test.describe("admin", () => {
  test("wrong password is refused", async ({ page }) => {
    await page.goto("/admin/login");
    await page.getByLabel("Email").fill(ADMIN.email);
    await page.getByLabel("Password").fill("wrong-password-123");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByRole("alert")).toContainText("Incorrect");
  });

  test("draft → preview → publish → held by the approval gate", async ({ page }) => {
    await page.goto("/admin/login");
    await page.getByLabel("Email").fill(ADMIN.email);
    await page.getByLabel("Password").fill(ADMIN.password);
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByRole("heading", { name: "Projects" })).toBeVisible();
    await page.getByRole("link", { name: "New project" }).click();
    await page.getByLabel("Title (English) *").fill("E2E Published From Admin");
    await page.getByRole("button", { name: "Create project" }).click();
    await expect(page.getByText("Draft: only visible here and in Preview.")).toBeVisible();
    const slugUrl = "/projects/e2e-published-from-admin";
    expect((await page.request.get(slugUrl)).status()).toBe(404);
    await page.getByRole("link", { name: "Preview" }).click();
    await expect(page.locator(".case__title")).toHaveText("E2E Published From Admin");
    await page.getByRole("link", { name: "Back to editing" }).click();
    await page.getByLabel("Published").check();
    await page.getByRole("button", { name: "Save changes" }).click();
    await expect(page.getByText("Saved.")).toBeVisible();
    // Published but no client permission on record yet: the approval gate keeps it off the site
    // (recording the approval is covered in content.spec.ts).
    expect((await page.request.get(slugUrl)).status()).toBe(404);
    await expect(page.getByText(/Not visible publicly because/)).toBeVisible();
  });
});
