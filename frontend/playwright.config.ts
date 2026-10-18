import { defineConfig, devices } from "@playwright/test";
import { existsSync } from "node:fs";

// End-to-end tests run against the real backend serving the built site (npm run build first).
// The server uses a throw-away database (see e2e/server.mjs), never your real data.
const PORT = Number(process.env.E2E_PORT ?? 8130);
const chromium = process.env.PW_CHROMIUM ?? "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const launchOptions = existsSync(chromium) ? { executablePath: chromium, args: ["--no-sandbox"] } : {};

export default defineConfig({
  testDir: "e2e",
  timeout: 30_000,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: { baseURL: `http://127.0.0.1:${PORT}`, launchOptions, trace: "retain-on-failure" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 }, launchOptions }, testIgnore: /mobile/ },
    { name: "tablet", use: { viewport: { width: 820, height: 1180 }, hasTouch: true, launchOptions }, testMatch: /responsive/ },
    { name: "mobile", use: { ...devices["Pixel 7"], launchOptions }, testMatch: /responsive|mobile/ },
  ],
  webServer: {
    command: `node e2e/server.mjs ${PORT}`,
    url: `http://127.0.0.1:${PORT}/api/health`,
    reuseExistingServer: false,
    timeout: 60_000,
  },
  globalSetup: "./e2e/global-setup.ts",
});
