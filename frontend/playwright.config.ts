import { defineConfig, devices } from '@playwright/test'

// e2e contra la app servida por FastAPI (correr antes `bash scripts/build_frontend.sh`).
export default defineConfig({
  testDir: './e2e',
  outputDir: './test-results/artifacts',
  timeout: 60_000,
  use: {
    baseURL: 'http://localhost:8000',
    viewport: { width: 1280, height: 800 },
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'uv run --project ../backend python -m app.run',
    cwd: '../backend',
    env: { NO_BROWSER: '1' },
    url: 'http://localhost:8000/api/health',
    reuseExistingServer: true,
    timeout: 120_000,
  },
})
