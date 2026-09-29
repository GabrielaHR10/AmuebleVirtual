import { defineConfig, devices } from '@playwright/test'

// e2e contra la app servida por FastAPI (correr antes `bash scripts/build_frontend.sh`).
// E2E_PORT permite usar otro puerto si la app ya está abierta en el 8000.
const port = Number(process.env.E2E_PORT ?? 8000)

export default defineConfig({
  testDir: './e2e',
  // un solo servidor con un solo modelo de IA: las pruebas en paralelo se estorban (análisis de ~1 min en video)
  workers: 1,
  outputDir: './test-results/artifacts',
  timeout: 60_000,
  use: {
    baseURL: `http://localhost:${port}`,
    viewport: { width: 1280, height: 800 },
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: `uv run uvicorn app.main:app --host 127.0.0.1 --port ${port}`,
    cwd: '../backend',
    url: `http://localhost:${port}/api/health`,
    reuseExistingServer: true,
    timeout: 120_000,
  },
})
