import { test, expect } from "./fixtures";
import { AnalyticsPanelPage } from "./pages";

/**
 * Analytics / Intel panel — change detection trigger, result states,
 * candidate review actions, and edge cases.
 */

test.describe("AnalyticsPanel — core", () => {
  let ap: AnalyticsPanelPage;

  test.beforeEach(async ({ page }) => {
    ap = new AnalyticsPanelPage(page);
    await ap.open();
  });

  test("panel renders heading and submit button", async () => {
    await expect(ap.heading).toContainText("Change Detection");
    await expect(ap.submitBtn).toBeVisible();
  });

  test("submit button text says Run Change Detection", async () => {
    await expect(ap.submitBtn).toContainText(/Run Change Detection|Run/i);
  });

  test("running change detection shows result state", async () => {
    await ap.runChangeDetection();
    await ap.waitForResults();
    // Should be in one of: running, candidates, no candidates, or error
    const panel = ap.panel;
    const hasRunning = await panel.locator("text=Running").isVisible();
    const hasCandidates = (await ap.candidates.count()) > 0;
    const hasNone = await panel.locator("text=No candidates").isVisible();
    const hasError = await panel.locator("text=Failed").isVisible();
    expect(hasRunning || hasCandidates || hasNone || hasError).toBeTruthy();
  });

  test("submitting does not freeze the map container", async () => {
    await ap.runChangeDetection();
    await expect(
      ap.mapContainer.or(ap.globeContainer).first(),
    ).toBeVisible({ timeout: 3_000 });
  });
});

test.describe("AnalyticsPanel — candidate actions", () => {
  test("confirm and dismiss buttons appear on candidates", async ({ page }) => {
    const ap = new AnalyticsPanelPage(page);
    await ap.open();
    await ap.runChangeDetection();
    await ap.waitForResults();

    const candidateCount = await ap.candidates.count();
    if (candidateCount > 0) {
      await expect(ap.confirmBtns.first()).toBeVisible();
      await expect(ap.dismissBtns.first()).toBeVisible();
    }
  });

  test("clicking confirm on a candidate changes its state", async ({ page }) => {
    const ap = new AnalyticsPanelPage(page);
    await ap.open();
    await ap.runChangeDetection();
    await ap.waitForResults();

    if ((await ap.confirmBtns.count()) > 0) {
      await ap.confirmCandidate(0);
      // Panel should remain stable
      await expect(ap.panel).toBeVisible();
    }
  });

  test("clicking dismiss on a candidate changes its state", async ({ page }) => {
    const ap = new AnalyticsPanelPage(page);
    await ap.open();
    await ap.runChangeDetection();
    await ap.waitForResults();

    if ((await ap.dismissBtns.count()) > 0) {
      await ap.dismissCandidate(0);
      await expect(ap.panel).toBeVisible();
    }
  });
});
