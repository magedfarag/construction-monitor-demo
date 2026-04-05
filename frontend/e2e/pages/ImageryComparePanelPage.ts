import { type Page, type Locator, expect } from "@playwright/test";
import { BasePage } from "./BasePage";

export class ImageryComparePanelPage extends BasePage {
  readonly beforeSelect: Locator;
  readonly afterSelect: Locator;
  readonly swapBtn: Locator;
  readonly emptyState: Locator;

  constructor(page: Page) {
    super(page);
    const panel = page.locator(".side-panel");
    this.beforeSelect = panel.locator("select").first();
    this.afterSelect = panel.locator("select").last();
    this.swapBtn = panel.locator('button:has-text("⇄")');
    this.emptyState = panel.locator("text=No imagery results yet");
  }

  async open() {
    await this.goto();
    await this.openPanel("Diff");
  }
}
