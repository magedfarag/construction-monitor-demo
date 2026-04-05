import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  /* Ignore the legacy monolithic spec backup */
  testIgnore: ["**/*.bak"],
  fullyParallel: false,
  /* Single worker — WebGL map rendering saturates GPU with parallel instances */
  workers: 1,
  /*
   * CesiumJS WebGL globe causes slow browser-context teardown in headless
   * Chromium due to GPU ReadPixels stalls.  120s accommodates both the test
   * assertion phase (~30s) and the teardown phase (~90s worst case).
   */
  timeout: 120_000,
  expect: { timeout: 10_000 },
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  /* Reporter: rich HTML report in CI, list for local dev */
  reporter: process.env.CI
    ? [["html", { open: "never" }], ["list"]]
    : "list",
  use: {
    baseURL: "http://localhost:5173",
    headless: true,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    video: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npx vite --port 5173",
    url: "http://localhost:5173",
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
});