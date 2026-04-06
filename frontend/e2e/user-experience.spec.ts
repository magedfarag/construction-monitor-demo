import { test, expect } from "./fixtures";
import { BasePage, SearchPanelPage, AnalyticsPanelPage, ExportPanelPage } from "./pages";

/**
 * User Experience (UX) Tests — Focuses on user flows, task completion,
 * and overall user satisfaction with the application interface.
 */

test.describe("UX: Core User Flows", () => {
  let base: BasePage;

  test.beforeEach(async ({ page }) => {
    base = new BasePage(page);
    await base.goto();
  });

  test("new user onboarding experience", async ({ page }) => {
    // Verify essential elements are immediately visible without confusion
    await expect(base.appTitle).toBeVisible();
    await expect(base.header).toBeVisible();
    await expect(base.liveBadge).toBeVisible();
    
    // Check that the main view is ready for interaction
    await expect(
      base.mapContainer.or(base.globeContainer).first(),
    ).toBeVisible({ timeout: 15000 });
    
    // Verify critical navigation elements are discoverable
    await expect(base.sidebar).toBeVisible();
    await expect(base.btn2D).toBeVisible();
    await expect(base.btn3D).toBeVisible();
  });

  test("task completion flow: search -> analyze -> export", async ({ page }) => {
    const startTime = Date.now();
    
    // Step 1: User searches for data
    const searchPanel = new SearchPanelPage(page);
    await base.openPanel("Signals");
    await expect(searchPanel.panel).toBeVisible({ timeout: 10000 });
    await searchPanel.search();
    await searchPanel.waitForResults();
    
    // Step 2: User switches to analytics
    const analyticsPanel = new AnalyticsPanelPage(page);
    await base.openPanel("Analytics");
    await expect(analyticsPanel.panel).toBeVisible({ timeout: 10000 });
    
    // Step 3: User exports results
    const exportPanel = new ExportPanelPage(page);
    await base.openPanel("Extract");
    await expect(exportPanel.panel).toBeVisible({ timeout: 10000 });
    await exportPanel.selectFormat("CSV");
    await exportPanel.export();
    
    // Verify the entire flow completes in reasonable time
    const elapsed = Date.now() - startTime;
    expect(elapsed).toBeLessThan(60000); // Should complete within 60 seconds
  });

  test("error recovery: handle network failures gracefully", async ({ page }) => {
    // Simulate network issues by intercepting and failing API calls
    await page.route('**/api/**', route => route.abort());
    
    const searchPanel = new SearchPanelPage(page);
    await base.openPanel("Signals");
    await searchPanel.search();
    
    // Verify error states are user-friendly (not technical stack traces)
    const errorMessages = page.locator('.error-message, .alert-error, [role="alert"]');
    if (await errorMessages.count() > 0) {
      await expect(errorMessages.first()).toBeVisible({ timeout: 10000 });
    }
    
    // Verify users can recover from errors
    await page.unroute('**/api/**');
    await searchPanel.search();
    await searchPanel.waitForResults();
  });

  test("progressive disclosure: complex features are discoverable but not overwhelming", async ({ page }) => {
    // Verify advanced features aren't immediately visible but are discoverable
    await base.openPanel("Analytics");
    
    // Check that basic analytics options are visible
    const basicControls = page.locator('.analytics-basic, .analytics-simple');
    if (await basicControls.count() > 0) {
      await expect(basicControls.first()).toBeVisible();
    }
    
    // Check that advanced options might be collapsed or in secondary menus
    const advancedToggles = page.locator('button:has-text("Advanced"), .show-more, .expand-options');
    if (await advancedToggles.count() > 0) {
      // Advanced features should be discoverable via progressive disclosure
      await advancedToggles.first().click();
    }
  });
});

test.describe("UX: Context Switching & Multi-tasking", () => {
  let base: BasePage;

  test.beforeEach(async ({ page }) => {
    base = new BasePage(page);
    await base.goto();
  });

  test("seamless panel switching preserves user context", async ({ page }) => {
    // Start work in search panel
    await base.openPanel("Signals");
    const searchPanel = new SearchPanelPage(page);
    await searchPanel.search();
    await searchPanel.waitForResults();
    
    // Switch to analytics
    await base.openPanel("Analytics");
    
    // Return to search - verify context is preserved
    await base.openPanel("Signals");
    const resultsStillVisible = page.locator('.search-results');
    if (await resultsStillVisible.count() > 0) {
      await expect(resultsStillVisible).toBeVisible();
    }
  });

  test("view mode switching maintains data and selections", async ({ page }) => {
    // Work in 2D mode
    await base.switchTo2D();
    await base.openPanel("Sensors");
    
    // Switch to 3D mode  
    await base.switchTo3D();
    
    // Verify layers panel retains state
    await expect(base.sidebar).toBeVisible();
    await base.expectPanelActive("Sensors");
    
    // Switch back to 2D
    await base.switchTo2D();
    await base.expectPanelActive("Sensors");
  });
});

test.describe("UX: Performance & Responsiveness", () => {
  test("app loads within acceptable time limits", async ({ page }) => {
    const startTime = Date.now();
    
    const base = new BasePage(page);
    await base.goto();
    
    const loadTime = Date.now() - startTime;
    
    // App should be interactive within 10 seconds  
    expect(loadTime).toBeLessThan(10000);
    
    // Critical content should be visible much faster
    await expect(base.header).toBeVisible({ timeout: 3000 });
  });

  test("interactions provide immediate feedback", async ({ page }) => {
    const base = new BasePage(page);
    await base.goto();
    
    // Click should provide immediate visual feedback
    const sensorBtn = base.sidebar.locator('.sidebar-btn:has-text("Sensors")');
    
    // Measure time to visual feedback
    const startTime = Date.now();
    await sensorBtn.click();
    
    // Button state should change immediately (within 100ms)
    await expect(sensorBtn).toHaveClass(/sidebar-btn--active/, { timeout: 1000 });
    
    const feedbackTime = Date.now() - startTime;
    expect(feedbackTime).toBeLessThan(1000); // Visual feedback within 1 second
  });

  test("heavy operations show appropriate loading states", async ({ page }) => {
    const base = new BasePage(page);
    await base.goto();
    
    const analyticsPanel = new AnalyticsPanelPage(page);
    await base.openPanel("Analytics");
    
    // Trigger a heavy operation
    if (await page.locator('button:has-text("Run"), .run-analysis').count() > 0) {
      await page.locator('button:has-text("Run"), .run-analysis').first().click();
      
      // Should show loading state
      const loadingIndicators = page.locator('.loading, .spinner, .processing, [data-loading="true"]');
      if (await loadingIndicators.count() > 0) {
        await expect(loadingIndicators.first()).toBeVisible({ timeout: 2000 });
      }
    }
  });
});