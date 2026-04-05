export type RenderMode = "day" | "low_light" | "night_vision" | "thermal";

export interface RenderModeConfig {
  mode: RenderMode;
  label: string;
  description: string;
  /** CSS filter for dark basemaps (dark-matter globe). */
  cssFilter: string;
  /**
   * CSS filter for light/vector basemaps (2D MapView default).
   * Falls back to cssFilter when not set.
   */
  cssFilterLight?: string;
  /** Tint color applied as a semi-transparent overlay */
  tintColor?: string;
  tintOpacity?: number;
}

export const RENDER_MODE_CONFIGS: Record<RenderMode, RenderModeConfig> = {
  day: {
    mode: "day",
    label: "Day",
    description: "Standard daylight visualization",
    cssFilter: "none",
  },
  low_light: {
    mode: "low_light",
    label: "Low Light",
    description: "Reduced brightness, enhanced contrast for dusk/dawn operations",
    cssFilter: "brightness(0.58) contrast(1.25) saturate(0.75)",
    tintColor: "#001133",
    tintOpacity: 0.2,
  },
  night_vision: {
    mode: "night_vision",
    label: "Night Vision",
    description: "Green-channel amplification simulation for NVG operations",
    // Dark basemap (dark-matter globe): brighten first, then sepia → NVG-green.
    // Net effect: readable phosphor-green display on near-black tiles.
    cssFilter:
      "saturate(0) brightness(4) contrast(1.8) sepia(0.85) hue-rotate(82deg) saturate(4) brightness(0.6)",
    // Light/vector basemap (2D MapView): skip brightness boost to avoid blowout;
    // just desaturate → sepia-warm → hue-rotate to green → saturate → dim slightly.
    cssFilterLight:
      "saturate(0) sepia(0.9) hue-rotate(82deg) saturate(4) brightness(0.65) contrast(1.5)",
    tintColor: "#001a00",
    tintOpacity: 0.2,
  },
  thermal: {
    mode: "thermal",
    label: "Thermal",
    description:
      "False-color thermal IR simulation — heat sources appear warm-white to red",
    // Dark basemap: lift luminance first so map features survive the hue shift.
    cssFilter:
      "saturate(0) brightness(3.5) contrast(2) sepia(0.9) hue-rotate(320deg) saturate(3.5) brightness(0.75)",
    // Light/vector basemap: features are already bright; skip boost, just
    // convert to red/orange FLIR palette.
    cssFilterLight:
      "saturate(0) sepia(0.9) hue-rotate(320deg) saturate(4) contrast(1.6) brightness(0.8)",
    tintColor: "#1a0000",
    tintOpacity: 0.2,
  },
};
