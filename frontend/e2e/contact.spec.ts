import { expect, test } from "@playwright/test";

test.describe("enquiry form", () => {
  test("validation is accessible and keyboard friendly", async ({ page }) => {
    await page.goto("/contact");
    await page.getByRole("button", { name: "Send enquiry" }).click();
    await expect(page.getByRole("alert")).toBeVisible();
    await expect(page.locator("#f-name")).toBeFocused();
    await expect(page.locator("#f-name")).toHaveAttribute("aria-invalid", "true");
    await expect(page.locator("#f-name")).toHaveAttribute("aria-describedby", "err-name");
  });

  test("successful submission (once), stored with notification status", async ({ page, request }) => {
    await page.goto("/contact");
    await page.locator("#f-name").fill("E2E Visitor");
    await page.locator("#f-phone").fill("100 123 4567");
    await page.locator("#f-country").selectOption("eg");
    await page.locator("#f-service").selectOption("fitout");
    await page.locator("#f-message").fill("Fit-out for a 200 m² apartment");
    await page.locator('input[name="consent"]').check();
    await page.waitForTimeout(2800); // a person takes longer than the bot threshold
    await page.getByRole("button", { name: "Send enquiry" }).click();
    await expect(page.getByRole("status")).toContainText("Thank you");
    const login = await (await request.post("/api/admin/login", { data: { email: "e2e-admin@example.com", password: "E2e-admin-pass-2026" } })).json();
    const list = await (await request.get("/api/admin/enquiries", { headers: { Authorization: `Bearer ${login.token}` } })).json();
    const mine = list.filter((e: { name: string }) => e.name === "E2E Visitor");
    expect(mine).toHaveLength(1);
    expect(mine[0].notify_status).toBe("not_configured"); // no SMTP in tests: stored, flagged, never lost
  });
});
