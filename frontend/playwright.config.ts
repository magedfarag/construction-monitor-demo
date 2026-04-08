import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./e2e/global-setup.ts",
  /* Ignore the legacy monolithic spec backup */
  testIgnore: ["**/*.bak"],
  /* Enable parallel execution - GPU-heavy tests can opt out per-suite */
  fullyParallel: true,
  /* 
   * Moderate parallelism to balance speed with GPU resource constraints.
   * - CI: Use sharding instead of high worker count (set via --shard flag)
   * - Local: 2-4 workers based on available CPU cores
   * GPU-intensive suites should use test.describe.configure({ mode: 'serial' })
   */
  workers: process.env.CI ? "50%" : undefined, // CI: 50%, local: CPU count
  /* Extend timeouts for GPU operations and worker teardown cleanup */
  timeout: 480_000,
  expect: { timeout: 15_000 },
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 1,
  /* HTML report for demo walkthroughs; list for console progress */
  reporter: [
    ["html", { open: "never", outputFolder: "playwright-report" }],
    ["list"],
  ],
  use: {
    baseURL: "http://localhost:5173",
    headless: true,
    screenshot: "on",
    trace: "retain-on-failure",
    video: "on",
    /* Reduce GPU ReadPixels stalls in headless SwiftShader */
    launchOptions: {
      args: [
        "--disable-gpu-compositing",
        "--disable-accelerated-video-decode",
        "--disable-accelerated-video-encode",
      ],
    },
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npx vite --port 5173",
    url: "http://localhost:5173",
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
});