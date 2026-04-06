import { type Page, type Locator } from "@playwright/test";
import { BasePage } from "./BasePage";

export class VesselProfileModalPage extends BasePage {
  readonly modal: Locator;
  readonly closeBtn: Locator;
  readonly overlay: Locator;
  readonly vesselName: Locator;

  constructor(page: Page) {
    super(page);
    this.modal = page.locator('[data-testid="vessel-modal"]');
    this.closeBtn = this.modal.locator('button:has-text("✕")');
    this.overlay = this.modal;
    this.vesselName = this.modal.locator("h2");
  }

  async isOpen(): Promise<boolean> {
    return this.modal.isVisible();
  }

  async close() {
    await this.closeBtn.click();
  }

  async closeByOverlay() {
    // Click the overlay (the root div) outside the modal content
    await this.overlay.click({ position: { x: 5, y: 5 } });
  }

  async waitForContent(timeout = 8_000): Promise<void> {
    await Promise.race([
      this.vesselName.waitFor({ timeout }),
      this.page.locator("text=Loading vessel profile").waitFor({ timeout }),
      this.page.locator("text=No profile found").waitFor({ timeout }),
    ]).catch(() => {});
  }
}
