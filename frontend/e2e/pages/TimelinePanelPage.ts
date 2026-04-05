import { type Page, type Locator, expect } from "@playwright/test";
import { BasePage } from "./BasePage";

export class TimelinePanelPage extends BasePage {
  readonly panel: Locator;
  readonly heading: Locator;
  readonly expandToggle: Locator;
  readonly preset24h: Locator;
  readonly preset7d: Locator;
  readonly preset30d: Locator;
  readonly startInput: Locator;
  readonly endInput: Locator;

  constructor(page: Page) {
    super(page);
    this.panel = page.locator('[data-testid="timeline-panel"]');
    this.heading = this.panel.locator("h3");
    this.expandToggle = this.panel.locator('button:has-text("▼"), button:has-text("▲")');
    this.preset24h = this.panel.locator('button:has-text("24h")');
    this.preset7d = this.panel.locator('button:has-text("7d")');
    this.preset30d = this.panel.locator('button:has-text("30d")');
    this.startInput = this.panel.locator('input[type="datetime-local"]').first();
    this.endInput = this.panel.locator('input[type="datetime-local"]').last();
  }

  async expectPanelVisible() {
    await expect(this.panel).toBeVisible();
  }

  /** Ensure timeline is in expanded state (showing chart and inputs) */
  async expand() {
    // "▲" button means currently collapsed → click to expand
    const expandBtn = this.panel.locator('button:has-text("▲")');
    if (await expandBtn.isVisible()) {
      await expandBtn.click();
    }
    // "▼" means already expanded — do nothing
  }

  /** Ensure timeline is in collapsed state */
  async collapse() {
    // "▼" button means currently expanded → click to collapse
    const collapseBtn = this.panel.locator('button:has-text("▼")');
    if (await collapseBtn.isVisible()) {
      await collapseBtn.click();
    }
  }

  async selectPreset(preset: "24h" | "7d" | "30d") {
    const btn = { "24h": this.preset24h, "7d": this.preset7d, "30d": this.preset30d }[preset];
    await btn.click();
  }

  async setStartDate(value: string) {
    await this.startInput.fill(value);
  }

  async setEndDate(value: string) {
    await this.endInput.fill(value);
  }
}
