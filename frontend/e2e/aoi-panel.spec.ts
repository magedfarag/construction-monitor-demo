import { test, expect } from "./fixtures";
import { AoiPanelPage } from "./pages";

/**
 * AOI / Zones panel — draw tools, save form, AOI list, selection,
 * deletion, empty state, and edge cases.
 */

test.describe("AoiPanel — core", () => {
  let aoi: AoiPanelPage;

  test.beforeEach(async ({ page }) => {
    aoi = new AoiPanelPage(page);
    await aoi.open();
  });

  test("panel renders heading", async () => {
    await expect(aoi.heading).toContainText("Areas of Interest");
  });

  test("panel shows draw tools or existing AOI list", async () => {
    const hasDrawTools = await aoi.panel.locator(".draw-tools").isVisible();
    const hasAois = (await aoi.getAoiCount()) > 0;
    const hasEmpty = await aoi.panel.locator("text=Draw a").isVisible();
    expect(hasDrawTools || hasAois || hasEmpty).toBeTruthy();
  });
});

test.describe("AoiPanel — AOI list interactions", () => {
  let aoi: AoiPanelPage;

  test.beforeEach(async ({ page }) => {
    aoi = new AoiPanelPage(page);
    await aoi.open();
  });

  test("clicking an AOI item selects it without error", async () => {
    const count = await aoi.getAoiCount();
    if (count > 0) {
      await aoi.selectAoi(0);
      // App should remain stable
      await expect(
        aoi.mapContainer.or(aoi.globeContainer).first(),
      ).toBeVisible();
    }
  });

  test("multiple AOIs can be clicked in sequence", async () => {
    const count = await aoi.getAoiCount();
    for (let i = 0; i < Math.min(count, 3); i++) {
      await aoi.selectAoi(i);
    }
    await expect(aoi.panel).toBeVisible();
  });
});

test.describe("AoiPanel — 2D draw tools", () => {
  test("draw tools (BBox and Polygon) are visible in 2D mode", async ({ page }) => {
    const aoi = new AoiPanelPage(page);
    await aoi.goto();
    await aoi.switchTo2D();

    await expect(aoi.drawBboxBtn).toBeVisible();
    await expect(aoi.drawPolygonBtn).toBeVisible();
  });

  test("clicking BBox activates draw mode and shows hint", async ({ page }) => {
    const aoi = new AoiPanelPage(page);
    await aoi.goto();
    await aoi.switchTo2D();

    await aoi.drawBboxBtn.click();
    await expect(aoi.drawHint).toBeVisible();
    await expect(aoi.drawHint).toContainText("corners");
  });

  test("clicking Polygon activates draw mode and shows hint", async ({ page }) => {
    const aoi = new AoiPanelPage(page);
    await aoi.goto();
    await aoi.switchTo2D();

    await aoi.drawPolygonBtn.click();
    await expect(aoi.drawHint).toBeVisible();
    await expect(aoi.drawHint).toContainText("vertices");
  });

  test("clicking active draw tool deactivates it", async ({ page }) => {
    const aoi = new AoiPanelPage(page);
    await aoi.goto();
    await aoi.switchTo2D();

    await aoi.drawBboxBtn.click();
    await expect(aoi.drawHint).toBeVisible();
    // Click again to deactivate
    await aoi.drawBboxBtn.click();
    await expect(aoi.drawHint).not.toBeVisible();
  });

  test("switching draw tool from BBox to Polygon changes hint", async ({ page }) => {
    const aoi = new AoiPanelPage(page);
    await aoi.goto();
    await aoi.switchTo2D();

    await aoi.drawBboxBtn.click();
    await expect(aoi.drawHint).toContainText("corners");

    await aoi.drawPolygonBtn.click();
    await expect(aoi.drawHint).toContainText("vertices");
  });
});
