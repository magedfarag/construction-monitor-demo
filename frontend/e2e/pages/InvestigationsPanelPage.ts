import { type Page, type Locator, expect } from "@playwright/test";
import { BasePage } from "./BasePage";

export class InvestigationsPanelPage extends BasePage {
  readonly panel: Locator;
  readonly newBtn: Locator;
  readonly nameInput: Locator;
  readonly descriptionInput: Locator;
  readonly tagsInput: Locator;
  readonly createBtn: Locator;
  readonly cancelBtn: Locator;
  readonly absenceSignalsBtn: Locator;
  readonly heading: Locator;
  readonly investigationRows: Locator;

  constructor(page: Page) {
    super(page);
    this.panel = page.locator('[data-testid="investigations-panel"]');
    this.newBtn = this.panel.locator('button:has-text("+ New")');
    this.nameInput = this.panel.locator('input[placeholder="Name *"]');
    this.descriptionInput = this.panel.locator('input[placeholder*="Description"], textarea[placeholder*="Description"]');
    this.tagsInput = this.panel.locator('input[placeholder*="Tags"], input[placeholder*="tags"]');
    this.createBtn = this.panel.locator('button:has-text("Create")');
    this.cancelBtn = this.panel.locator('button:has-text("Cancel")');
    this.absenceSignalsBtn = this.panel.locator('button:has-text("Absence Signals")');
    this.heading = this.panel.locator("h3");
    this.investigationRows = this.panel.locator(".investigation-row, .investigation-item, li");
  }

  async open() {
    await this.goto();
    await this.openPanel("Cases");
    await expect(this.panel).toBeVisible({ timeout: 10_000 });
  }

  async openCreateForm() {
    await this.newBtn.click();
  }

  async fillCreateForm(name: string, description?: string, tags?: string) {
    await this.nameInput.fill(name);
    if (description) await this.descriptionInput.fill(description);
    if (tags) await this.tagsInput.fill(tags);
  }

  async submitCreate() {
    await this.createBtn.click();
  }

  async cancelCreate() {
    await this.cancelBtn.click();
  }

  async toggleAbsenceSignals() {
    await this.absenceSignalsBtn.click();
  }

  async clickInvestigation(index: number) {
    await this.investigationRows.nth(index).click();
  }
}
