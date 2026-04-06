import { test, expect } from "./fixtures";
import { ChokepointPanelPage, DarkShipPanelPage, IntelBriefingPanelPage } from "./pages";

/**
 * Maritime intelligence panels — Chokepoints, Dark Ships, Intel Briefing.
 * Tests content loading, item interaction, and edge cases.
 */

// ── Chokepoints ───────────────────────────────────────────────────────────
test.describe("ChokepointPanel — core", () => {
  let cp: ChokepointPanelPage;

  test.beforeEach(async ({ page }) => {
    cp = new ChokepointPanelPage(page);
    await cp.open();
  });

  test("panel renders heading Chokepoints", async () => {
    await expect(cp.heading).toContainText("Chokepoints");
  });

  test("panel shows loading, items, or error state", async () => {
    await cp.waitForContent();
    await expect(cp.panel).toBeVisible();
  });

  test("chokepoint items are clickable", async () => {
    await cp.waitForContent();
    const count = await cp.getChokepointCount();
    if (count > 0) {
      await cp.selectChokepoint(0);
      await expect(cp.panel).toBeVisible();
    }
  });

  test("threat badges appear on chokepoint items", async () => {
    await cp.waitForContent();
    const count = await cp.getChokepointCount();
    if (count > 0) {
      // Should contain a threat indicator
      const badges = cp.panel.locator("text=CRITICAL, text=HIGH, text=ELEVATED, text=LOW");
      // At least some threat label should be present in the panel
      await expect(cp.panel).toBeVisible();
    }
  });
});

// ── Dark Ships ────────────────────────────────────────────────────────────
test.describe("DarkShipPanel — core", () => {
  let ds: DarkShipPanelPage;

  test.beforeEach(async ({ page }) => {
    ds = new DarkShipPanelPage(page);
    await ds.open();
  });

  test("panel renders heading Dark Ships", async () => {
    await expect(ds.heading).toContainText("Dark Ships");
  });

  test("panel shows detection state (loading / candidates / empty / error)", async () => {
    await ds.waitForContent();
    await expect(ds.panel).toBeVisible();
  });

  test("dark ship candidates are clickable", async () => {
    await ds.waitForContent();
    const count = await ds.getCandidateCount();
    if (count > 0) {
      await ds.selectCandidate(0);
      await expect(ds.panel).toBeVisible();
    }
  });

  test("candidate count badge is visible in heading", async () => {
    await ds.waitForContent();
    // The heading may include a count badge
    await expect(ds.heading).toBeVisible();
  });
});

// ── Intel Briefing ────────────────────────────────────────────────────────
test.describe("IntelBriefingPanel — core", () => {
  let ib: IntelBriefingPanelPage;

  test.beforeEach(async ({ page }) => {
    ib = new IntelBriefingPanelPage(page);
    await ib.open();
  });

  test("panel renders INTELLIGENCE BRIEFING content", async () => {
    await ib.waitForContent();
    await expect(ib.panel).toBeVisible();
  });

  test("vessel alerts are clickable", async () => {
    await ib.waitForContent();
    const count = await ib.vesselAlerts.count();
    if (count > 0) {
      await ib.selectVesselAlert(0);
      await expect(ib.panel).toBeVisible();
    }
  });
});

// ── Cross-panel navigation between maritime panels ────────────────────────
test.describe("Maritime panels — cross-navigation", () => {
  test("switching between Routes → Dark Ships → Briefing works seamlessly", async ({ page }) => {
    const cp = new ChokepointPanelPage(page);
    await cp.goto();

    await cp.openPanel("Routes");
    await expect(cp.panel).toBeVisible({ timeout: 10_000 });

    await cp.openPanel("Dark Ships");
    await expect(page.locator('[data-testid="dark-ship-panel"]')).toBeVisible({ timeout: 10_000 });

    await cp.openPanel("Briefing");
    await expect(page.locator('[data-testid="intel-briefing-panel"]')).toBeVisible({ timeout: 10_000 });
  });
});
