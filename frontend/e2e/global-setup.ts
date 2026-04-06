import type { FullConfig } from "@playwright/test";

const BACKEND_HEALTH_URLS = [
  "http://127.0.0.1:8000/api/health",
  "http://localhost:8000/api/health",
];
const WAIT_TIMEOUT_MS = 180_000;
const RETRY_DELAY_MS = 2_000;

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForBackendHealth(): Promise<void> {
  const deadline = Date.now() + WAIT_TIMEOUT_MS;
  let lastError = "";

  while (Date.now() < deadline) {
    for (const url of BACKEND_HEALTH_URLS) {
      try {
        const response = await fetch(url);
        if (response.ok) {
          return;
        }
        lastError = `${url} => HTTP ${response.status}`;
      } catch (error) {
        lastError = error instanceof Error ? `${url} => ${error.message}` : `${url} => ${String(error)}`;
      }
    }
    await delay(RETRY_DELAY_MS);
  }

  throw new Error(
    `Backend is not ready after ${WAIT_TIMEOUT_MS / 1000}s (${lastError}). ` +
      "Start the API server before running e2e tests.",
  );
}

export default async function globalSetup(_config: FullConfig): Promise<void> {
  await waitForBackendHealth();
}
