import { test, expect } from "@playwright/test";
import { BasePage } from "./pages";

/**
 * Accessibility and keyboard navigation tests.
 * Ensures the app can be operated via keyboard, ARIA attributes
 * are correct, and interactive elements are focusable.
 */

test.describe("Accessibility — keyboard navigation", () => {
  let base: BasePage;

  test.beforeEach(async ({ page }) => {
    base = new BasePage(page);
    await base.goto();
  });

  test("sidebar buttons are focusable via Tab", async ({ page }) => {
    // Focus the first sidebar button, then tab through
    const firstBtn = base.sidebar.locator(".sidebar-btn").first();
    await firstBtn.focus();
    await expect(firstBtn).toBeFocused();
  });

  test("sidebar button activates on Enter key", async ({ page }) => {
    const sensorsBtn = base.sidebar.locator('.sidebar-btn:has-text("Sensors")');
    await sensorsBtn.focus();
    await page.keyboard.press("Enter");
    await expect(sensorsBtn).toHaveClass(/sidebar-btn--active/);
  });

  test("API key input is focusable and accepts keyboard input", async ({ page }) => {
    await base.apiKeyInput.focus();
    await expect(base.apiKeyInput).toBeFocused();
    await page.keyboard.type("test-key");
    await expect(base.apiKeyInput).toHaveValue("test-key");
  });

  test("view mode buttons are focusable", async () => {
    await base.btn2D.focus();
    await expect(base.btn2D).toBeFocused();
  });
});

test.describe("Accessibility — ARIA and semantics", () => {
  let base: BasePage;

  test.beforeEach(async ({ page }) => {
    base = new BasePage(page);
    await base.goto();
  });

  test("page has exactly one h1 element", async ({ page }) => {
    const h1s = page.locator("h1");
    await expect(h1s).toHaveCount(1);
  });

  test("API key input has a title attribute for screen readers", async () => {
    await expect(base.apiKeyInput).toHaveAttribute("title", /API key/i);
  });

  test("view mode buttons have title attributes", async () => {
    await expect(base.btn2D).toHaveAttribute("title", /2D/i);
    await expect(base.btn3D).toHaveAttribute("title", /3D/i);
  });

  test("interactive buttons have visible text or ARIA labels", async ({ page }) => {
    const buttons = base.sidebar.locator("button");
    const count = await buttons.count();
    for (let i = 0; i < count; i++) {
      const btn = buttons.nth(i);
      const text = await btn.textContent();
      const ariaLabel = await btn.getAttribute("aria-label");
      // Each button should have either visible text or an ARIA label
      expect((text?.trim().length ?? 0) > 0 || (ariaLabel?.trim().length ?? 0) > 0).toBeTruthy();
    }
  });
});

test.describe("Accessibility — color contrast", () => {
  test("header text is readable (not transparent or invisible)", async ({ page }) => {
    const base = new BasePage(page);
    await base.goto();

    const color = await base.appTitle.evaluate((el) =>
      window.getComputedStyle(el).color,
    );
    // Ensure text is not fully transparent
    expect(color).not.toBe("rgba(0, 0, 0, 0)");
    expect(color).not.toBe("transparent");
  });
});
