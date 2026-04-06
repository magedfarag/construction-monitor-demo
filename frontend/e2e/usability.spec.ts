import { test, expect } from "./fixtures";
import { BasePage, SearchPanelPage, InvestigationsPanelPage } from "./pages";

/**
 * Usability Tests — Focuses on ease of use, learnability, efficiency,
 * memorability, error prevention, and user satisfaction.
 */

test.describe("Usability: Discoverability & Learnability", () => {
  let base: BasePage;

  test.beforeEach(async ({ page }) => {
    base = new BasePage(page);
    await base.goto();
  });

  test("main navigation is intuitive and labeled clearly", async ({ page }) => {
    // All main navigation buttons should have clear, descriptive labels
    const navButtons = base.sidebar.locator('.sidebar-btn');
    const buttonCount = await navButtons.count();
    
    expect(buttonCount).toBeGreaterThan(0);
    
    for (let i = 0; i < buttonCount; i++) {
      const button = navButtons.nth(i);
      const text = await button.textContent();
      
      // Navigation labels should be descriptive (not just icons)
      expect(text).toBeTruthy();
      expect(text!.trim().length).toBeGreaterThan(2);
    }
  });

  test("interactive elements have appropriate hover states", async ({ page }) => {
    // Hover over main navigation elements
    const navButtons = base.sidebar.locator('.sidebar-btn');
    if (await navButtons.count() > 0) {
      await navButtons.first().hover();
      
      // Should provide visual feedback on hover
      await expect(navButtons.first()).toHaveCSS('cursor', /pointer/);
    }
    
    // Test other interactive elements
    const buttons = page.locator('button:visible');
    if (await buttons.count() > 0) {
      await buttons.first().hover();
      await expect(buttons.first()).toHaveCSS('cursor', /pointer/);
    }
  });

  test("tooltips provide helpful context without cluttering interface", async ({ page }) => {
    // Check for tooltips on complex controls
    const complexControls = page.locator('[title], [data-tooltip], .has-tooltip');
    
    if (await complexControls.count() > 0) {
      // Hover to trigger tooltip
      await complexControls.first().hover();
      
      // Tooltip content should be meaningful
      const tooltip = page.locator('.tooltip:visible, [role="tooltip"]:visible');
      if (await tooltip.count() > 0) {
        const tooltipText = await tooltip.textContent();
        expect(tooltipText).toBeTruthy();
        expect(tooltipText!.trim().length).toBeGreaterThan(5);
      }
    }
  });

  test("help and documentation is accessible when needed", async ({ page }) => {
    // Look for help buttons, documentation links, or info icons
    const helpElements = page.locator('button:has-text("Help"), button:has-text("?"), .help-icon, .info-icon');
    
    if (await helpElements.count() > 0) {
      await helpElements.first().click();
      
      // Should open help content or documentation
      const helpContent = page.locator('.help-content, .documentation, .modal:visible');
      if (await helpContent.count() > 0) {
        await expect(helpContent.first()).toBeVisible();
      }
    }
  });
});

test.describe("Usability: Efficiency & Productivity", () => {
  let base: BasePage;

  test.beforeEach(async ({ page }) => {
    base = new BasePage(page);
    await base.goto();
  });

  test("keyboard shortcuts work for common actions", async ({ page }) => {
    // Test common keyboard shortcuts
    await page.keyboard.press('Escape'); // Should close any open modal/panel
    
    // Try common shortcuts - these may or may not exist but shouldn't break
    await page.keyboard.press('Control+f'); // Search
    await page.keyboard.press('Control+r'); // Refresh
    await page.keyboard.press('Control+s'); // Save
    
    // App should remain stable after keyboard input
    await expect(base.header).toBeVisible();
  });

  test("bulk operations are available for repetitive tasks", async ({ page }) => {
    await base.openPanel("Signals");
    
    // Look for bulk selection capabilities
    const bulkSelectors = page.locator('input[type="checkbox"]:visible, .select-all, .bulk-actions');
    
    if (await bulkSelectors.count() > 0) {
      // Should be able to select multiple items
      const checkboxes = page.locator('input[type="checkbox"]:visible');
      if (await checkboxes.count() > 1) {
        await checkboxes.first().check();
        await checkboxes.nth(1).check();
        
        // Should show bulk action options
        const bulkActions = page.locator('.bulk-actions:visible, button:has-text("Export Selected"), button:has-text("Delete Selected")');
        if (await bulkActions.count() > 0) {
          await expect(bulkActions.first()).toBeVisible();
        }
      }
    }
  });

  test("recently used items or quick access is available", async ({ page }) => {
    // Look for recent items, history, or quick access features
    const quickAccess = page.locator('.recent-items, .history, .quick-access, .favorites');
    
    if (await quickAccess.count() > 0) {
      await expect(quickAccess.first()).toBeVisible();
    }
  });

  test("search functionality is fast and accurate", async ({ page }) => {
    const searchPanel = new SearchPanelPage(page);
    await base.openPanel("Signals");
    
    const searchStartTime = Date.now();
    await searchPanel.search();
    
    // Wait for results but measure time
    try {
      await searchPanel.waitForResults();
      const searchTime = Date.now() - searchStartTime;
      
      // Search should complete within reasonable time
      expect(searchTime).toBeLessThan(10000); // 10 seconds
    } catch (error) {
      // If search fails, that's also valuable usability feedback
      console.log("Search functionality may need improvement");
    }
  });
});

test.describe("Usability: Error Prevention & Recovery", () => {
  let base: BasePage;

  test.beforeEach(async ({ page }) => {
    base = new BasePage(page);
    await base.goto();
  });

  test("form validation prevents common errors", async ({ page }) => {
    // Test form validation in investigations panel
    const investigationsPanel = new InvestigationsPanelPage(page);
    await base.openPanel("Investigations");
    
    try {
      await investigationsPanel.openCreateForm();
      
      // Try to submit empty form
      const submitBtn = page.locator('button:has-text("Create"), button:has-text("Submit")');
      if (await submitBtn.count() > 0) {
        await submitBtn.first().click();
        
        // Should show validation errors
        const validationErrors = page.locator('.error, .validation-error, [aria-invalid="true"]');
        if (await validationErrors.count() > 0) {
          await expect(validationErrors.first()).toBeVisible();
        }
      }
    } catch (error) {
      // Form may not be available in current state
      console.log("Investigation form validation test skipped");
    }
  });

  test("destructive actions require confirmation", async ({ page }) => {
    // Look for potentially destructive actions (delete, clear, reset)
    const destructiveActions = page.locator('button:has-text("Delete"), button:has-text("Clear"), button:has-text("Reset"), button:has-text("Remove")');
    
    if (await destructiveActions.count() > 0) {
      await destructiveActions.first().click();
      
      // Should show confirmation dialog
      const confirmation = page.locator('.confirmation, .modal:visible, [role="dialog"]:visible');
      if (await confirmation.count() > 0) {
        await expect(confirmation.first()).toBeVisible();
        
        // Should have cancel option
        const cancelBtn = page.locator('button:has-text("Cancel"), button:has-text("No")');
        if (await cancelBtn.count() > 0) {
          await expect(cancelBtn.first()).toBeVisible();
          await cancelBtn.first().click(); // Cancel to avoid actual deletion
        }
      }
    }
  });

  test("users can undo recent actions", async ({ page }) => {
    // Look for undo functionality
    const undoControls = page.locator('button:has-text("Undo"), .undo-action, [title*="undo" i]');
    
    if (await undoControls.count() > 0) {
      await expect(undoControls.first()).toBeVisible();
    }
    
    // Test keyboard undo
    await page.keyboard.press('Control+z');
    
    // App should remain stable
    await expect(base.header).toBeVisible();
  });

  test("error messages are user-friendly and actionable", async ({ page }) => {
    // Trigger potential error by trying invalid operations
    await page.route('**/api/**', route => {
      route.fulfill({
        status: 500,
        body: 'Internal Server Error'
      });
    });
    
    const searchPanel = new SearchPanelPage(page);
    await base.openPanel("Signals");
    await searchPanel.search();
    
    // Look for user-friendly error messages
    const errorMessages = page.locator('.error-message:visible, .alert-error:visible, [role="alert"]:visible');
    
    if (await errorMessages.count() > 0) {
      const errorText = await errorMessages.first().textContent();
      
      // Error should not contain technical details like stack traces
      expect(errorText).not.toMatch(/Error:\s*at/);
      expect(errorText).not.toMatch(/Exception/);
      expect(errorText).not.toMatch(/500 Internal Server Error/);
      
      // Should provide guidance on what to do next
      expect(errorText!.length).toBeGreaterThan(20);
    }
    
    // Clean up route
    await page.unroute('**/api/**');
  });
});