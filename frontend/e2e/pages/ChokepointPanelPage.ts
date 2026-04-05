import { type Page, type Locator, expect } from "@playwright/test";
import { BasePage } from "./BasePage";

export class ChokepointPanelPage extends BasePage {
  readonly panel: Locator;
  readonly heading: Locator;
  readonly chokepointItems: Locator;

  constructor(page: Page) {
    super(page);
    this.panel = page.locator('[data-testid="chokepoint-panel"]');
    this.heading = this.panel.locator("h3");
    this.chokepointItems = this.panel.locator("li, .chokepoint-item");
  }

  async open() {
    await this.goto();
    await this.openPanel("Routes");
    await expect(this.panel).toBeVisible({ timeout: 10_000 });
  }

  async waitForContent(timeout = 8_000): Promise<void> {
    await Promise.race([
      this.chokepointItems.first().waitFor({ timeout }),
      this.page.locator("text=Loading chokepoints").waitFor({ timeout }),
      this.page.locator("text=Failed to load chokepoints").waitFor({ timeout }),
    ]).catch(() => {});
  }

  async selectChokepoint(index: number) {
    await this.chokepointItems.nth(index).click();
  }

  async getChokepointCount(): Promise<number> {
    return this.chokepointItems.count();
  }
}
