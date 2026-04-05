import { type Page, type Locator, expect } from "@playwright/test";
import { BasePage } from "./BasePage";

export class CameraFeedPanelPage extends BasePage {
  readonly panel: Locator;
  readonly heading: Locator;
  readonly cameraItems: Locator;
  readonly playBtn: Locator;
  readonly stopBtn: Locator;
  readonly jumpToMapBtns: Locator;

  constructor(page: Page) {
    super(page);
    this.panel = page.locator('[data-testid="camera-feed-panel"]');
    this.heading = this.panel.locator("h3");
    this.cameraItems = this.panel.locator(".camera-item, li");
    this.playBtn = this.panel.locator('button:has-text("PLAY")');
    this.stopBtn = this.panel.locator('button:has-text("Stop")');
    this.jumpToMapBtns = this.panel.locator('button:has-text("Jump to map")');
  }

  async open() {
    await this.goto();
    await this.openPanel("Cameras");
    await expect(this.panel).toBeVisible({ timeout: 10_000 });
  }

  async waitForContent(timeout = 8_000): Promise<void> {
    await Promise.race([
      this.panel.locator("text=Loading cameras").waitFor({ timeout }),
      this.panel.locator("text=Camera Feeds").waitFor({ timeout }),
      this.panel.locator("text=No cameras registered").waitFor({ timeout }),
      this.panel.locator("text=Camera feeds unavailable").waitFor({ timeout }),
    ]).catch(() => {});
  }

  async selectCamera(index: number) {
    const items = this.panel.locator("li, .camera-item");
    await items.nth(index).click();
  }
}
