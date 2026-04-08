export type TrackEntityType = "ship" | "aircraft";

export function normalizeEntityAltitudeM(
  entityType: TrackEntityType,
  altitudeM: unknown,
  aircraftFloorM = 0,
): number {
  if (entityType === "ship") return 0;

  const altitude = Number(altitudeM);
  if (!Number.isFinite(altitude)) return aircraftFloorM;

  return Math.max(altitude, aircraftFloorM);
}
