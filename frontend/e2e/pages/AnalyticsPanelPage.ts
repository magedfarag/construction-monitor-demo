import { type Page, type Locator, expect } from "@playwright/test";
import { BasePage } from "./BasePage";

export class AnalyticsPanelPage extends BasePage {
  readonly panel: Locator;
  readonly submitBtn: Locator;
  readonly heading: Locator;
  readonly candidates: Locator;
  readonly confirmBtns: Locator;
  readonly dismissBtns: Locator;

  constructor(page: Page) {
    super(page);
    this.panel = page.locator('[data-testid="analytics-panel"]');
    this.submitBtn = page.locator('[data-testid="submit-change-job-btn"]');
    this.heading = this.panel.locator("h3");
    this.candidates = this.panel.locator(".candidate, .change-candidate");
    this.confirmBtns = this.panel.locator('button:has-text("Confirm")');
    this.dismissBtns = this.panel.locator('button:has-text("Dismiss")');
  }

  async open() {
    await this.goto();
    await this.openPanel("Intel");
    await expect(this.panel).toBeVisible();
  }

  async runChangeDetection(): Promise<void> {
    await this.submitBtn.click();
  }

  async waitForResults(timeout = 10_000): Promise<void> {
    await Promise.race([
      this.candidates.first().waitFor({ timeout }),
      this.page.locator("text=Running").waitFor({ timeout }),
      this.page.locator("text=No candidates").waitFor({ timeout }),
      this.page.locator("text=Failed").waitFor({ timeout }),
    ]).catch(() => {});
  }

  async confirmCandidate(index: number) {
    await this.confirmBtns.nth(index).click();
  }

  async dismissCandidate(index: number) {
    await this.dismissBtns.nth(index).click();
  }
}
