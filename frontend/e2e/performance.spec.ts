import { test, expect } from "./fixtures";
import { BasePage, LayerPanelPage, SearchPanelPage } from "./pages";

/**
 * Performance and responsiveness tests — ensures the app meets its
 * declared performance budgets under realistic conditions.
 *
 * Budgets:
 *   - Page interactive: 8 s
 *   - Layer toggle response: 3 s
 *   - Search first results: 5 s
 *   - Density slider update: 2 s
 */

const INTERACTIVE_BUDGET_MS = 8_000;
const LAYER_TOGGLE_BUDGET_MS = 3_000;
const SEARCH_RENDER_BUDGET_MS = 5_000;

test.describe("Performance — page load", () => {
  test("page reaches interactive state within budget", async ({ page }) => {
    const base = new BasePage(page);
    const elapsed = await base.measureMs(async () => {
      await base.goto();
    });
    expect(elapsed).toBeLessThan(INTERACTIVE_BUDGET_MS);
  });

  test("PerformanceNavigationTiming domInteractive within budget", async ({ page }) => {
    const base = new BasePage(page);
    await base.goto();

    const metrics = await page.evaluate(() => {
      const [nav] = performance.getEntriesByType("navigation") as PerformanceNavigationTiming[];
      if (!nav) return null;
      return {
        domInteractive: Math.round(nav.domInteractive),
        domComplete: Math.round(nav.domComplete),
        loadEventEnd: Math.round(nav.loadEventEnd),
      };
    });

    if (metrics) {
      expect(metrics.domInteractive).toBeLessThan(INTERACTIVE_BUDGET_MS);
    }
  });
});

test.describe("Performance — layer toggling", () => {
  test("enabling all layers responds within budget", async ({ page }) => {
    const lp = new LayerPanelPage(page);
    await lp.open();

    const elapsed = await lp.measureMs(async () => {
      await lp.enableAll();
    });
    expect(elapsed).toBeLessThan(LAYER_TOGGLE_BUDGET_MS * 5); // 5x for all toggles
    await expect(lp.panel).toBeVisible({ timeout: LAYER_TOGGLE_BUDGET_MS });
  });
});

test.describe("Performance — search rendering", () => {
  test("search renders first results page within budget", async ({ page }) => {
    const sp = new SearchPanelPage(page);
    await sp.open();

    const elapsed = await sp.measureMs(async () => {
      await sp.search();
      await sp.waitForResults(SEARCH_RENDER_BUDGET_MS);
    });
    expect(elapsed).toBeLessThan(SEARCH_RENDER_BUDGET_MS);
  });
});

test.describe("Performance — cross-panel switching", () => {
  test("switching between panels does not exceed 2s per switch", async ({ page }) => {
    const base = new BasePage(page);
    await base.goto();

    const panels = ["Sensors", "Signals", "Replay", "Intel", "Routes", "Dark Ships", "Briefing", "Extract", "Diff", "Cameras", "Cases", "Zones"];

    for (const panelLabel of panels) {
      const elapsed = await base.measureMs(async () => {
        await base.openPanel(panelLabel);
      });
      expect(elapsed).toBeLessThan(2_000);
    }
  });

  test("sidebar remains interactive after rapid tab switching", async ({ page }) => {
    const base = new BasePage(page);
    await base.goto();

    // Rapid-fire panel switches
    for (const label of ["Sensors", "Signals", "Replay", "Intel", "Sensors"]) {
      await base.openPanel(label);
    }

    await base.expectPanelActive("Sensors");
  });
});

test.describe("Performance — no JS errors during navigation", () => {
  test("no console errors during full app interaction flow", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (err) => errors.push(err.message));

    const base = new BasePage(page);
    await base.goto();

    // Navigate through several panels
    for (const label of ["Sensors", "Signals", "Replay", "Intel", "Routes", "Cameras", "Cases", "Status"]) {
      await base.openPanel(label);
    }

    // Switch view modes
    await base.switchTo2D();
    await base.switchTo3D();

    // Any uncaught JS exceptions mean a real bug
    expect(errors).toEqual([]);
  });
});
