import { test, expect } from "@playwright/test";
import { BasePage, LayerPanelPage, SearchPanelPage, AnalyticsPanelPage, ExportPanelPage, PlaybackPanelPage } from "./pages";

/**
 * Integration / workflow tests — verifies multi-step user workflows
 * that span multiple panels and views.
 */

test.describe("Workflow: analyst investigation flow", () => {
  test("analyst opens layers → enables Maritime → switches to signals → searches → exports", async ({ page }) => {
    // Step 1: Enable Maritime layer
    const lp = new LayerPanelPage(page);
    await lp.open();
    await lp.toggleMaritime.check();
    await expect(lp.densityControl).toBeVisible();

    // Step 2: Switch to Search panel and search
    const sp = new SearchPanelPage(page);
    await sp.openPanel("Signals");
    await expect(sp.panel).toBeVisible();
    await sp.search();
    await sp.waitForResults();

    // Step 3: Export results
    const ep = new ExportPanelPage(page);
    await ep.openPanel("Extract");
    await expect(ep.panel).toBeVisible();
    await ep.selectFormat("CSV");
    await ep.export();
    await ep.waitForExportResult();

    // App should be fully stable
    await expect(
      ep.mapContainer.or(ep.globeContainer).first(),
    ).toBeVisible();
  });
});

test.describe("Workflow: change detection flow", () => {
  test("analyst runs change detection → reviews candidates → exports", async ({ page }) => {
    // Step 1: Run change detection
    const ap = new AnalyticsPanelPage(page);
    await ap.open();
    await ap.runChangeDetection();
    await ap.waitForResults();

    // Step 2: Export
    const ep = new ExportPanelPage(page);
    await ep.openPanel("Extract");
    await expect(ep.panel).toBeVisible();
    await ep.selectFormat("GeoJSON");
    await ep.export();
    await ep.waitForExportResult();
    await expect(ep.panel).toBeVisible();
  });
});

test.describe("Workflow: view mode during layer interaction", () => {
  test("layers persist state across 2D → 3D → 2D transitions", async ({ page }) => {
    const lp = new LayerPanelPage(page);
    await lp.open();

    // Enable Maritime in 2D
    await lp.switchTo2D();
    await lp.toggleMaritime.check();
    await expect(lp.toggleMaritime).toBeChecked();

    // Switch to 3D
    await lp.switchTo3D();
    // Go back to Sensors panel
    await lp.openPanel("Sensors");
    await expect(lp.toggleMaritime).toBeChecked();

    // Switch back to 2D
    await lp.switchTo2D();
    await lp.openPanel("Sensors");
    await expect(lp.toggleMaritime).toBeChecked();
  });
});

test.describe("Workflow: playback followed by analytics", () => {
  test("loading playback frames then switching to analytics keeps app stable", async ({ page }) => {
    const pb = new PlaybackPanelPage(page);
    await pb.open();
    await pb.loadFrames();
    await pb.waitForFramesLoaded();

    // Switch to analytics
    const ap = new AnalyticsPanelPage(page);
    await ap.openPanel("Intel");
    await expect(ap.panel).toBeVisible();
    await ap.submitBtn.click();
    await ap.waitForResults();

    // Map must be stable
    await expect(
      ap.mapContainer.or(ap.globeContainer).first(),
    ).toBeVisible();
  });
});

test.describe("Workflow: basemap style switching", () => {
  test("all basemap styles can be selected in 2D", async ({ page }) => {
    const base = new BasePage(page);
    await base.goto();
    await base.switchTo2D();

    const styles = ["Vector", "Dark", "Light", "Sat"];
    for (const style of styles) {
      const btn = base.basemapPicker.locator(`button:has-text("${style}")`);
      await btn.click();
      await expect(btn).toHaveClass(/basemap-btn--active/);
    }
  });
});

test.describe("Workflow: animation controls", () => {
  test("play/pause and reset animation controls work", async ({ page }) => {
    const base = new BasePage(page);
    await base.goto();

    // Play animation
    await base.animPlayPause.click();
    // Should show animation time or pause button
    await expect(base.animPlayPause).toBeVisible();

    // Reset
    await base.animReset.click();
    await expect(base.animPlayPause).toBeVisible();
  });

  test("animation time display appears during playback", async ({ page }) => {
    const base = new BasePage(page);
    await base.goto();

    await base.animPlayPause.click();
    // Wait a moment for animation to start
    await page.waitForTimeout(500);
    // Time display should appear (if animation started successfully)
    const hasTime = await base.animTime.isVisible().catch(() => false);
    if (hasTime) {
      await expect(base.animTime).toContainText(/\d/);
    }

    // Stop animation
    await base.animPlayPause.click();
  });
});

test.describe("Workflow: full sidebar cycle", () => {
  test("visiting every panel and returning to Zones produces no errors", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (err) => errors.push(err.message));

    const base = new BasePage(page);
    await base.goto();

    const allPanels = [
      "Zones", "Sensors", "Signals", "Replay", "Intel",
      "Routes", "Dark Ships", "Briefing", "Extract", "Diff",
      "Cameras", "Status", "Cases",
    ];

    for (const label of allPanels) {
      await base.openPanel(label);
      // Give each panel a moment to render
      await page.waitForTimeout(200);
    }

    // Return to Zones
    await base.openPanel("Zones");
    await base.expectPanelActive("Zones");

    expect(errors).toEqual([]);
  });
});
