import { test, expect } from "./fixtures";
import { ExportPanelPage } from "./pages";

/**
 * Export / Extract panel — format selection, export trigger,
 * result states, and edge cases.
 */

test.describe("ExportPanel — core", () => {
  let ep: ExportPanelPage;

  test.beforeEach(async ({ page }) => {
    ep = new ExportPanelPage(page);
    await ep.open();
  });

  test("panel renders heading, format select, and export button", async () => {
    await expect(ep.heading).toContainText("Export");
    await expect(ep.formatSelect).toBeVisible();
    await expect(ep.exportBtn).toBeVisible();
  });

  test("format selector has CSV and GeoJSON options", async () => {
    const options = ep.formatSelect.locator("option");
    const count = await options.count();
    expect(count).toBeGreaterThanOrEqual(2);

    const texts: string[] = [];
    for (let i = 0; i < count; i++) {
      texts.push((await options.nth(i).textContent()) ?? "");
    }
    expect(texts.some((t) => /csv/i.test(t))).toBeTruthy();
    expect(texts.some((t) => /geojson/i.test(t))).toBeTruthy();
  });

  test("selecting CSV format sets the select value", async () => {
    await ep.selectFormat("CSV");
    const val = await ep.formatSelect.inputValue();
    expect(val.toLowerCase()).toContain("csv");
  });

  test("selecting GeoJSON format sets the select value", async () => {
    await ep.selectFormat("GeoJSON");
    const val = await ep.formatSelect.inputValue();
    expect(val.toLowerCase()).toContain("geojson");
  });
});

test.describe("ExportPanel — export action", () => {
  test("clicking export shows a result state", async ({ page }) => {
    const ep = new ExportPanelPage(page);
    await ep.open();
    await ep.export();
    await ep.waitForExportResult();
    // Should show one of: Submitting, Done, Export failed, or Error
    const panel = ep.panel;
    const hasSubmitting = await panel.locator("text=Submitting").isVisible();
    const hasDone = await panel.locator("text=Done").isVisible();
    const hasFailed = await panel.locator("text=Export failed").isVisible();
    const hasError = await panel.locator("text=Error").isVisible();
    expect(hasSubmitting || hasDone || hasFailed || hasError).toBeTruthy();
  });

  test("export with CSV format does not crash", async ({ page }) => {
    const ep = new ExportPanelPage(page);
    await ep.open();
    await ep.selectFormat("CSV");
    await ep.export();
    await ep.waitForExportResult();
    await expect(ep.panel).toBeVisible();
  });

  test("export with GeoJSON format does not crash", async ({ page }) => {
    const ep = new ExportPanelPage(page);
    await ep.open();
    await ep.selectFormat("GeoJSON");
    await ep.export();
    await ep.waitForExportResult();
    await expect(ep.panel).toBeVisible();
  });

  test("switching formats between exports does not produce errors", async ({ page }) => {
    const ep = new ExportPanelPage(page);
    await ep.open();
    await ep.selectFormat("CSV");
    await ep.export();
    await ep.waitForExportResult();
    await ep.selectFormat("GeoJSON");
    await ep.export();
    await ep.waitForExportResult();
    await expect(ep.panel).toBeVisible();
  });
});
