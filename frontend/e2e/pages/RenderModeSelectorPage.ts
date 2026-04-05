import { type Page, type Locator, expect } from "@playwright/test";
import { BasePage } from "./BasePage";

export class RenderModeSelectorPage extends BasePage {
  readonly dayBtn: Locator;
  readonly lowLightBtn: Locator;
  readonly nightVisionBtn: Locator;
  readonly thermalBtn: Locator;

  constructor(page: Page) {
    super(page);
    this.dayBtn = page.getByRole("button", { name: /^day$/i });
    this.lowLightBtn = page.getByRole("button", { name: /^low light$/i });
    this.nightVisionBtn = page.getByRole("button", { name: /^night vision$/i });
    this.thermalBtn = page.getByRole("button", { name: /^thermal$/i });
  }

  async waitForSelector() {
    await expect(this.dayBtn).toBeVisible({ timeout: 10_000 });
  }

  async selectMode(mode: "day" | "lowLight" | "nightVision" | "thermal") {
    const btn = {
      day: this.dayBtn,
      lowLight: this.lowLightBtn,
      nightVision: this.nightVisionBtn,
      thermal: this.thermalBtn,
    }[mode];
    await btn.click();
  }

  async expectActiveMode(mode: "day" | "lowLight" | "nightVision" | "thermal") {
    const btn = {
      day: this.dayBtn,
      lowLight: this.lowLightBtn,
      nightVision: this.nightVisionBtn,
      thermal: this.thermalBtn,
    }[mode];
    await expect(btn).toHaveCSS("font-weight", "700");
  }
}
