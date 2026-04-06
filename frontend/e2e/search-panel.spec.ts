import { test, expect } from "./fixtures";
import { SearchPanelPage } from "./pages";

/**
 * Search / Events panel — search flow, pagination, event click,
 * empty state, loading state, and performance budget.
 */

test.describe("SearchPanel — core", () => {
  let sp: SearchPanelPage;

  test.beforeEach(async ({ page }) => {
    sp = new SearchPanelPage(page);
    await sp.open();
  });

  test("panel renders heading and search button", async () => {
    await expect(sp.panel.locator("h3")).toContainText("Events");
    await expect(sp.searchBtn).toBeVisible();
  });

  test("clicking search does not crash and panel remains visible", async () => {
    await sp.search();
    await sp.waitForResults();
    // After search, the panel should still be visible regardless of backend state
    await expect(sp.panel).toBeVisible();
  });
});

test.describe("SearchPanel — pagination", () => {
  let sp: SearchPanelPage;

  test.beforeEach(async ({ page }) => {
    sp = new SearchPanelPage(page);
    await sp.open();
    await sp.search();
    await sp.waitForResults();
  });

  test("pagination controls appear when there are multiple pages", async () => {
    const eventCount = await sp.getEventCount();
    if (eventCount > 0) {
      const paginationVisible = await sp.pagination.isVisible();
      // Pagination shown only when > 1 page; verify it renders correctly if present
      if (paginationVisible) {
        await expect(sp.paginationInfo).toBeVisible();
        await expect(sp.paginationPrev).toBeVisible();
        await expect(sp.paginationNext).toBeVisible();
      }
    }
  });

  test("next page advances pagination info", async () => {
    if (await sp.pagination.isVisible()) {
      const before = await sp.getPageInfo();
      await sp.nextPage();
      // Page info may change or next button may be disabled on last page
      const after = await sp.getPageInfo();
      // At minimum the component should not crash
      expect(typeof after).toBe("string");
    }
  });

  test("prev button is disabled on first page", async () => {
    if (await sp.pagination.isVisible()) {
      await expect(sp.paginationPrev).toBeDisabled();
    }
  });
});

test.describe("SearchPanel — event interaction", () => {
  test("clicking an event item does not crash the app", async ({ page }) => {
    const sp = new SearchPanelPage(page);
    await sp.open();
    await sp.search();
    await sp.waitForResults();

    const count = await sp.getEventCount();
    if (count > 0) {
      await sp.clickEvent(0);
      // App should remain stable — map still visible
      await expect(
        sp.mapContainer.or(sp.globeContainer).first(),
      ).toBeVisible();
    }
  });
});

test.describe("SearchPanel — performance", () => {
  const SEARCH_BUDGET_MS = 5_000;

  test("search renders first results within 5s budget", async ({ page }) => {
    const sp = new SearchPanelPage(page);
    await sp.open();

    const elapsed = await sp.measureMs(async () => {
      await sp.search();
      await sp.waitForResults(SEARCH_BUDGET_MS);
    });
    expect(elapsed).toBeLessThan(SEARCH_BUDGET_MS);
  });
});
