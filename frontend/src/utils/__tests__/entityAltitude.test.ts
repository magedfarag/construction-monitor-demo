import { describe, expect, it } from "vitest";
import { normalizeEntityAltitudeM } from "../entityAltitude";

describe("normalizeEntityAltitudeM", () => {
  it("always keeps ship altitude at sea level", () => {
    expect(normalizeEntityAltitudeM("ship", 1200)).toBe(0);
    expect(normalizeEntityAltitudeM("ship", -50)).toBe(0);
    expect(normalizeEntityAltitudeM("ship", undefined)).toBe(0);
  });

  it("preserves finite aircraft altitude", () => {
    expect(normalizeEntityAltitudeM("aircraft", 8200)).toBe(8200);
  });

  it("applies an aircraft floor when requested", () => {
    expect(normalizeEntityAltitudeM("aircraft", undefined, 3500)).toBe(3500);
    expect(normalizeEntityAltitudeM("aircraft", 1200, 3500)).toBe(3500);
    expect(normalizeEntityAltitudeM("aircraft", 4800, 3500)).toBe(4800);
  });
});
