import { test, expect } from "./fixtures";
import { HealthDashboardPage } from "./pages";

/**
 * System Health / Status dashboard — sections, refresh, banner,
 * connectors, alerts, and edge cases.
 */

test.describe("HealthDashboard — core sections", () => {
  let hd: HealthDashboardPage;

  test.beforeEach(async ({ page }) => {
    hd = new HealthDashboardPage(page);
    await hd.open();
    await hd.waitForData();
  });

  test("page root is visible", async () => {
    await expect(hd.pageRoot).toBeVisible();
  });

  test("heading says System Health", async () => {
    await expect(hd.heading).toContainText("System Health");
  });

  test("status banner is present", async () => {
    // Banner may show loading or actual status
    await expect(hd.banner).toBeVisible();
  });

  test("infrastructure section is present", async () => {
    await expect(hd.infrastructure).toBeVisible();
  });

  test("satellite providers section is present", async () => {
    await expect(hd.providers).toBeVisible();
  });

  test("circuit breakers section is present", async () => {
    await expect(hd.circuitBreakers).toBeVisible();
  });

  test("data connectors section is present", async () => {
    await expect(hd.connectors).toBeVisible();
  });

  test("alerts section is present", async () => {
    await expect(hd.alerts).toBeVisible();
  });
});

test.describe("HealthDashboard — refresh", () => {
  test("refresh button is visible", async ({ page }) => {
    const hd = new HealthDashboardPage(page);
    await hd.open();
    await hd.waitForData();
    await expect(hd.refreshBtn).toBeVisible();
  });

  test("clicking refresh does not crash the dashboard", async ({ page }) => {
    const hd = new HealthDashboardPage(page);
    await hd.open();
    await hd.waitForData();
    await hd.refresh();
    // Dashboard should remain visible after refresh
    await expect(hd.pageRoot).toBeVisible({ timeout: 10_000 });
  });

  test("multiple rapid refreshes do not crash", async ({ page }) => {
    const hd = new HealthDashboardPage(page);
    await hd.open();
    await hd.waitForData();
    await hd.refresh();
    await hd.refresh();
    await hd.refresh();
    await expect(hd.pageRoot).toBeVisible();
  });
});

test.describe("HealthDashboard — does not hide map", () => {
  test("switching to Status replaces map with health page", async ({ page }) => {
    const hd = new HealthDashboardPage(page);
    await hd.goto();
    // Map should be visible initially
    await expect(
      hd.mapContainer.or(hd.globeContainer).first(),
    ).toBeVisible();

    // Switch to Status
    await hd.openPanel("Status");
    await expect(hd.pageRoot).toBeVisible({ timeout: 10_000 });
  });

  test("returning from Status restores map view", async ({ page }) => {
    const hd = new HealthDashboardPage(page);
    await hd.open();
    await hd.waitForData();

    // Switch back to map panel
    await hd.openPanel("Zones");
    await expect(
      hd.mapContainer.or(hd.globeContainer).first(),
    ).toBeVisible({ timeout: 10_000 });
  });
});
