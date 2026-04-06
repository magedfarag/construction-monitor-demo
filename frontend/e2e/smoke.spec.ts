import { test, expect } from "./fixtures";
import { BasePage } from "./pages";

/**
 * Smoke tests — verifies the app shell loads correctly, the header is
 * present, all sidebar tabs exist, and the primary view containers mount.
 *
 * These are the gate-keeper tests: if any of these fail, the rest of the
 * suite is not meaningful.
 */

test.describe("App Shell — smoke", () => {
  let base: BasePage;

  test.beforeEach(async ({ page }) => {
    base = new BasePage(page);
    await base.goto();
  });

  // ── Header ──────────────────────────────────────────────────────────────
  test("page loads and renders the map or globe container", async () => {
    await expect(
      base.mapContainer.or(base.globeContainer).first(),
    ).toBeVisible();
  });

  test("app title contains ARGUS", async () => {
    await expect(base.appTitle).toContainText("ARGUS");
  });

  test("LIVE badge is visible in header", async () => {
    await expect(base.liveBadge).toBeVisible();
    await expect(base.liveBadge).toContainText("LIVE");
  });

  test("UTC clock updates in header", async () => {
    await expect(base.headerClock).toBeVisible();
    await expect(base.headerClock).toContainText("UTC");
  });

  test("API key input is present in header", async () => {
    await expect(base.apiKeyInput).toBeVisible();
    await expect(base.apiKeyInput).toHaveAttribute("type", "password");
  });

  test("API key input accepts text and masks it", async () => {
    await base.apiKeyInput.fill("test-secret-key");
    await expect(base.apiKeyInput).toHaveValue("test-secret-key");
    // Type=password means value is masked in the UI
    await expect(base.apiKeyInput).toHaveAttribute("type", "password");
  });

  // ── Sidebar tabs ────────────────────────────────────────────────────────
  const EXPECTED_TABS = [
    "Zones", "Sensors", "Signals", "Replay", "Intel",
    "Routes", "Dark Ships", "Briefing", "Extract", "Diff",
    "Cameras", "Status", "Cases",
  ];

  for (const tab of EXPECTED_TABS) {
    test(`sidebar tab "${tab}" is visible and clickable`, async () => {
      const btn = base.sidebar.locator(`.sidebar-btn:has-text("${tab}")`);
      await expect(btn).toBeVisible();
      await btn.click();
      await expect(btn).toHaveClass(/sidebar-btn--active/);
    });
  }

  // ── Sidebar switching ───────────────────────────────────────────────────
  test("switching between tabs deactivates previous tab", async () => {
    // Click Zones first
    const zonesBtn = base.sidebar.locator('.sidebar-btn:has-text("Zones")');
    await zonesBtn.click();
    await expect(zonesBtn).toHaveClass(/sidebar-btn--active/);

    // Switch to Sensors
    const sensorsBtn = base.sidebar.locator('.sidebar-btn:has-text("Sensors")');
    await sensorsBtn.click();
    await expect(sensorsBtn).toHaveClass(/sidebar-btn--active/);
    await expect(zonesBtn).not.toHaveClass(/sidebar-btn--active/);
  });

  test("only one sidebar tab is active at a time", async () => {
    for (const tab of ["Signals", "Intel", "Routes"]) {
      await base.openPanel(tab);
    }
    // Only Routes should be active
    const activeBtns = base.sidebar.locator(".sidebar-btn--active");
    await expect(activeBtns).toHaveCount(1);
  });

  // ── View mode toggle ───────────────────────────────────────────────────
  test("2D/3D toggle buttons are visible", async () => {
    await expect(base.btn2D).toBeVisible();
    await expect(base.btn3D).toBeVisible();
  });

  test("switching to 2D shows map container", async () => {
    await base.switchTo2D();
    await expect(base.mapContainer).toBeVisible();
  });

  test("switching to 3D shows globe container", async () => {
    await base.switchTo3D();
    await expect(base.globeContainer).toBeVisible();
  });

  test("toggling 3D → 2D → 3D works without errors", async () => {
    await base.switchTo3D();
    await expect(base.globeContainer).toBeVisible();
    await base.switchTo2D();
    await expect(base.mapContainer).toBeVisible();
    await base.switchTo3D();
    await expect(base.globeContainer).toBeVisible();
  });
});
