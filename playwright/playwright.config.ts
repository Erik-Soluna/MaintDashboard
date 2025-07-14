import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './',
  timeout: 180000, // 3 minutes timeout for each test (increased from 1 minute)
  expect: {
    timeout: 30000, // 30 seconds timeout for expect assertions (increased from 10 seconds)
  },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://web:8000', // Use the Docker service name instead of localhost
    trace: 'on-first-retry',
    actionTimeout: 30000, // 30 seconds for actions like click, fill (increased from 10 seconds)
    navigationTimeout: 60000, // 60 seconds for navigation (increased from 10 seconds)
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
  // Remove webServer section - we'll use the existing Django server
}); 