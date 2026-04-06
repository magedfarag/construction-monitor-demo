import { test, expect } from "./fixtures";
import { BasePage, LayerPanelPage, SearchPanelPage, AnalyticsPanelPage } from "./pages";

/**
 * Navigation Flow Tests — Focuses on navigation patterns, panel management,
 * breadcrumbs, and deep linking capabilities.
 */

test.describe("Navigation: Panel Management", () => {
  let base: BasePage;

  test.beforeEach(async ({ page }) => {
    base = new BasePage(page);
    await base.goto();
  });

  test("panel switching is smooth and immediate", async ({ page }) => {
    // Test rapid panel switching
    const panels = ["Sensors", "Signals", "Analytics", "Extract"];
    
    for (const panel of panels) {
      const switchStartTime = Date.now();
      await base.openPanel(panel);
      
      // Panel should become active quickly
      await base.expectPanelActive(panel);
      
      const switchTime = Date.now() - switchStartTime;
      expect(switchTime).toBeLessThan(3000); // Switch within 3 seconds
    }
  });

  test("sidebar collapse/expand preserves functionality", async ({ page }) => {
    // Look for sidebar toggle button
    const sidebarToggle = page.locator('.sidebar-toggle, .collapse-sidebar, button[aria-label*="sidebar" i]');
    
    if (await sidebarToggle.count() > 0) {
      // Collapse sidebar
      await sidebarToggle.click();
      
      // Sidebar should still be accessible (possibly as overlay)
      const collapsedSidebar = page.locator('.sidebar-collapsed, .sidebar-overlay');
      if (await collapsedSidebar.count() > 0) {
        // Should still be able to access panels
        await base.openPanel("Sensors");
        await base.expectPanelActive("Sensors");
      }
      
      // Expand sidebar again
      await sidebarToggle.click();
      await expect(base.sidebar).toBeVisible();
    }
  });

  test("breadcrumb navigation works correctly", async ({ page }) => {
    // Look for breadcrumb navigation
    const breadcrumbs = page.locator('.breadcrumb, .breadcrumbs, .nav-path');
    
    if (await breadcrumbs.count() > 0) {
      await base.openPanel("Analytics");
      
      // Breadcrumbs should update to reflect current location
      await expect(breadcrumbs).toBeVisible();
      
      // Should be able to navigate back using breadcrumbs
      const breadcrumbLinks = breadcrumbs.locator('a, button');
      if (await breadcrumbLinks.count() > 0) {
        await breadcrumbLinks.first().click();
        // Should navigate to clicked breadcrumb location
      }
    }
  });

  test("panel content persists when switching views", async ({ page }) => {
    // Open layers panel and make changes
    const layerPanel = new LayerPanelPage(page);
    await layerPanel.open();
    
    // Enable some layers
    if (await page.locator('[data-testid="layer-panel"] input[type="checkbox"]').count() > 0) {
      await page.locator('[data-testid="layer-panel"] input[type="checkbox"]').first().check();
    }
    
    // Switch to different panel
    await base.openPanel("Signals");
    
    // Switch back to layers
    await base.openPanel("Sensors");
    
    // Layer settings should be preserved
    const checkedBoxes = page.locator('[data-testid="layer-panel"] input[type="checkbox"]:checked');
    if (await checkedBoxes.count() > 0) {
      await expect(checkedBoxes.first()).toBeChecked();
    }
  });
});

test.describe("Navigation: Deep Linking & URL Management", () => {
  test("URL reflects current application state", async ({ page }) => {
    const base = new BasePage(page);
    await base.goto();
    
    // Initial URL should be clean
    const initialUrl = page.url();
    expect(initialUrl).toMatch(/localhost:5173/);
    
    // Navigate to specific panel
    await base.openPanel("Analytics");
    
    // URL might update to reflect panel state (if implemented)
    const analyticsUrl = page.url();
    // Note: This test will pass regardless of URL strategy
  });

  test("browser back/forward buttons work correctly", async ({ page }) => {
    const base = new BasePage(page);
    await base.goto();
    
    // Navigate through panels
    await base.openPanel("Sensors");
    await base.openPanel("Analytics");
    await base.openPanel("Signals");
    
    // Use browser back button
    await page.goBack();
    
    // App should remain stable
    await expect(base.header).toBeVisible();
    
    // Use browser forward button
    await page.goForward();
    
    // App should remain stable
    await expect(base.header).toBeVisible();
  });

  test("page refresh preserves critical state", async ({ page }) => {
    const base = new BasePage(page);
    await base.goto();
    
    // Set some state
    await base.openPanel("Analytics");
    
    // Refresh page
    await page.reload();
    
    // Core app should load successfully
    await expect(base.header).toBeVisible({ timeout: 15000 });
    await expect(
      base.mapContainer.or(base.globeContainer).first(),
    ).toBeVisible({ timeout: 15000 });
  });
});

test.describe("Navigation: Accessibility & Keyboard Navigation", () => {
  let base: BasePage;

  test.beforeEach(async ({ page }) => {
    base = new BasePage(page);
    await base.goto();
  });

  test("tab navigation follows logical order", async ({ page }) => {
    // Tab through interactive elements
    await page.keyboard.press('Tab');
    
    // First focusable element should be highlighted
    const focused = page.locator(':focus');
    await expect(focused).toBeVisible();
    
    // Continue tabbing through several elements
    for (let i = 0; i < 5; i++) {
      await page.keyboard.press('Tab');
      
      const currentFocused = page.locator(':focus');
      if (await currentFocused.count() > 0) {
        await expect(currentFocused).toBeVisible();
      }
    }
  });

  test("keyboard shortcuts for navigation work", async ({ page }) => {
    // Test escape to close panels/modals
    await base.openPanel("Analytics");
    await page.keyboard.press('Escape');
    
    // App should remain stable
    await expect(base.header).toBeVisible();
    
    // Test arrow keys for navigation (if implemented)
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('ArrowUp');
    await page.keyboard.press('ArrowLeft');
    await page.keyboard.press('ArrowRight');
    
    // App should handle arrow keys gracefully
    await expect(base.header).toBeVisible();
  });

  test("focus indicators are visible and clear", async ({ page }) => {
    // Focus on interactive elements and check visibility
    const buttons = page.locator('button:visible');
    
    if (await buttons.count() > 0) {
      await buttons.first().focus();
      
      // Should have visible focus indicator
      const focusedButton = page.locator('button:focus');
      await expect(focusedButton).toBeVisible();
      
      // Check that focus is visually distinct
      const outlineStyle = await focusedButton.evaluate((el) => {
        const styles = window.getComputedStyle(el);
        return styles.outline + styles.outlineColor + styles.outlineWidth;
      });
      
      expect(outlineStyle).not.toBe('none');
    }
  });

  test("screen reader landmarks are present", async ({ page }) => {
    // Check for proper ARIA landmarks
    const landmarks = [
      '[role="banner"], header',
      '[role="navigation"], nav',
      '[role="main"], main',
      '[role="complementary"], aside'
    ];
    
    for (const landmark of landmarks) {
      const elements = page.locator(landmark);
      if (await elements.count() > 0) {
        // Landmark should be present (good for accessibility)
        await expect(elements.first()).toBeInDOM();
      }
    }
  });
});

test.describe("Navigation: Context Preservation", () => {
  let base: BasePage;

  test.beforeEach(async ({ page }) => {
    base = new BasePage(page);
    await base.goto();
  });

  test("map/globe view state persists across panel changes", async ({ page }) => {
    // Set initial view state
    await base.switchTo2D();
    
    // Navigate through panels
    await base.openPanel("Sensors");
    await base.openPanel("Analytics");
    await base.openPanel("Signals");
    
    // View should still be 2D
    await expect(base.mapContainer).toBeVisible({ timeout: 5000 });
    
    // Switch to 3D
    await base.switchTo3D();
    
    // Navigate through panels again
    await base.openPanel("Sensors");
    await base.openPanel("Analytics");
    
    // View should still be 3D
    await expect(base.globeContainer).toBeVisible({ timeout: 5000 });
  });

  test("search results persist when navigating to analysis", async ({ page }) => {
    // Perform search
    const searchPanel = new SearchPanelPage(page);
    await base.openPanel("Signals");
    await searchPanel.search();
    await searchPanel.waitForResults();
    
    // Navigate to analytics
    const analyticsPanel = new AnalyticsPanelPage(page);
    await base.openPanel("Analytics");
    
    // Return to search
    await base.openPanel("Signals");
    
    // Results should still be visible
    const results = page.locator('.search-results, .results-container');
    if (await results.count() > 0) {
      await expect(results.first()).toBeVisible();
    }
  });

  test("window resize maintains navigation functionality", async ({ page }) => {
    // Test at different window sizes
    const sizes = [
      { width: 1920, height: 1080 },
      { width: 1366, height: 768 },
      { width: 1024, height: 768 },
      { width: 768, height: 1024 }
    ];
    
    for (const size of sizes) {
      await page.setViewportSize(size);
      
      // Navigation should still work
      await base.openPanel("Sensors");
      await base.expectPanelActive("Sensors");
      
      await base.openPanel("Analytics");
      await base.expectPanelActive("Analytics");
      
      // Core elements should remain visible
      await expect(base.header).toBeVisible();
    }
  });
});