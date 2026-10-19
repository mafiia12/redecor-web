import { expect, test } from "@playwright/test";

/** Measured budgets (local, no throttling): layout stability, script weight and requests on first visit. */
for (const path of ["/", "/projects", "/projects/e2e-office-fit-out", "/ar"]) {
  test(`performance budget: ${path}`, async ({ page }) => {
    const scripts: number[] = [];
    page.on("response", async (r) => {
      if (r.request().resourceType() === "script") scripts.push((await r.request().sizes()).responseBodySize);
    });
    await page.addInitScript(() => {
      (window as unknown as { __cls: number }).__cls = 0;
      new PerformanceObserver((list) => {
        for (const e of list.getEntries() as (PerformanceEntry & { value: number; hadRecentInput: boolean })[]) {
          if (!e.hadRecentInput) (window as unknown as { __cls: number }).__cls += e.value;
        }
      }).observe({ type: "layout-shift", buffered: true });
    });
    await page.goto(path, { waitUntil: "networkidle" });
    await page.waitForTimeout(500);
    const m = await page.evaluate(() => {
      const nav = performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming;
      const fcp = performance.getEntriesByName("first-contentful-paint")[0]?.startTime ?? 0;
      return { cls: (window as unknown as { __cls: number }).__cls, fcp, domContentLoaded: nav.domContentLoadedEventEnd };
    });
    const js = scripts.reduce((a, b) => a + b, 0);
    console.log(`PERF ${path} CLS=${m.cls.toFixed(3)} FCP=${Math.round(m.fcp)}ms DCL=${Math.round(m.domContentLoaded)}ms JS=${Math.round(js / 1024)}kB transferred`);
    expect(m.cls).toBeLessThan(0.1);
    expect(js).toBeLessThan(120 * 1024); // compressed JavaScript on first visit
  });
}
