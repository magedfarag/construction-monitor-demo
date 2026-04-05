import { type Page, type Locator, expect } from "@playwright/test";
import { BasePage } from "./BasePage";

export class ExportPanelPage extends BasePage {
  readonly panel: Locator;
  readonly exportBtn: Locator;
  readonly formatSelect: Locator;
  readonly heading: Locator;

  constructor(page: Page) {
    super(page);
    this.panel = page.locator('[data-testid="export-panel"]');
    this.exportBtn = page.locator('[data-testid="export-btn"]');
    this.formatSelect = this.panel.locator("select");
    this.heading = this.panel.locator("h3");
  }

  async open() {
    await this.goto();
    await this.openPanel("Extract");
    await expect(this.panel).toBeVisible();
  }

  async selectFormat(format: "CSV" | "GeoJSON") {
    await this.formatSelect.selectOption({ label: format });
  }

  async export(): Promise<void> {
    await this.exportBtn.click();
  }

  async waitForExportResult(timeout = 8_000): Promise<void> {
    await Promise.race([
      this.page.locator("text=Done").waitFor({ timeout }),
      this.page.locator("text=Export failed").waitFor({ timeout }),
      this.page.locator("text=Submitting").waitFor({ timeout }),
      this.page.locator("text=Error").waitFor({ timeout }),
    ]).catch(() => {});
  }
}
