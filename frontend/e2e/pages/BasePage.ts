import { type Page, type Locator, expect } from "@playwright/test";

/**
 * Base page object providing shared navigation, sidebar, header, and
 * common assertion helpers used by every feature-specific page object.
 */
export class BasePage {
  readonly page: Page;

  /* ── Header ─────────────────────────────────────────────────── */
  readonly header: Locator;
  readonly appTitle: Locator;
  readonly liveBadge: Locator;
  readonly headerClock: Locator;
  readonly apiKeyInput: Locator;

  /* ── Sidebar ────────────────────────────────────────────────── */
  readonly sidebar: Locator;

  /* ── View mode ──────────────────────────────────────────────── */
  readonly btn2D: Locator;
  readonly btn3D: Locator;

  /* ── Map / Globe containers ─────────────────────────────────── */
  readonly mapContainer: Locator;
  readonly globeContainer: Locator;

  /* ── Animation controls ─────────────────────────────────────── */
  readonly animPlayPause: Locator;
  readonly animReset: Locator;
  readonly animTime: Locator;

  /* ── Draw tools (2D only) ───────────────────────────────────── */
  readonly drawBboxBtn: Locator;
  readonly drawPolygonBtn: Locator;
  readonly drawHint: Locator;

  /* ── Basemap picker ─────────────────────────────────────────── */
  readonly basemapPicker: Locator;

  /* ── Imagery opacity (2D only) ──────────────────────────────── */
  readonly imageryOpacitySlider: Locator;

  constructor(page: Page) {
    this.page = page;

    this.header = page.locator(".app-header");
    this.appTitle = page.locator("h1");
    this.liveBadge = page.locator(".live-badge");
    this.headerClock = page.locator(".header-clock");
    this.apiKeyInput = page.locator(".api-key-input");

    this.sidebar = page.locator(".sidebar");

    this.btn2D = page.locator('button:has-text("2D")');
    this.btn3D = page.locator('button:has-text("🌐 3D")');

    this.mapContainer = page.locator('[data-testid="map-container"]');
    this.globeContainer = page.locator('[data-testid="globe-container"]');

    this.animPlayPause = page.locator(".anim-controls .btn").first();
    this.animReset = page.locator(".anim-controls .btn").nth(1);
    this.animTime = page.locator(".anim-time");

    this.drawBboxBtn = page.locator('button:has-text("BBox")').first();
    this.drawPolygonBtn = page.locator('button:has-text("Polygon")').first();
    this.drawHint = page.locator(".draw-hint");

    this.basemapPicker = page.locator(".basemap-picker");
    this.imageryOpacitySlider = page.locator(".opacity-slider");
  }

  /* ── Navigation ─────────────────────────────────────────────── */
  async goto() {
    await this.page.goto("/");
    await expect(
      this.mapContainer.or(this.globeContainer).first(),
    ).toBeVisible({ timeout: 20_000 });
  }

  /* ── Sidebar helpers ────────────────────────────────────────── */
  private sidebarBtn(label: string): Locator {
    return this.sidebar.locator(`.sidebar-btn:has-text("${label}")`);
  }

  async openPanel(label: string) {
    await this.sidebarBtn(label).click();
  }

  async expectPanelActive(label: string) {
    await expect(this.sidebarBtn(label)).toHaveClass(/sidebar-btn--active/);
  }

  /* ── View mode helpers ──────────────────────────────────────── */
  async switchTo2D() {
    await this.btn2D.click();
    await expect(this.mapContainer).toBeVisible({ timeout: 10_000 });
  }

  async switchTo3D() {
    await this.btn3D.click();
    await expect(this.globeContainer).toBeVisible({ timeout: 10_000 });
  }

  /* ── Generic waits / assertions ─────────────────────────────── */
  async expectVisible(locator: Locator, timeout = 10_000) {
    await expect(locator).toBeVisible({ timeout });
  }

  async expectNotVisible(locator: Locator, timeout = 5_000) {
    await expect(locator).not.toBeVisible({ timeout });
  }

  async expectText(locator: Locator, text: string | RegExp) {
    if (typeof text === "string") {
      await expect(locator).toContainText(text);
    } else {
      await expect(locator).toHaveText(text);
    }
  }

  /** Measure elapsed wall-clock time of an async action. */
  async measureMs(fn: () => Promise<void>): Promise<number> {
    const t0 = Date.now();
    await fn();
    return Date.now() - t0;
  }
}
