import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright E2E Test Configuration for ElohimOS Frontend
 *
 * Tests require both backend and frontend servers to be running:
 * - Backend: http://localhost:8000
 * - Frontend: http://localhost:4200
 */
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',

  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:4200',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // Optionally start dev server if not running
  // Commented out by default - run servers manually for faster iteration
  // webServer: {
  //   command: 'npm run dev',
  //   url: 'http://localhost:4200',
  //   reuseExistingServer: !process.env.CI,
  //   timeout: 120 * 1000,
  // },
})
