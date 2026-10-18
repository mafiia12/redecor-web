// Starts the FastAPI backend on a fresh temporary database for the end-to-end tests.
import { spawn } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const port = process.argv[2] ?? "8130";
const dir = mkdtempSync(join(tmpdir(), "redecor-e2e-"));
const backend = resolve(import.meta.dirname, "../../backend");
const python = process.env.PYTHON ?? (process.platform === "win32" ? "python" : "python3");
const env = {
  ...process.env,
  APP_ENV: "development",
  DATABASE_URL: `sqlite:///${join(dir, "e2e.db")}`,
  UPLOAD_DIR: join(dir, "uploads"),
  ATTACHMENTS_DIR: join(dir, "attachments"),
  FRONTEND_DIST: resolve(import.meta.dirname, "../dist"),
  SECRET_KEY: "e2e-secret-key-e2e-secret-key-e2e-secret-key",
  ADMIN_EMAIL: "e2e-admin@example.com",
  ADMIN_PASSWORD: "E2e-admin-pass-2026",
  SITE_URL: `http://127.0.0.1:${port}`,
  SEED_DEMO: "0",
  NOTIFY_RETRY_SECONDS: "0",
};
const child = spawn(python, ["-m", "uvicorn", "app.main:app", "--port", port, "--host", "127.0.0.1"], { cwd: backend, env, stdio: "inherit" });
const stop = () => child.kill();
process.on("SIGTERM", stop);
process.on("SIGINT", stop);
child.on("exit", (code) => process.exit(code ?? 0));
