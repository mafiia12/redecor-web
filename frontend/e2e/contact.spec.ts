import { expect, test } from "@playwright/test";
import { adminHeaders, signIn } from "./helpers";

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
    const list = await (await request.get("/api/admin/enquiries", { headers: adminHeaders() })).json();
    const mine = list.filter((e: { name: string }) => e.name === "E2E Visitor");
    expect(mine).toHaveLength(1);
    expect(mine[0].notify_status).toBe("not_configured"); // no SMTP in tests: stored, flagged, never lost
  });
});

test.describe("quote form attachments", () => {
  const PDF = Buffer.from("%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n");

  test("attach, remove, refuse a bad file, send; admin downloads it", async ({ page, request }) => {
    await page.goto("/contact");
    const input = page.locator('input[name="files"]');
    await input.setInputFiles([
      { name: "plan.pdf", mimeType: "application/pdf", buffer: PDF },
      { name: "extra.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4 other") },
    ]);
    await expect(page.locator(".file-list li")).toHaveCount(2);
    await page.getByRole("button", { name: "Remove extra.pdf" }).click();
    await expect(page.locator(".file-list li")).toHaveCount(1);
    await input.setInputFiles({ name: "setup.exe", mimeType: "application/octet-stream", buffer: Buffer.from("MZ") });
    await expect(page.locator("#f-files-err")).toContainText("setup.exe can’t be sent");
    await expect(page.locator(".file-list li")).toHaveCount(1);

    await page.locator("#f-name").fill("E2E Attachment");
    await page.locator("#f-phone").fill("100 765 4321");
    await page.locator("#f-country").selectOption("eg");
    await page.locator("#f-service").selectOption("fitout");
    await page.locator('input[name="consent"]').check();
    await page.waitForTimeout(2800);
    await page.getByRole("button", { name: "Send enquiry" }).click();
    await expect(page.getByRole("status")).toContainText("Thank you");

    const headers = adminHeaders();
    const list = await (await request.get("/api/admin/enquiries?status=", { headers })).json();
    const mine = list.find((e: { name: string }) => e.name === "E2E Attachment");
    expect(mine.attachment_count).toBe(1);
    const detail = await (await request.get(`/api/admin/enquiries/${mine.id}`, { headers })).json();
    expect(detail.attachments[0].scan_status).toBe("quarantine"); // scanner off: flagged, still delivered to the admin
    const dl = await request.get(`/api/admin/enquiries/${mine.id}/attachments/${detail.attachments[0].id}`, { headers });
    expect(dl.status()).toBe(200);
    expect(dl.headers()["content-disposition"]).toContain("attachment");
    expect(dl.headers()["x-content-type-options"]).toBe("nosniff");
    expect(Buffer.from(await dl.body()).equals(PDF)).toBe(true);
  });

  test("admin sees the file and its warning in the enquiries page", async ({ page }) => {
    await signIn(page, "/admin/enquiries");
    const card = page.locator("article", { hasText: "E2E Attachment" });
    await expect(card.getByText("1 file")).toBeVisible();
    await card.getByRole("button", { name: "Open" }).click();
    await expect(card.getByText("plan.pdf")).toBeVisible();
    await expect(card.getByText(/Not scanned/)).toBeVisible();
    const download = page.waitForEvent("download");
    await card.getByRole("button", { name: "Download" }).click();
    expect((await download).suggestedFilename()).toBe("plan.pdf");
    // CRM: move it on and leave a note; the history records it
    await card.getByLabel("Change status").selectOption("contacted");
    await card.getByLabel(/Internal note/).fill("Called the client (test)");
    await card.getByRole("button", { name: "Save" }).click();
    await expect(card.getByText("Status New → Contacted")).toBeVisible();
    await expect(card.getByText("Called the client (test)")).toBeVisible();
  });
});
