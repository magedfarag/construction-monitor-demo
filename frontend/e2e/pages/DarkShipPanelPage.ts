import { type Page, type Locator, expect } from "@playwright/test";
import { BasePage } from "./BasePage";

export class DarkShipPanelPage extends BasePage {
  readonly panel: Locator;
  readonly heading: Locator;
  readonly candidates: Locator;

  constructor(page: Page) {
    super(page);
    this.panel = page.locator('[data-testid="dark-ship-panel"]');
    this.heading = this.panel.locator("h3");
    this.candidates = this.panel.locator("li, .dark-ship-item, .candidate-item");
  }

  async open() {
    await this.goto();
    await this.openPanel("Dark Ships");
    await expect(this.panel).toBeVisible({ timeout: 10_000 });
  }

  async waitForContent(timeout = 8_000): Promise<void> {
    await Promise.race([
      this.candidates.first().waitFor({ timeout }),
      this.page.locator("text=Running detection").waitFor({ timeout }),
      this.page.locator("text=Detection unavailable").waitFor({ timeout }),
      this.page.locator("text=No dark ship events").waitFor({ timeout }),
    ]).catch(() => {});
  }

  async selectCandidate(index: number) {
    await this.candidates.nth(index).click();
  }

  async getCandidateCount(): Promise<number> {
    return this.candidates.count();
  }
}
