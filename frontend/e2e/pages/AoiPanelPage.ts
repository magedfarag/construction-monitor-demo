import { type Page, type Locator, expect } from "@playwright/test";
import { BasePage } from "./BasePage";

export class AoiPanelPage extends BasePage {
  readonly panel: Locator;
  readonly nameInput: Locator;
  readonly aoiItems: Locator;
  readonly saveBtn: Locator;
  readonly cancelBtn: Locator;
  readonly heading: Locator;
  /* Panel-scoped draw buttons (avoid matching the map-overlay duplicates) */
  override readonly drawBboxBtn: Locator;
  override readonly drawPolygonBtn: Locator;

  constructor(page: Page) {
    super(page);
    this.panel = page.locator('[data-testid="aoi-panel"]');
    this.nameInput = page.locator('[data-testid="aoi-name-input"]');
    this.aoiItems = page.locator('[data-testid="aoi-item"]');
    this.saveBtn = this.panel.locator('button:has-text("Save")');
    this.cancelBtn = this.panel.locator('button:has-text("Cancel")');
    this.heading = this.panel.locator("h3");
    this.drawBboxBtn = this.panel.locator('button:has-text("BBox")');
    this.drawPolygonBtn = this.panel.locator('button:has-text("Polygon")');
  }

  async open() {
    await this.goto();
    await this.openPanel("Zones");
    await expect(this.panel).toBeVisible();
  }

  async getAoiCount(): Promise<number> {
    return this.aoiItems.count();
  }

  async selectAoi(index: number) {
    await this.aoiItems.nth(index).click();
  }

  async deleteAoi(index: number) {
    await this.aoiItems.nth(index).locator("button:has-text('✕')").click();
  }

  async fillName(name: string) {
    await this.nameInput.fill(name);
  }

  async save() {
    await this.saveBtn.click();
  }

  async cancel() {
    await this.cancelBtn.click();
  }
}
