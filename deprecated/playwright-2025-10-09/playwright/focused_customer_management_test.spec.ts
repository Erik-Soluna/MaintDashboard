import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:4405';

test('Navigate to Customer Management page as admin', async ({ page }) => {
  // Go to login page
  await page.goto(`${BASE_URL}/auth/login/`);

  // Fill in login form
  await page.fill('input[name="username"]', 'admin');
  await page.fill('input[name="password"]', 'temppass123');
  await page.click('button[type="submit"]');

  // Wait for dashboard to load
  await page.waitForSelector('nav');

  // Click Settings in the nav bar
  await page.click('text=Settings');

  // Click Customers in the dropdown or sidebar
  // Try both direct link and dropdown
  if (await page.isVisible('a[href*="customers"]')) {
    await page.click('a[href*="customers"]');
  } else {
    // Fallback: try clicking via menu
    await page.click('text=Customers');
  }

  // Wait for Customer Management heading
  await page.waitForSelector('h2:has-text("Customer Management")');

  // Assert the heading is present
  const heading = await page.textContent('h2');
  expect(heading).toContain('Customer Management');

  // Optionally, check for the Add Customer button
  await expect(page.locator('button, a').filter({ hasText: '+Add Customer' })).toBeVisible();
}); 