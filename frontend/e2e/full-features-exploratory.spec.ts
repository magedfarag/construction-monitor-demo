import fs from "node:fs";
import path from "node:path";
import type { TestInfo } from "@playwright/test";
import { test, expect } from "./fixtures";
import {
  AnalyticsPanelPage,
  AoiPanelPage,
  BasePage,
  CameraFeedPanelPage,
  ChokepointPanelPage,
  DarkShipPanelPage,
  ExportPanelPage,
  HealthDashboardPage,
  ImageryComparePanelPage,
  IntelBriefingPanelPage,
  InvestigationsPanelPage,
  LayerPanelPage,
  PlaybackPanelPage,
  RenderModeSelectorPage,
  SearchPanelPage,
  TimelinePanelPage,
  VesselProfileModalPage,
} from "./pages";

type StepResult = {
  name: string;
  status: "ok" | "warning";
  notes: string[];
};

const AUTH_ENV_KEYS = ["ANALYST_API_KEY", "OPERATOR_API_KEY", "ADMIN_API_KEY", "API_KEY"] as const;

function cleanEnvValue(raw: string): string {
  const trimmed = raw.trim();
  if (
    (trimmed.startsWith('"') && trimmed.endsWith('"')) ||
    (trimmed.startsWith("'") && trimmed.endsWith("'"))
  ) {
    return trimmed.slice(1, -1);
  }
  return trimmed;
}

function resolveBackendApiKey(): string {
  for (const key of AUTH_ENV_KEYS) {
    const value = process.env[key];
    if (value?.trim()) return value.trim();
  }

  const envCandidates = [
    path.resolve(process.cwd(), ".env"),
    path.resolve(process.cwd(), "..", ".env"),
    path.resolve(process.cwd(), "..", "..", ".env"),
  ];

  for (const envPath of envCandidates) {
    if (!fs.existsSync(envPath)) continue;

    const envFile = fs.readFileSync(envPath, "utf8");
    for (const key of AUTH_ENV_KEYS) {
      const match = envFile.match(new RegExp(`^${key}=(.*)$`, "m"));
      if (match?.[1]) return cleanEnvValue(match[1]);
    }
  }

  return "";
}

const backendApiKey = resolveBackendApiKey();

async function captureEvidence(page: BasePage["page"], testInfo: TestInfo, slug: string): Promise<void> {
  const path = testInfo.outputPath(`${slug}.png`);
  await page.screenshot({ path, fullPage: false });
  await testInfo.attach(`screenshot-${slug}`, {
    path,
    contentType: "image/png",
  });
}

async function collectVisibleTexts(page: BasePage["page"], selector: string, limit = 3): Promise<string[]> {
  const locator = page.locator(selector);
  const count = await locator.count();
  const values: string[] = [];

  for (let i = 0; i < Math.min(count, limit); i += 1) {
    const text = (await locator.nth(i).textContent())?.trim();
    if (text) values.push(text.replace(/\s+/g, " "));
  }

  return values;
}

async function seedSessionAuth(page: BasePage["page"]): Promise<void> {
  if (!backendApiKey) return;

  await page.context().addCookies([
    {
      name: "api_key",
      value: backendApiKey,
      domain: "localhost",
      path: "/",
      sameSite: "Lax",
    },
    {
      name: "api_key",
      value: backendApiKey,
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax",
    },
  ]).catch(() => {});

  await page.addInitScript((token: string) => {
    window.localStorage.setItem("geoint_api_key", token);
    document.cookie = `api_key=${encodeURIComponent(token)}; path=/; SameSite=Lax`;
  }, backendApiKey);
}

function createRecorder(page: BasePage["page"], testInfo: TestInfo, pageErrors: string[], summaryName: string) {
  const results: StepResult[] = [];

  async function runStep(name: string, slug: string, fn: () => Promise<string[]>) {
    const result = await test.step(name, async () => {
      const notes = await fn();
      await captureEvidence(page, testInfo, slug);
      return { name, status: "ok" as const, notes };
    }).catch(async (error: unknown) => {
      const message = error instanceof Error ? error.message : String(error);
      await captureEvidence(page, testInfo, `${slug}-warning`).catch(() => {});
      return { name, status: "warning" as const, notes: [message] };
    });

    results.push(result);
  }

  async function finalize() {
    const dedupedPageErrors = [...new Set(pageErrors)];
    if (dedupedPageErrors.length > 0) {
      results.push({
        name: "runtime page errors",
        status: "warning",
        notes: dedupedPageErrors,
      });
    }

    await testInfo.attach(summaryName, {
      body: JSON.stringify(
        {
          executedAt: new Date().toISOString(),
          authConfigured: Boolean(backendApiKey),
          pageErrors: dedupedPageErrors,
          warnings: results.filter((entry) => entry.status === "warning"),
          steps: results,
        },
        null,
        2,
      ),
      contentType: "application/json",
    });
  }

  return { runStep, finalize };
}

test.describe.configure({ mode: "serial" });

test.describe("Exploratory: full features evidence sweep", () => {
  test.setTimeout(10 * 60 * 1000);

  test.beforeEach(async ({ page }) => {
    await seedSessionAuth(page);
  });

  test("shell, timeline, zones, and sensors", async ({ page }, testInfo) => {
    const pageErrors: string[] = [];
    page.on("pageerror", (error) => pageErrors.push(error.message));

    const base = new BasePage(page);
    const renderModes = new RenderModeSelectorPage(page);
    const timeline = new TimelinePanelPage(page);
    const aoi = new AoiPanelPage(page);
    const layers = new LayerPanelPage(page);
    const recorder = createRecorder(page, testInfo, pageErrors, "summary-shell-zones");

    await recorder.runStep("app shell and view modes", "01-shell", async () => {
      await base.goto();
      await expect(base.header).toBeVisible();
      await expect(base.liveBadge).toContainText("LIVE");
      await expect(base.headerClock).toContainText("UTC");
      await base.switchTo2D();
      await renderModes.waitForSelector();
      await renderModes.selectMode("lowLight");
      await renderModes.selectMode("nightVision");
      await renderModes.selectMode("thermal");
      await renderModes.selectMode("day");
      await base.switchTo3D();
      await base.switchTo2D();
      return ["App shell loaded", "2D/3D toggled", "Render modes cycled"];
    });

    await recorder.runStep("timeline presets and animation controls", "02-timeline", async () => {
      await timeline.expectPanelVisible();
      await timeline.expand();
      await timeline.selectPreset("24h");
      await page.waitForTimeout(500);
      await timeline.selectPreset("7d");
      await page.waitForTimeout(500);
      await timeline.selectPreset("30d");
      await page.waitForTimeout(500);
      await timeline.collapse();
      await base.animPlayPause.click().catch(() => {});
      await page.waitForTimeout(750);
      await base.animPlayPause.click().catch(() => {});
      await base.animReset.click().catch(() => {});
      return ["Timeline expanded", "24h/7d/30d presets exercised", "Animation controls tapped"];
    });

    await recorder.runStep("zones and AOI tools", "03-zones", async () => {
      await base.openPanel("Zones");
      await expect(aoi.panel).toBeVisible();
      await base.switchTo2D();
      await aoi.drawBboxBtn.click();
      await expect(aoi.drawHint).toContainText(/corners/i);
      await aoi.drawBboxBtn.click();
      await aoi.drawPolygonBtn.click();
      await expect(aoi.drawHint).toContainText(/vertices/i);
      await aoi.drawPolygonBtn.click();
      const count = await aoi.getAoiCount();
      if (count > 0) await aoi.selectAoi(0);
      return [`AOI count: ${count}`, "BBox and polygon tool states exercised"];
    });

    await recorder.runStep("sensor layers and map controls", "04-sensors", async () => {
      await base.openPanel("Sensors");
      await expect(layers.panel).toBeVisible();
      await layers.toggleMaritime.check().catch(() => {});
      await layers.toggleAviation.check().catch(() => {});
      await layers.toggleImageryFootprints.check().catch(() => {});
      await layers.toggleDetections.check().catch(() => {});
      await layers.toggleTerrain.check().catch(() => {});

      if (await layers.densitySlider.isVisible().catch(() => false)) {
        await layers.setDensity("0.5");
      }
      if (await layers.imageryOpacityControlSlider.isVisible().catch(() => false)) {
        await layers.imageryOpacityControlSlider.fill("0.6");
      }

      await page.locator(".maplibregl-ctrl-zoom-in").click().catch(() => {});
      await page.waitForTimeout(400);
      await page.locator(".maplibregl-ctrl-zoom-out").click().catch(() => {});
      return ["Core sensor layers enabled", "Density/imagery controls adjusted", "Map zoom controls exercised"];
    });

    await recorder.finalize();
  });

  test("signals, replay, and intel analytics", async ({ page }, testInfo) => {
    const pageErrors: string[] = [];
    page.on("pageerror", (error) => pageErrors.push(error.message));

    const base = new BasePage(page);
    const search = new SearchPanelPage(page);
    const playback = new PlaybackPanelPage(page);
    const analytics = new AnalyticsPanelPage(page);
    const recorder = createRecorder(page, testInfo, pageErrors, "summary-signals-replay-intel");

    await recorder.runStep("signals search", "05-signals", async () => {
      const responsePromise = page
        .waitForResponse((response) => response.url().includes("/api/v1/events/search"), { timeout: 20_000 })
        .catch(() => null);
      await base.goto();
      await base.openPanel("Signals");
      await expect(search.panel).toBeVisible();
      await search.search();
      const response = await responsePromise;
      await search.waitForResults(20_000);
      const count = await search.getEventCount();
      if (count > 0) await search.clickEvent(0);
      const sampleEvents = await collectVisibleTexts(page, '[data-testid="event-item"]', 3);
      return [
        `Search request: ${response ? `HTTP ${response.status()}` : "not observed"}`,
        `Events visible: ${count}`,
        ...sampleEvents,
      ];
    });

    await recorder.runStep("replay transport", "06-replay", async () => {
      const responsePromise = page
        .waitForResponse((response) => response.url().includes("/api/v1/playback/query"), { timeout: 15_000 })
        .catch(() => null);
      await base.openPanel("Replay");
      await expect(playback.panel).toBeVisible();
      if (await playback.loadFramesBtn.isVisible().catch(() => false)) {
        await playback.loadFramesBtn.click({ timeout: 5_000 }).catch(() => {});
      }
      const response = await responsePromise;
      await playback.waitForFramesLoaded(10_000);

      const hasTransportControls = await playback.stepBackBtn.isVisible().catch(() => false);
      if (hasTransportControls) {
        await playback.play();
        await page.waitForTimeout(1_500);
        await playback.setSpeed("2×").catch(() => {});
        await page.waitForTimeout(750);
        await playback.stepForwardBtn.click().catch(() => {});
        await playback.stepBackBtn.click().catch(() => {});
        await playback.pause();
      }

      return [
        "Replay panel opened",
        `Playback query: ${response ? `HTTP ${response.status()}` : "not observed"}`,
        `Transport controls visible: ${hasTransportControls}`,
      ];
    });

    await recorder.runStep("intel analytics", "07-intel", async () => {
      const responsePromise = page
        .waitForResponse(
          (response) =>
            response.url().includes("/api/v1/analytics/change-detection") &&
            response.request().method() === "POST",
          { timeout: 20_000 },
        )
        .catch(() => null);
      await base.openPanel("Intel");
      await expect(analytics.panel).toBeVisible();
      await analytics.runChangeDetection();
      const response = await responsePromise;
      await analytics.waitForResults(20_000);
      const count = await analytics.candidates.count();
      if (count > 0) await analytics.candidates.first().click().catch(() => {});
      return [
        `Change detection submit: ${response ? `HTTP ${response.status()}` : "not observed"}`,
        `Change candidates visible: ${count}`,
      ];
    });

    await recorder.finalize();
  });

  test("routes, dark ships, briefing, and cases", async ({ page }, testInfo) => {
    const pageErrors: string[] = [];
    page.on("pageerror", (error) => pageErrors.push(error.message));

    const base = new BasePage(page);
    const routes = new ChokepointPanelPage(page);
    const darkShips = new DarkShipPanelPage(page);
    const vesselModal = new VesselProfileModalPage(page);
    const briefing = new IntelBriefingPanelPage(page);
    const cases = new InvestigationsPanelPage(page);
    const recorder = createRecorder(page, testInfo, pageErrors, "summary-maritime-cases");

    await recorder.runStep("routes chokepoints", "08-routes", async () => {
      await base.goto();
      await base.openPanel("Routes");
      await expect(routes.panel).toBeVisible();
      await routes.waitForContent(20_000);
      const count = await routes.getChokepointCount();
      if (count > 0) await routes.selectChokepoint(0);
      return [`Chokepoints visible: ${count}`];
    });

    await recorder.runStep("dark ships and vessel profile", "09-dark-ships", async () => {
      await base.openPanel("Dark Ships");
      await expect(darkShips.panel).toBeVisible();
      await darkShips.waitForContent(20_000);
      const count = await darkShips.getCandidateCount();
      if (count > 0) {
        await darkShips.selectCandidate(0);
        await vesselModal.waitForContent(10_000);
        if (await vesselModal.isOpen()) {
          await vesselModal.close().catch(() => vesselModal.closeByOverlay());
        }
      }
      return [`Dark ship candidates visible: ${count}`];
    });

    await recorder.runStep("briefing intelligence summary", "10-briefing", async () => {
      await base.openPanel("Briefing");
      await expect(briefing.panel).toBeVisible();
      await briefing.waitForContent(20_000);
      const count = await briefing.vesselAlerts.count();
      if (count > 0) await briefing.selectVesselAlert(0);
      return [`Briefing alerts visible: ${count}`];
    });

    await recorder.runStep("cases surface and create flow", "11-cases", async () => {
      await base.openPanel("Cases");
      await expect(cases.panel).toBeVisible({ timeout: 20_000 });
      const count = await cases.investigationRows.count();
      if (count > 0) await cases.clickInvestigation(0);
      if (await cases.newBtn.isVisible().catch(() => false)) {
        await cases.openCreateForm();
        await cases.fillCreateForm(
          `Exploratory ${Date.now()}`,
          "Evidence-only exploratory form exercise",
          "playwright,evidence",
        );
        await cases.cancelCreate().catch(() => {});
      }
      return [`Investigation rows visible: ${count}`, "Create/cancel flow exercised"];
    });

    await recorder.finalize();
  });

  test("export, diff, cameras, and system health", async ({ page }, testInfo) => {
    const pageErrors: string[] = [];
    page.on("pageerror", (error) => pageErrors.push(error.message));

    const base = new BasePage(page);
    const exportPanel = new ExportPanelPage(page);
    const imageryCompare = new ImageryComparePanelPage(page);
    const cameras = new CameraFeedPanelPage(page);
    const status = new HealthDashboardPage(page);
    const recorder = createRecorder(page, testInfo, pageErrors, "summary-export-status");

    await recorder.runStep("export panel", "12-export", async () => {
      const responsePromise = page
        .waitForResponse(
          (response) =>
            response.url().includes("/api/v1/exports") &&
            response.request().method() === "POST",
          { timeout: 20_000 },
        )
        .catch(() => null);
      await base.goto();
      await base.openPanel("Extract");
      await expect(exportPanel.panel).toBeVisible();
      await exportPanel.selectFormat("CSV").catch(() => {});
      await exportPanel.export();
      const response = await responsePromise;
      await exportPanel.waitForExportResult(20_000);
      return [`Export submit: ${response ? `HTTP ${response.status()}` : "not observed"}`, "CSV export flow exercised"];
    });

    await recorder.runStep("imagery compare panel", "13-diff", async () => {
      await base.openPanel("Diff");
      await page.waitForTimeout(750);
      const emptyStateVisible = await imageryCompare.emptyState.isVisible().catch(() => false);
      const swapVisible = await imageryCompare.swapBtn.isVisible().catch(() => false);
      return [
        `Diff empty state visible: ${emptyStateVisible}`,
        `Diff swap control visible: ${swapVisible}`,
      ];
    });

    await recorder.runStep("camera feeds", "14-cameras", async () => {
      await base.openPanel("Cameras");
      await expect(cameras.panel).toBeVisible();
      await cameras.waitForContent(20_000);
      const count = await cameras.cameraItems.count();
      if (count > 0) await cameras.selectCamera(0);
      return [`Camera rows visible: ${count}`];
    });

    await recorder.runStep("status dashboard", "15-status", async () => {
      await base.openPanel("Status");
      await expect(status.pageRoot).toBeVisible({ timeout: 20_000 });
      await status.waitForData(20_000);
      await status.refresh().catch(() => {});
      return ["Status dashboard opened", "Refresh exercised"];
    });

    await recorder.finalize();
  });
});
