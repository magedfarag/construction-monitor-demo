// P2-5.1: Integrate globe.gl as secondary 3D view mode
// P2-5.2: Render AOIs and event clusters on globe
import { useEffect, useRef } from "react";
import type { Aoi, CanonicalEvent } from "../../api/types";

interface Props {
  aois: Aoi[];
  events: CanonicalEvent[];
  gdeltEvents?: CanonicalEvent[];
  showEventLayer?: boolean;
  showGdeltLayer?: boolean;
}

// Centroid of a GeoJSON polygon's outer ring
function polygonCentroid(coords: number[][][]): [number, number] {
  const ring = coords[0];
  let lngSum = 0, latSum = 0;
  for (const [lng, lat] of ring) { lngSum += lng; latSum += lat; }
  return [lngSum / ring.length, latSum / ring.length];
}

export function GlobeView({ aois, events, gdeltEvents = [], showEventLayer = true, showGdeltLayer = false }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const globeRef = useRef<any>(null);

  // P2-5.1: initialise globe.gl on mount
  useEffect(() => {
    if (!containerRef.current) return;
    let cancelled = false;

    import("globe.gl").then(({ default: Globe }) => {
      if (cancelled || !containerRef.current) return;

      const globe = Globe({ animateIn: true })(containerRef.current);

      globe
        .globeImageUrl("//unpkg.com/three-globe/example/img/earth-night.jpg")
        .backgroundImageUrl("//unpkg.com/three-globe/example/img/night-sky.png")
        .backgroundColor("#0f172a")
        .width(containerRef.current.clientWidth || 800)
        .height(containerRef.current.clientHeight || 600)
        .showAtmosphere(true)
        .atmosphereColor("#1e6fce")
        .atmosphereAltitude(0.25);

      // Start centred on Middle East
      globe.pointOfView({ lat: 25, lng: 45, altitude: 1.8 });

      globeRef.current = globe;
    }).catch(err => {
      console.error("globe.gl failed to load:", err);
    });

    return () => {
      cancelled = true;
      if (globeRef.current) {
        try { globeRef.current._destructor(); } catch (_) { /* ignore */ }
        globeRef.current = null;
      }
    };
  }, []);

  // P2-5.2: render AOI polygons on globe
  useEffect(() => {
    const globe = globeRef.current;
    if (!globe) return;

    const polygonFeatures = aois
      .filter(a => a.geometry.type === "Polygon" || a.geometry.type === "MultiPolygon")
      .map(a => ({
        type: "Feature" as const,
        geometry: a.geometry,
        properties: { name: a.name, id: a.id },
      }));

    globe
      .polygonsData(polygonFeatures)
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .polygonCapColor(() => "rgba(33, 150, 243, 0.25)")
      .polygonSideColor(() => "rgba(33, 150, 243, 0.4)")
      .polygonStrokeColor(() => "#2196f3")
      .polygonAltitude(0.005)
      .polygonLabel(
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (d: any) => `<div class="globe-tooltip">${d.properties?.name ?? "AOI"}</div>`
      );
  }, [aois]);

  // P2-5.2: render event clusters as points on globe
  useEffect(() => {
    const globe = globeRef.current;
    if (!globe) return;

    const pointData: { lat: number; lng: number; color: string; label: string; radius: number }[] = [];

    if (showEventLayer) {
      for (const evt of events) {
        if (evt.geometry?.type === "Point") {
          const [lng, lat] = evt.geometry.coordinates as [number, number];
          pointData.push({
            lat, lng,
            color: "#f59e0b",
            label: `${evt.event_type} — ${new Date(evt.event_time).toLocaleDateString()}`,
            radius: 0.4,
          });
        }
      }
    }

    if (showGdeltLayer) {
      for (const evt of gdeltEvents) {
        if (evt.geometry?.type === "Point") {
          const [lng, lat] = evt.geometry.coordinates as [number, number];
          pointData.push({
            lat, lng,
            color: "#9c27b0",
            label: `GDELT: ${new Date(evt.event_time).toLocaleDateString()}`,
            radius: 0.3,
          });
        }
      }
    }

    globe
      .pointsData(pointData)
      .pointLat("lat")
      .pointLng("lng")
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .pointColor((d: any) => d.color)
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .pointRadius((d: any) => d.radius)
      .pointAltitude(0.01)
      .pointResolution(6)
      .pointLabel("label");
  }, [events, gdeltEvents, showEventLayer, showGdeltLayer]);

  // AOI label markers (centroids)
  useEffect(() => {
    const globe = globeRef.current;
    if (!globe) return;

    const labels = aois
      .filter(a => a.geometry.type === "Polygon")
      .map(a => {
        const [lng, lat] = polygonCentroid(a.geometry.coordinates as number[][][]);
        return { lat, lng, text: a.name };
      });

    globe
      .labelsData(labels)
      .labelLat("lat")
      .labelLng("lng")
      .labelText("text")
      .labelSize(1.4)
      .labelDotRadius(0.4)
      .labelColor(() => "#e2e8f0")
      .labelResolution(2)
      .labelAltitude(0.01);
  }, [aois]);

  // Handle container resize
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      const g = globeRef.current;
      if (g) {
        g.width(el.clientWidth).height(el.clientHeight);
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  return (
    <div
      ref={containerRef}
      style={{ width: "100%", height: "100%", background: "#0f172a" }}
      data-testid="globe-container"
    />
  );
}
