import { test as base, expect } from "@playwright/test";

/**
 * Extended Playwright fixtures that navigate the page to about:blank after
 * each test.  This releases CesiumJS / WebGL GPU resources *before* the
 * browser context closes, preventing the "GPU stall due to ReadPixels"
 * teardown timeout that otherwise occurs when video recording is enabled.
 */
export const test = base.extend<Record<string, never>>({
  page: async ({ page }, use) => {
    await use(page);
    // Release WebGL context with short timeout before Playwright finalises the video.
    try {
      await Promise.race([
        page.goto("about:blank", { waitUntil: "domcontentloaded" }),
        new Promise(resolve => setTimeout(resolve, 5000)) // 5s max wait
      ]);
    } catch {
      // Ignore any errors during cleanup
    }
  },
});

export { expect };
