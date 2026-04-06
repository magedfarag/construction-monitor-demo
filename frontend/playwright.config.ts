import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./e2e/global-setup.ts",
  /* Ignore the legacy monolithic spec backup */
  testIgnore: ["**/*.bak"],
  fullyParallel: false,
  /* Single worker — WebGL map rendering saturates GPU with parallel instances */
  workers: 1,
  /* Extend timeouts for GPU operations and worker teardown cleanup */
  timeout: 480_000,
  expect: { timeout: 15_000 },
  /* Allow sufficient time for WebGL cleanup fixture to run */
  webServer: undefined, // No built-in server; app runs separately
  /* Extended worker teardown timeout for GPU cleanup */
  fullyParallel: false,
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