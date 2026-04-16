import { defineConfig } from 'vitest/config'
import { loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { fileURLToPath } from 'url'

// Resolve project root regardless of which directory Vite is invoked from.
// __dirname is not available in ESM; derive it from import.meta.url instead.
const __dirname = path.dirname(fileURLToPath(import.meta.url))
const projectRoot = path.resolve(__dirname, '..')

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Load all env vars from the PROJECT ROOT (.env lives next to pyproject.toml,
  // not inside frontend/).
  const env = loadEnv(mode, projectRoot, '')
  // Prefer OPERATOR_API_KEY for the dev proxy so operator-only endpoints
  // (e.g. POST /api/v1/investigations) work out of the box in development.
  const proxyApiKey = env.OPERATOR_API_KEY || env.API_KEY || ''
  const backendTarget = env.ARGUS_BACKEND_TARGET || 'http://127.0.0.1:8000'
  // Explicit type annotation avoids the `{ Authorization?: undefined }` union
  // that breaks Vite's ProxyOptions header signature.
  const proxyHeaders: Record<string, string> = proxyApiKey ? { Authorization: `Bearer ${proxyApiKey}` } : {}

  return {
    plugins: [react()],
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: ['./src/test-setup.ts'],
      include: ['src/**/*.{test,spec}.{ts,tsx}'],
      exclude: ['e2e/**', 'node_modules/**'],
    },
    server: {
      port: 5173,
      proxy: {
        // Strip trailing slashes before forwarding to prevent FastAPI's
        // redirect_slashes from issuing a 307 that the browser would follow
        // cross-origin (strict-origin-when-cross-origin referrer policy).
        '/api': {
          target: backendTarget,
          changeOrigin: true,
          headers: proxyHeaders,
          rewrite: (path) => path.replace(/\/+$/, ''),
        },
        '/demo': { target: backendTarget, changeOrigin: true },
        '/static': { target: backendTarget, changeOrigin: true },
        '/healthz': { target: backendTarget, changeOrigin: true },
        '/readyz': { target: backendTarget, changeOrigin: true },
      },
    },
  }
})
