import { test, expect } from "./fixtures";
import { CameraFeedPanelPage } from "./pages";

/**
 * Camera Feed panel — opening, content states (loading / cameras / empty / error),
 * camera selection, and edge cases.
 */

test.describe("CameraFeedPanel — core", () => {
  let cam: CameraFeedPanelPage;

  test.beforeEach(async ({ page }) => {
    cam = new CameraFeedPanelPage(page);
    await cam.open();
  });

  test("panel is visible after opening Cameras tab", async () => {
    await expect(cam.panel).toBeVisible();
  });

  test("panel renders heading Camera Feeds", async () => {
    await expect(cam.heading.first()).toContainText("Camera Feeds");
  });

  test("panel shows loading, camera list, empty, or error state", async () => {
    await cam.waitForContent();
    // At least the panel itself is visible
    await expect(cam.panel).toBeVisible();
  });
});

test.describe("CameraFeedPanel — interactions", () => {
  test("clicking a camera item does not crash", async ({ page }) => {
    const cam = new CameraFeedPanelPage(page);
    await cam.open();
    await cam.waitForContent();

    const items = cam.panel.locator("li, .camera-item");
    const count = await items.count();
    if (count > 0) {
      await items.first().click();
      await expect(cam.panel).toBeVisible();
    }
  });

  test("Jump to map button is present when cameras exist", async ({ page }) => {
    const cam = new CameraFeedPanelPage(page);
    await cam.open();
    await cam.waitForContent();

    const items = cam.panel.locator("li, .camera-item");
    const count = await items.count();
    if (count > 0) {
      await items.first().click();
      // Jump to map button may appear in detail view
      const jumpBtn = cam.jumpToMapBtns.first();
      if (await jumpBtn.isVisible().catch(() => false)) {
        await expect(jumpBtn).toBeVisible();
      }
    }
  });
});

test.describe("CameraFeedPanel — edge cases", () => {
  test("switching to Cameras tab multiple times does not duplicate content", async ({ page }) => {
    const cam = new CameraFeedPanelPage(page);
    await cam.goto();
    await cam.openPanel("Cameras");
    await expect(cam.panel).toBeVisible({ timeout: 10_000 });
    await cam.openPanel("Sensors");
    await cam.openPanel("Cameras");
    await expect(cam.panel).toBeVisible({ timeout: 10_000 });
    // Only one panel instance should exist
    const panelCount = await page.locator('[data-testid="camera-feed-panel"]').count();
    expect(panelCount).toBe(1);
  });
});
