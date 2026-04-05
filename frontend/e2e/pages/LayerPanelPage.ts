import { type Page, type Locator, expect } from "@playwright/test";
import { BasePage } from "./BasePage";

export class LayerPanelPage extends BasePage {
  readonly panel: Locator;
  readonly densityControl: Locator;
  readonly densitySlider: Locator;
  readonly imageryOpacityControl: Locator;
  readonly imageryOpacityControlSlider: Locator;

  /* ── Named layer toggles ────────────────────────────────────── */
  readonly toggleAoiBoundaries: Locator;
  readonly toggleImageryFootprints: Locator;
  readonly toggleEvents: Locator;
  readonly toggleGdelt: Locator;
  readonly toggleMaritime: Locator;
  readonly toggleAviation: Locator;
  readonly toggleSatelliteOrbits: Locator;
  readonly toggleAirspace: Locator;
  readonly toggleGpsJamming: Locator;
  readonly toggleStrikes: Locator;
  readonly toggleTerrain: Locator;
  readonly toggle3dBuildings: Locator;
  readonly toggleDetections: Locator;

  constructor(page: Page) {
    super(page);
    this.panel = page.locator('[data-testid="layer-panel"]');
    this.densityControl = page.locator('[data-testid="density-control"]');
    this.densitySlider = page.locator('[data-testid="density-slider"]');
    this.imageryOpacityControl = page.locator('[data-testid="imagery-opacity-control"]');
    this.imageryOpacityControlSlider = page.locator('[data-testid="imagery-opacity-slider"]');

    const toggle = (text: string) =>
      page.locator(".layer-toggle").filter({ hasText: text }).locator("input");

    this.toggleAoiBoundaries = toggle("AOI Boundaries");
    this.toggleImageryFootprints = toggle("Imagery Footprints");
    this.toggleEvents = page.getByRole("checkbox", { name: "Events", exact: true });
    this.toggleGdelt = toggle("GDELT");
    this.toggleMaritime = toggle("Maritime");
    this.toggleAviation = toggle("Aviation");
    this.toggleSatelliteOrbits = toggle("Satellite Orbits");
    this.toggleAirspace = toggle("Airspace");
    this.toggleGpsJamming = toggle("GPS Jamming");
    this.toggleStrikes = toggle("Strike Events");
    this.toggleTerrain = toggle("Terrain");
    this.toggle3dBuildings = toggle("3D Buildings");
    this.toggleDetections = toggle("Detections");
  }

  async open() {
    await this.goto();
    await this.openPanel("Sensors");
    await expect(this.panel).toBeVisible();
  }

  async allToggles(): Promise<Locator> {
    return this.page.locator(".layer-toggle input");
  }

  async enableAll() {
    const toggles = this.page.locator(".layer-toggle input");
    const count = await toggles.count();
    for (let i = 0; i < count; i++) {
      await toggles.nth(i).check().catch(() => {});
    }
  }

  async disableAll() {
    const toggles = this.page.locator(".layer-toggle input");
    const count = await toggles.count();
    for (let i = 0; i < count; i++) {
      await toggles.nth(i).uncheck().catch(() => {});
    }
  }

  async setDensity(value: string) {
    await expect(this.densitySlider).toBeVisible();
    await this.densitySlider.fill(value);
  }

  async getDensity(): Promise<string> {
    return this.densitySlider.inputValue();
  }
}
