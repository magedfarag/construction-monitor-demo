import { type Page, type Locator, expect } from "@playwright/test";
import { BasePage } from "./BasePage";

export class PlaybackPanelPage extends BasePage {
  readonly panel: Locator;
  readonly loadFramesBtn: Locator;
  readonly playPauseBtn: Locator;
  readonly stepBackBtn: Locator;
  readonly stepForwardBtn: Locator;
  readonly speedSelect: Locator;
  readonly scrubber: Locator;
  readonly heading: Locator;

  constructor(page: Page) {
    super(page);
    this.panel = page.locator('[data-testid="playback-panel"]');
    this.loadFramesBtn = this.panel.locator('button:has-text("Load Frames")');
    this.playPauseBtn = this.panel.locator('button:has-text("▶"), button:has-text("⏸")');
    this.stepBackBtn = this.panel.locator('button:has-text("⏮")');
    this.stepForwardBtn = this.panel.locator('button:has-text("⏭")');
    this.speedSelect = this.panel.locator("select");
    this.scrubber = this.panel.locator('input[type="range"]');
    this.heading = this.panel.locator("h3");
  }

  async open() {
    await this.goto();
    await this.openPanel("Replay");
    await expect(this.panel).toBeVisible();
  }

  async loadFrames(): Promise<void> {
    await this.loadFramesBtn.click();
  }

  async waitForFramesLoaded(timeout = 8_000): Promise<void> {
    // Wait for transport controls after frames load
    await Promise.race([
      this.stepBackBtn.waitFor({ state: "visible", timeout }),
      this.page.locator("text=Loading").waitFor({ timeout }),
    ]).catch(() => {});
  }

  async setSpeed(value: string) {
    await this.speedSelect.selectOption(value);
  }

  async play() {
    const playBtn = this.panel.locator('button:has-text("▶")');
    if (await playBtn.isVisible()) {
      await playBtn.click();
    }
  }

  async pause() {
    const pauseBtn = this.panel.locator('button:has-text("⏸")');
    if (await pauseBtn.isVisible()) {
      await pauseBtn.click();
    }
  }
}
