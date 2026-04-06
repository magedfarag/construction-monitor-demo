import { test, expect } from "./fixtures";
import { LayerPanelPage } from "./pages";

/**
 * Layer panel — toggles, conditional controls, density slider,
 * boundary conditions, and all-layers performance scenario.
 */

test.describe("LayerPanel — core functionality", () => {
  let lp: LayerPanelPage;

  test.beforeEach(async ({ page }) => {
    lp = new LayerPanelPage(page);
    await lp.open();
  });

  test("panel renders heading and toggles", async () => {
    await expect(lp.panel.locator("h3")).toContainText("Layers");
    const toggles = lp.page.locator(".layer-toggle input");
    const count = await toggles.count();
    expect(count).toBeGreaterThanOrEqual(10);
  });

  // ── Individual toggle checks ────────────────────────────────────────
  const TOGGLE_NAMES: Array<[string, keyof LayerPanelPage]> = [
    ["AOI Boundaries", "toggleAoiBoundaries"],
    ["Imagery Footprints", "toggleImageryFootprints"],
    ["Events", "toggleEvents"],
    ["GDELT", "toggleGdelt"],
    ["Maritime", "toggleMaritime"],
    ["Aviation", "toggleAviation"],
    ["Satellite Orbits", "toggleSatelliteOrbits"],
    ["Airspace", "toggleAirspace"],
    ["GPS Jamming", "toggleGpsJamming"],
    ["Strike Events", "toggleStrikes"],
    ["Terrain", "toggleTerrain"],
    ["3D Buildings", "toggle3dBuildings"],
    ["Detections", "toggleDetections"],
  ];

  for (const [label, prop] of TOGGLE_NAMES) {
    test(`toggle "${label}" can be checked and unchecked`, async () => {
      const toggle = lp[prop] as import("@playwright/test").Locator;
      await toggle.check();
      await expect(toggle).toBeChecked();
      await toggle.uncheck();
      await expect(toggle).not.toBeChecked();
    });
  }
});

test.describe("LayerPanel — density controls", () => {
  let lp: LayerPanelPage;

  test.beforeEach(async ({ page }) => {
    lp = new LayerPanelPage(page);
    await lp.open();
  });

  test("density control appears when Maritime layer is enabled", async () => {
    await lp.toggleMaritime.check();
    await expect(lp.densityControl).toBeVisible();
    await expect(lp.densitySlider).toBeVisible();
  });

  test("density control appears when Aviation layer is enabled", async () => {
    await lp.toggleAviation.check();
    await expect(lp.densityControl).toBeVisible();
  });

  test("density control hides when both Maritime and Aviation are disabled", async () => {
    await lp.toggleMaritime.check();
    await expect(lp.densityControl).toBeVisible();
    await lp.toggleMaritime.uncheck();
    await lp.toggleAviation.uncheck().catch(() => {});
    await expect(lp.densityControl).not.toBeVisible();
  });

  test("density slider has numeric value in range [0.1, 1]", async () => {
    await lp.toggleMaritime.check();
    const val = parseFloat(await lp.getDensity());
    expect(val).toBeGreaterThanOrEqual(0.1);
    expect(val).toBeLessThanOrEqual(1);
  });

  test("density slider value updates when set to a new value", async () => {
    await lp.toggleMaritime.check();
    const before = await lp.getDensity();
    await lp.setDensity("0.5");
    const after = await lp.getDensity();
    expect(after).toBe("0.5");
  });

  test("density slider boundary: minimum value 0.1", async () => {
    await lp.toggleMaritime.check();
    await lp.setDensity("0.1");
    const val = await lp.getDensity();
    expect(parseFloat(val)).toBeCloseTo(0.1, 1);
  });

  test("density slider boundary: maximum value 1", async () => {
    await lp.toggleMaritime.check();
    await lp.setDensity("1");
    const val = await lp.getDensity();
    expect(parseFloat(val)).toBeCloseTo(1, 1);
  });
});

test.describe("LayerPanel — imagery opacity", () => {
  let lp: LayerPanelPage;

  test.beforeEach(async ({ page }) => {
    lp = new LayerPanelPage(page);
    await lp.open();
  });

  test("imagery opacity control appears when Imagery Footprints is enabled", async () => {
    await lp.toggleImageryFootprints.check();
    await expect(lp.imageryOpacityControl).toBeVisible();
  });

  test("imagery opacity control hides when Imagery Footprints is disabled", async () => {
    await lp.toggleImageryFootprints.check();
    await expect(lp.imageryOpacityControl).toBeVisible();
    await lp.toggleImageryFootprints.uncheck();
    await expect(lp.imageryOpacityControl).not.toBeVisible();
  });
});

test.describe("LayerPanel — all-layers stress", () => {
  const TOGGLE_BUDGET_MS = 3_000;

  // Stress tests need extra time for 13+ toggles with map re-rendering
  test.setTimeout(180_000);

  test("enabling all layers simultaneously keeps sidebar interactive", async ({ page }) => {
    const lp = new LayerPanelPage(page);
    await lp.open();
    await lp.enableAll();
    await expect(lp.panel).toBeVisible({ timeout: TOGGLE_BUDGET_MS });
    // Verify we can still interact with the panel
    await lp.toggleMaritime.uncheck();
    await expect(lp.toggleMaritime).not.toBeChecked();
  });

  test("disabling all layers after enable-all does not hang", async ({ page }) => {
    const lp = new LayerPanelPage(page);
    await lp.open();
    await lp.enableAll();
    await lp.disableAll();
    await expect(lp.panel).toBeVisible({ timeout: TOGGLE_BUDGET_MS });
  });

  test("rapid toggle on/off does not crash", async ({ page }) => {
    const lp = new LayerPanelPage(page);
    await lp.open();
    for (let i = 0; i < 5; i++) {
      await lp.toggleMaritime.check();
      await lp.toggleMaritime.uncheck();
    }
    await expect(lp.panel).toBeVisible();
  });
});
