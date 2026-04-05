import { type Page, type Locator, expect } from "@playwright/test";
import { BasePage } from "./BasePage";

export class SearchPanelPage extends BasePage {
  readonly panel: Locator;
  readonly searchBtn: Locator;
  readonly eventList: Locator;
  readonly eventItems: Locator;
  readonly pagination: Locator;
  readonly paginationPrev: Locator;
  readonly paginationNext: Locator;
  readonly paginationInfo: Locator;

  constructor(page: Page) {
    super(page);
    this.panel = page.locator('[data-testid="search-panel"]');
    this.searchBtn = page.locator('[data-testid="search-btn"]');
    this.eventList = page.locator('[data-testid="event-list"]');
    this.eventItems = page.locator('[data-testid="event-item"]');
    this.pagination = page.locator('[data-testid="pagination"]');
    this.paginationPrev = page.locator('[data-testid="pagination-prev"]');
    this.paginationNext = page.locator('[data-testid="pagination-next"]');
    this.paginationInfo = page.locator('[data-testid="pagination-info"]');
  }

  async open() {
    await this.goto();
    await this.openPanel("Signals");
    await expect(this.panel).toBeVisible();
  }

  async search(): Promise<void> {
    await this.searchBtn.click();
  }

  async waitForResults(timeout = 8_000): Promise<void> {
    await Promise.race([
      this.eventItems.first().waitFor({ timeout }),
      this.page.locator("text=No events found").waitFor({ timeout }),
      this.page.locator("text=Searching").waitFor({ timeout }),
    ]).catch(() => {});
  }

  async getEventCount(): Promise<number> {
    return this.eventItems.count();
  }

  async getPageInfo(): Promise<string> {
    return this.paginationInfo.textContent() as Promise<string>;
  }

  async nextPage() {
    await this.paginationNext.click();
  }

  async prevPage() {
    await this.paginationPrev.click();
  }

  async clickEvent(index: number) {
    await this.eventItems.nth(index).click();
  }
}
