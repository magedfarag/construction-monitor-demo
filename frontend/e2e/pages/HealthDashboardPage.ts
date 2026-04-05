import { type Page, type Locator, expect } from "@playwright/test";
import { BasePage } from "./BasePage";

export class HealthDashboardPage extends BasePage {
  readonly pageRoot: Locator;
  readonly banner: Locator;
  readonly alerts: Locator;
  readonly infrastructure: Locator;
  readonly providers: Locator;
  readonly circuitBreakers: Locator;
  readonly connectors: Locator;
  readonly refreshBtn: Locator;
  readonly heading: Locator;

  constructor(page: Page) {
    super(page);
    this.pageRoot = page.locator('[data-testid="system-health-page"]');
    this.banner = page.locator('[data-testid="sh-banner"]');
    this.alerts = page.locator('[data-testid="sh-alerts"]');
    this.infrastructure = page.locator('[data-testid="sh-infrastructure"]');
    this.providers = page.locator('[data-testid="sh-providers"]');
    this.circuitBreakers = page.locator('[data-testid="sh-circuit-breakers"]');
    this.connectors = page.locator('[data-testid="sh-connectors"]');
    this.refreshBtn = this.pageRoot.locator('button:has-text("Refresh")');
    this.heading = this.pageRoot.locator("h2");
  }

  async open() {
    await this.goto();
    await this.openPanel("Status");
    await expect(this.pageRoot).toBeVisible({ timeout: 10_000 });
  }

  async refresh() {
    await this.refreshBtn.click();
  }

  async waitForData(timeout = 10_000): Promise<void> {
    await Promise.race([
      this.banner.waitFor({ timeout }),
      this.page.locator("text=Fetching health data").waitFor({ timeout }),
    ]).catch(() => {});
  }

  async connectorCard(id: string): Promise<Locator> {
    return this.page.locator(`[data-testid="sh-connector-${id}"]`);
  }
}
