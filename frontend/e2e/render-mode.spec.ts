import { test, expect } from "@playwright/test";
import { RenderModeSelectorPage } from "./pages";

/**
 * Render Mode Selector — Phase 4 render modes: Day, Low Light,
 * Night Vision, Thermal. Tests mode switching, active state styling,
 * and round-trip toggling.
 */

test.describe("RenderModeSelector — visibility", () => {
  let rm: RenderModeSelectorPage;

  test.beforeEach(async ({ page }) => {
    rm = new RenderModeSelectorPage(page);
    await rm.goto();
    await rm.waitForSelector();
  });

  test("all four render mode buttons are visible on load", async () => {
    await expect(rm.dayBtn).toBeVisible();
    await expect(rm.lowLightBtn).toBeVisible();
    await expect(rm.nightVisionBtn).toBeVisible();
    await expect(rm.thermalBtn).toBeVisible();
  });
});

test.describe("RenderModeSelector — mode switching", () => {
  let rm: RenderModeSelectorPage;

  test.beforeEach(async ({ page }) => {
    rm = new RenderModeSelectorPage(page);
    await rm.goto();
    await rm.waitForSelector();
  });

  const MODES = ["day", "lowLight", "nightVision", "thermal"] as const;

  for (const mode of MODES) {
    test(`selecting ${mode} activates it`, async () => {
      await rm.selectMode(mode);
      await rm.expectActiveMode(mode);
    });
  }

  test("switching from Night Vision to Day resets active state", async () => {
    await rm.selectMode("nightVision");
    await rm.expectActiveMode("nightVision");
    await rm.selectMode("day");
    await rm.expectActiveMode("day");
  });

  test("cycling through all modes in sequence works", async () => {
    for (const mode of MODES) {
      await rm.selectMode(mode);
      await rm.expectActiveMode(mode);
    }
  });

  test("selecting the same mode twice keeps it active", async () => {
    await rm.selectMode("thermal");
    await rm.expectActiveMode("thermal");
    await rm.selectMode("thermal");
    await rm.expectActiveMode("thermal");
  });

  test("render mode persists across panel switches", async () => {
    await rm.selectMode("nightVision");
    await rm.expectActiveMode("nightVision");

    // Switch sidebar panels
    await rm.openPanel("Sensors");
    await rm.openPanel("Zones");

    // Mode should still be active
    await rm.expectActiveMode("nightVision");
  });
});
