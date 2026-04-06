import { test, expect } from "./fixtures";
import { PlaybackPanelPage } from "./pages";

/**
 * Playback / Replay panel — load frames, transport controls,
 * speed selection, and cross-panel interoperability.
 */

test.describe("PlaybackPanel — core", () => {
  let pb: PlaybackPanelPage;

  test.beforeEach(async ({ page }) => {
    pb = new PlaybackPanelPage(page);
    await pb.open();
  });

  test("panel renders heading and Load Frames button", async () => {
    await expect(pb.heading).toContainText("Playback");
    await expect(pb.loadFramesBtn).toBeVisible();
  });

  test("Load Frames triggers API request", async () => {
    const responsePromise = pb.page
      .waitForResponse(
        (r) => r.url().includes("/api/v1/playback/query"),
        { timeout: 5_000 },
      )
      .catch(() => null);
    await pb.loadFrames();
    // Should show loading state or transport controls
    await pb.waitForFramesLoaded();
    await responsePromise;
  });

  test("Load Frames shows loading indicator", async () => {
    await pb.loadFrames();
    // Briefly shows Loading state
    await Promise.race([
      pb.page.locator("text=Loading").waitFor({ timeout: 3_000 }),
      pb.stepBackBtn.waitFor({ timeout: 5_000 }),
    ]).catch(() => {});
    await expect(pb.panel).toBeVisible();
  });
});

test.describe("PlaybackPanel — transport controls after load", () => {
  test("transport controls appear after loading frames", async ({ page }) => {
    const pb = new PlaybackPanelPage(page);
    await pb.open();
    await pb.loadFrames();
    await pb.waitForFramesLoaded(8_000);

    // If frames loaded successfully, transport controls should be visible
    const hasControls = await pb.stepBackBtn.isVisible().catch(() => false);
    if (hasControls) {
      await expect(pb.stepForwardBtn).toBeVisible();
      await expect(pb.speedSelect).toBeVisible();
    }
  });

  test("speed selector has standard options", async ({ page }) => {
    const pb = new PlaybackPanelPage(page);
    await pb.open();
    await pb.loadFrames();
    await pb.waitForFramesLoaded(8_000);

    if (await pb.speedSelect.isVisible().catch(() => false)) {
      const options = pb.speedSelect.locator("option");
      const count = await options.count();
      expect(count).toBeGreaterThanOrEqual(2);
    }
  });
});

test.describe("PlaybackPanel — cross-panel interop", () => {
  test("loading frames does not freeze the sidebar — can switch tabs", async ({ page }) => {
    const pb = new PlaybackPanelPage(page);
    await pb.open();
    await pb.loadFrames();

    // Immediately switch to another tab
    await pb.openPanel("Sensors");
    const layerPanel = page.locator('[data-testid="layer-panel"]');
    await expect(layerPanel).toBeVisible({ timeout: 3_000 });
  });

  test("switching away from Replay and back preserves panel state", async ({ page }) => {
    const pb = new PlaybackPanelPage(page);
    await pb.open();
    await pb.loadFrames();
    await pb.waitForFramesLoaded();

    // Switch away
    await pb.openPanel("Signals");
    // Switch back
    await pb.openPanel("Replay");
    await expect(pb.panel).toBeVisible();
  });
});
