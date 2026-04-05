import { type Page, type Locator, expect } from "@playwright/test";
import { BasePage } from "./BasePage";

export class IntelBriefingPanelPage extends BasePage {
  readonly panel: Locator;
  readonly vesselAlerts: Locator;

  constructor(page: Page) {
    super(page);
    this.panel = page.locator('[data-testid="intel-briefing-panel"]');
    this.vesselAlerts = this.panel.locator("li, .vessel-alert, .alert-item");
  }

  async open() {
    await this.goto();
    await this.openPanel("Briefing");
    await expect(this.panel).toBeVisible({ timeout: 10_000 });
  }

  async waitForContent(timeout = 8_000): Promise<void> {
    await Promise.race([
      this.panel.locator("text=INTELLIGENCE BRIEFING").waitFor({ timeout }),
      this.panel.locator("text=Loading briefing").waitFor({ timeout }),
    ]).catch(() => {});
  }

  async selectVesselAlert(index: number) {
    await this.vesselAlerts.nth(index).click();
  }
}
