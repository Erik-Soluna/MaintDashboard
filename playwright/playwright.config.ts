import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './',
  timeout: 60000, // 1 minute timeout for each test
  expect: {
    timeout: 10000, // 10 seconds timeout for expect assertions
  },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:4405',
    trace: 'on-first-retry',
    actionTimeout: 10000, // 10 seconds for actions like click, fill
    navigationTimeout: 10000, // 10 seconds for navigation
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],
  webServer: {
    command: 'echo "Django server should be running on port 4405"',
    url: 'http://localhost:4405',
    reuseExistingServer: !process.env.CI,
    timeout: 10000,
  },
}); 