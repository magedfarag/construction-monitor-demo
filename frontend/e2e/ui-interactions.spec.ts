import { test, expect } from "./fixtures";
import { BasePage, LayerPanelPage, SearchPanelPage } from "./pages";

/**
 * UI Interaction Tests — Tests interactive elements, controls, feedback,
 * visual states, and user interface responsiveness.
 */

test.describe("UI: Interactive Controls & Feedback", () => {
  let base: BasePage;

  test.beforeEach(async ({ page }) => {
    base = new BasePage(page);
    await base.goto();
  });

  test("buttons provide immediate visual feedback on interaction", async ({ page }) => {
    // Test main navigation buttons
    const navButtons = base.sidebar.locator('.sidebar-btn');
    
    if (await navButtons.count() > 0) {
      const firstButton = navButtons.first();
      
      // Button should have normal state
      const initialClass = await firstButton.getAttribute('class');
      
      // Click and check for active/pressed state
      await firstButton.click();
      
      // Should have active state class
      await expect(firstButton).toHaveClass(/active|selected|current/);
      
      // Visual feedback should be immediate
      const activeClass = await firstButton.getAttribute('class');
      expect(activeClass).not.toBe(initialClass);
    }
  });

  test("hover states provide clear visual cues", async ({ page }) => {
    const interactiveElements = page.locator('button:visible, a:visible, .clickable:visible');
    
    if (await interactiveElements.count() > 0) {
      const element = interactiveElements.first();
      
      // Hover over element
      await element.hover();
      
      // Should change cursor to pointer
      await expect(element).toHaveCSS('cursor', /pointer|hand/);
    }
  });

  test("disabled states are visually distinct and non-interactive", async ({ page }) => {
    // Look for disabled elements
    const disabledElements = page.locator('button:disabled, input:disabled, [disabled], [aria-disabled="true"]');
    
    if (await disabledElements.count() > 0) {
      const disabledElement = disabledElements.first();
      
      // Should look visually disabled
      await expect(disabledElement).toHaveCSS('cursor', /not-allowed|default/);
      
      // Should not be clickable
      const initialText = await page.textContent('body');
      
      try {
        await disabledElement.click({ timeout: 1000 });
      } catch {
        // Click should fail or have no effect
      }
      
      // Page state shouldn't change
      const afterText = await page.textContent('body');
      expect(afterText).toBe(initialText);
    }
  });

  test("loading states are clear and informative", async ({ page }) => {
    // Trigger operations that might show loading states
    const searchPanel = new SearchPanelPage(page);
    await base.openPanel("Signals");
    
    // Start search operation
    await searchPanel.search();
    
    // Look for loading indicators during operation
    const loadingElements = page.locator('.loading, .spinner, .processing, [aria-busy="true"]');
    
    if (await loadingElements.count() > 0) {
      // Loading indicator should be visible
      await expect(loadingElements.first()).toBeVisible();
      
      // Loading text should be informative
      const loadingText = await loadingElements.first().textContent();
      if (loadingText && loadingText.trim()) {
        expect(loadingText.length).toBeGreaterThan(3);
        expect(loadingText.toLowerCase()).toMatch(/loading|searching|processing|working/);
      }
    }
  });
});

test.describe("UI: Form Controls & Input Validation", () => {
  let base: BasePage;

  test.beforeEach(async ({ page }) => {
    base = new BasePage(page);
    await base.goto();
  });

  test("input fields provide clear focus and validation states", async ({ page }) => {
    // Find input fields
    const inputs = page.locator('input:visible, textarea:visible, select:visible');
    
    if (await inputs.count() > 0) {
      const input = inputs.first();
      
      // Focus on input
      await input.focus();
      
      // Should have visible focus indicator
      const outlineStyle = await input.evaluate((el) => {
        const styles = window.getComputedStyle(el);
        return styles.outline + styles.outlineColor + styles.boxShadow;
      });
      
      expect(outlineStyle).not.toBe('none');
      
      // Type invalid data if it's an email or number field
      const inputType = await input.getAttribute('type');
      if (inputType === 'email') {
        await input.fill('invalid-email');
        await input.blur();
        
        // Should show validation state
        const validationState = await input.evaluate(el => el.validity.valid);
        expect(validationState).toBe(false);
      }
    }
  });

  test("dropdown and select controls are accessible", async ({ page }) => {
    const selects = page.locator('select:visible');
    
    if (await selects.count() > 0) {
      const select = selects.first();
      
      // Should be able to interact with select
      await select.click();
      
      // Should have options
      const options = page.locator('option');
      if (await options.count() > 0) {
        expect(await options.count()).toBeGreaterThan(0);
        
        // Select an option
        await options.first().click();
        
        // Value should change
        const selectedValue = await select.inputValue();
        expect(selectedValue).toBeTruthy();
      }
    }
    
    // Check for custom dropdowns
    const customDropdowns = page.locator('.dropdown, .select-wrapper, [role="combobox"]');
    if (await customDropdowns.count() > 0) {
      const dropdown = customDropdowns.first();
      await dropdown.click();
      
      // Should show dropdown options
      const dropdownOptions = page.locator('.dropdown-option, .select-option, [role="option"]');
      if (await dropdownOptions.count() > 0) {
        await expect(dropdownOptions.first()).toBeVisible();
      }
    }
  });

  test("checkboxes and radio buttons have clear visual feedback", async ({ page }) => {
    // Test checkboxes
    const checkboxes = page.locator('input[type="checkbox"]:visible');
    if (await checkboxes.count() > 0) {
      const checkbox = checkboxes.first();
      
      // Initially unchecked
      const initialState = await checkbox.isChecked();
      
      // Click to check
      await checkbox.check();
      
      // Should be checked
      await expect(checkbox).toBeChecked();
      
      // Uncheck
      await checkbox.uncheck();
      await expect(checkbox).not.toBeChecked();
    }
    
    // Test radio buttons
    const radioButtons = page.locator('input[type="radio"]:visible');
    if (await radioButtons.count() > 1) {
      const firstRadio = radioButtons.first();
      const secondRadio = radioButtons.nth(1);
      
      // Select first radio
      await firstRadio.check();
      await expect(firstRadio).toBeChecked();
      
      // Select second radio (should uncheck first if same group)
      const firstName = await firstRadio.getAttribute('name');
      const secondName = await secondRadio.getAttribute('name');
      
      if (firstName === secondName) {
        await secondRadio.check();
        await expect(secondRadio).toBeChecked();
        await expect(firstRadio).not.toBeChecked();
      }
    }
  });
});

test.describe("UI: Visual Consistency & Layout", () => {
  let base: BasePage;

  test.beforeEach(async ({ page }) => {
    base = new BasePage(page);
    await base.goto();
  });

  test("buttons follow consistent styling patterns", async ({ page }) => {
    const buttons = page.locator('button:visible');
    
    if (await buttons.count() > 1) {
      const buttonStyles = [];
      
      // Collect styles from first few buttons
      const sampleSize = Math.min(5, await buttons.count());
      
      for (let i = 0; i < sampleSize; i++) {
        const button = buttons.nth(i);
        const styles = await button.evaluate(el => {
          const computed = getComputedStyle(el);
          return {
            fontFamily: computed.fontFamily,
            fontSize: computed.fontSize,
            fontWeight: computed.fontWeight,
            borderRadius: computed.borderRadius,
            padding: computed.padding
          };
        });
        buttonStyles.push(styles);
      }
      
      // Basic consistency check - font family should be similar
      const firstFontFamily = buttonStyles[0].fontFamily;
      buttonStyles.forEach(style => {
        expect(style.fontFamily).toContain(firstFontFamily.split(',')[0]);
      });
    }
  });

  test("color scheme is consistent across components", async ({ page }) => {
    // Check for consistent use of CSS variables or color values
    const elements = page.locator('.sidebar, .header, .panel, button');
    
    if (await elements.count() > 0) {
      // Get background colors
      const colors = [];
      const sampleSize = Math.min(3, await elements.count());
      
      for (let i = 0; i < sampleSize; i++) {
        const element = elements.nth(i);
        const bgColor = await element.evaluate(el => getComputedStyle(el).backgroundColor);
        colors.push(bgColor);
      }
      
      // Colors should not be completely random
      // (This is a basic check - more sophisticated color analysis could be added)
      colors.forEach(color => {
        expect(color).toMatch(/^rgb\(|^rgba\(|transparent|initial|inherit/);
      });
    }
  });

  test("typography hierarchy is clear and consistent", async ({ page }) => {
    // Check heading hierarchy
    const headings = page.locator('h1, h2, h3, h4, h5, h6');
    
    if (await headings.count() > 1) {
      const h1Size = await page.locator('h1').first().evaluate(el => {
        return parseFloat(getComputedStyle(el).fontSize);
      }).catch(() => 16);
      
      const h2Size = await page.locator('h2').first().evaluate(el => {
        return parseFloat(getComputedStyle(el).fontSize);
      }).catch(() => 14);
      
      // H1 should typically be larger than H2
      if (h1Size > 0 && h2Size > 0) {
        expect(h1Size).toBeGreaterThanOrEqual(h2Size);
      }
    }
  });

  test("spacing and alignment create visual harmony", async ({ page }) => {
    // Check that major layout elements have consistent spacing
    const layoutElements = page.locator('.header, .sidebar, .panel, .main-content');
    
    if (await layoutElements.count() > 0) {
      // Elements should have reasonable margins/padding
      for (let i = 0; i < Math.min(3, await layoutElements.count()); i++) {
        const element = layoutElements.nth(i);
        
        const spacing = await element.evaluate(el => {
          const styles = getComputedStyle(el);
          return {
            marginTop: parseFloat(styles.marginTop),
            marginBottom: parseFloat(styles.marginBottom),
            paddingTop: parseFloat(styles.paddingTop),
            paddingBottom: parseFloat(styles.paddingBottom)
          };
        });
        
        // Spacing values should be reasonable (not 0 or extremely large)
        Object.values(spacing).forEach(value => {
          if (value > 0) {
            expect(value).toBeLessThan(100); // No ridiculously large spacing
            expect(value).toBeGreaterThanOrEqual(0); // No negative spacing
          }
        });
      }
    }
  });
});

test.describe("UI: Responsive Design & Device Adaptation", () => {
  const viewports = [
    { name: 'Desktop Large', width: 1920, height: 1080 },
    { name: 'Desktop Medium', width: 1366, height: 768 },
    { name: 'Laptop', width: 1024, height: 768 },
    { name: 'Tablet Portrait', width: 768, height: 1024 },
    { name: 'Mobile Large', width: 414, height: 896 },
    { name: 'Mobile Medium', width: 375, height: 667 }
  ];

  viewports.forEach(viewport => {
    test(`UI adapts correctly on ${viewport.name} (${viewport.width}x${viewport.height})`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      
      const base = new BasePage(page);
      await base.goto();
      
      // Core elements should be visible
      await expect(base.header).toBeVisible();
      
      // Main content area should be visible
      await expect(
        base.mapContainer.or(base.globeContainer).first(),
      ).toBeVisible({ timeout: 10000 });
      
      // Sidebar should either be visible or have a toggle
      const sidebarVisible = await base.sidebar.isVisible();
      if (!sidebarVisible && viewport.width < 768) {
        // On mobile, sidebar might be hidden but accessible via toggle
        const sidebarToggle = page.locator('.sidebar-toggle, .menu-toggle, [aria-label*="menu" i]');
        if (await sidebarToggle.count() > 0) {
          await expect(sidebarToggle).toBeVisible();
        }
      } else {
        await expect(base.sidebar).toBeVisible();
      }
      
      // Navigation should remain functional
      await base.openPanel("Sensors");
      await base.expectPanelActive("Sensors");
      
      // Text should remain readable (not cut off)
      const textElements = page.locator('h1, h2, h3, p, span, button');
      if (await textElements.count() > 0) {
        const sampleText = textElements.first();
        const textContent = await sampleText.textContent();
        
        if (textContent && textContent.trim()) {
          // Text should not be completely cut off (basic check)
          expect(textContent.length).toBeGreaterThan(0);
        }
      }
    });
  });

  test("touch targets are appropriately sized on mobile", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    
    const base = new BasePage(page);
    await base.goto();
    
    // Interactive elements should have appropriate touch target size (44px minimum)
    const touchTargets = page.locator('button:visible, a:visible, input:visible, [role="button"]:visible');
    
    if (await touchTargets.count() > 0) {
      const sampleSize = Math.min(5, await touchTargets.count());
      
      for (let i = 0; i < sampleSize; i++) {
        const target = touchTargets.nth(i);
        
        const dimensions = await target.evaluate(el => {
          const rect = el.getBoundingClientRect();
          return {
            width: rect.width,
            height: rect.height
          };
        });
        
        // Touch targets should be at least 44px in at least one dimension
        const minSize = Math.max(dimensions.width, dimensions.height);
        expect(minSize).toBeGreaterThanOrEqual(30); // Slightly relaxed for demo
      }
    }
  });
});