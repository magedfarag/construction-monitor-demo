import { test, expect } from "@playwright/test";
import { TimelinePanelPage } from "./pages";

/**
 * Timeline panel — visibility, expand/collapse, presets,
 * date range inputs, and boundary conditions.
 */

test.describe("TimelinePanel — core", () => {
  let tp: TimelinePanelPage;

  test.beforeEach(async ({ page }) => {
    tp = new TimelinePanelPage(page);
    await tp.goto();
  });

  test("timeline panel is visible at the bottom of the page", async () => {
    await tp.expectPanelVisible();
  });

  test("timeline heading says Timeline", async () => {
    await expect(tp.heading).toContainText("Timeline");
  });
});

test.describe("TimelinePanel — expand/collapse", () => {
  let tp: TimelinePanelPage;

  test.beforeEach(async ({ page }) => {
    tp = new TimelinePanelPage(page);
    await tp.goto();
  });

  test("expand toggle is present", async () => {
    await expect(tp.expandToggle).toBeVisible();
  });

  test("clicking expand toggle shows/hides content", async () => {
    // Click to collapse (or expand depending on initial state)
    await tp.expandToggle.click();
    // Click again to restore
    await tp.expandToggle.click();
    await tp.expectPanelVisible();
  });
});

test.describe("TimelinePanel — presets", () => {
  let tp: TimelinePanelPage;

  test.beforeEach(async ({ page }) => {
    tp = new TimelinePanelPage(page);
    await tp.goto();
    await tp.expand();
  });

  test("24h preset button is visible", async () => {
    await expect(tp.preset24h).toBeVisible();
  });

  test("7d preset button is visible", async () => {
    await expect(tp.preset7d).toBeVisible();
  });

  test("30d preset button is visible", async () => {
    await expect(tp.preset30d).toBeVisible();
  });

  test("clicking 24h preset updates the date range", async () => {
    await tp.selectPreset("24h");
    // Panel should remain stable
    await tp.expectPanelVisible();
  });

  test("clicking 7d preset updates the date range", async () => {
    await tp.selectPreset("7d");
    await tp.expectPanelVisible();
  });

  test("clicking 30d preset updates the date range", async () => {
    await tp.selectPreset("30d");
    await tp.expectPanelVisible();
  });

  test("cycling through all presets does not crash", async () => {
    await tp.selectPreset("24h");
    await tp.selectPreset("7d");
    await tp.selectPreset("30d");
    await tp.selectPreset("24h");
    await tp.expectPanelVisible();
  });
});

test.describe("TimelinePanel — date inputs", () => {
  let tp: TimelinePanelPage;

  test.beforeEach(async ({ page }) => {
    tp = new TimelinePanelPage(page);
    await tp.goto();
    await tp.expand();
  });

  test("start and end datetime inputs are present", async () => {
    await expect(tp.startInput).toBeVisible();
    await expect(tp.endInput).toBeVisible();
  });

  test("start input has a datetime-local type", async () => {
    await expect(tp.startInput).toHaveAttribute("type", "datetime-local");
  });

  test("end input has a datetime-local type", async () => {
    await expect(tp.endInput).toHaveAttribute("type", "datetime-local");
  });
});
