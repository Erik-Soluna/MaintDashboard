import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:4405';
const ADMIN_USER = 'admin';
const ADMIN_PASS = 'temppass123';

const LOGIN_ONLY = !!process.env.LOGIN_ONLY;
const ADD_EVENT = !!process.env.ADD_EVENT;
const VERIFY_CALENDAR = !!process.env.VERIFY_CALENDAR;
const SCREENSHOT_AFTER = !!process.env.SCREENSHOT_AFTER;

// Helper: Login as admin
async function loginAsAdmin(page) {
  await page.goto(`${BASE_URL}/auth/login/`);
  await page.fill('input[name="username"]', ADMIN_USER);
  await page.fill('input[name="password"]', ADMIN_PASS);
  await page.click('button[type="submit"]');
  await expect(page).not.toHaveURL(/auth\/login/);
}

test('Calendar: Flexible flow with flags', async ({ page }) => {
  // Login
  await loginAsAdmin(page);
  if (LOGIN_ONLY) {
    if (SCREENSHOT_AFTER) await page.screenshot({ path: 'login-only.png', fullPage: true });
    return;
  }

  // Go to calendar
  await page.goto(`${BASE_URL}/events/calendar/`);
  await expect(page.locator('h1, h2, h3')).toContainText(['Calendar', 'Events']);

  if (VERIFY_CALENDAR && !ADD_EVENT) {
    if (SCREENSHOT_AFTER) await page.screenshot({ path: 'calendar-view.png', fullPage: true });
    return;
  }

  // Wait for calendar to load
  await page.waitForSelector('.fc-toolbar');

  if (ADD_EVENT || (!LOGIN_ONLY && !VERIFY_CALENDAR)) {
    // Click to add event (simulate clicking a day cell)
    const dayCell = page.locator('.fc-daygrid-day').first();
    await dayCell.click();

    // Wait for modal to appear
    await page.waitForSelector('.modal.show, .modal-dialog');

    // Fill out event form
    await page.fill('input[name="title"]', 'Playwright Test Event');
    await page.selectOption('select[name="event_type"]', 'maintenance');
    await page.selectOption('select[name="priority"]', 'low');
    // Select first equipment if available
    const equipmentSelect = page.locator('select[name="equipment"]');
    if (await equipmentSelect.count()) {
      const options = await equipmentSelect.locator('option').all();
      if (options.length > 1) {
        await equipmentSelect.selectOption({ index: 1 }); // skip placeholder
      }
    }
    // Set date (today)
    const today = new Date().toISOString().slice(0, 10);
    await page.fill('input[name="date"]', today);
    // Save event
    await page.click('button:has-text("Save Event")');

    // Wait for modal to close and event to appear
    await page.waitForTimeout(2000);
    await expect(page.locator('.fc-event-title')).toContainText('Playwright Test Event');
    if (SCREENSHOT_AFTER) await page.screenshot({ path: 'calendar-after-add.png', fullPage: true });
    return;
  }

  // Default: full flow
  await expect(page.locator('.fc-event-title')).toContainText('Playwright Test Event');
  if (SCREENSHOT_AFTER) await page.screenshot({ path: 'calendar-full-flow.png', fullPage: true });
}); 