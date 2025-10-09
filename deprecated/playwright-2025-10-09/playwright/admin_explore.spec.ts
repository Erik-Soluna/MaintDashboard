import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

interface TestResult {
  page: string;
  timestamp: string;
  elementsFound: number;
  elementsClicked: number;
  errors: string[];
  warnings: string[];
  screenshots: string[];
  htmlDumps: string[];
}

class WebAppExplorer {
  private results: TestResult[] = [];
  private screenshotDir: string;
  private htmlDir: string;

  constructor() {
    this.screenshotDir = path.join(__dirname, 'screenshots', 'webapp-exploration');
    this.htmlDir = path.join(__dirname, 'html-dumps', 'webapp-exploration');
    
    // Ensure directories exist
    [this.screenshotDir, this.htmlDir].forEach(dir => {
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
    });
  }

  private async takeScreenshot(page: any, name: string): Promise<string> {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `${name}_${timestamp}.png`;
    const filepath = path.join(this.screenshotDir, filename);
    await page.screenshot({ path: filepath, fullPage: true });
    return filepath;
  }

  private async dumpHTML(page: any, name: string): Promise<string> {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `${name}_${timestamp}.html`;
    const filepath = path.join(this.htmlDir, filename);
    const html = await page.content();
    fs.writeFileSync(filepath, html);
    return filepath;
  }

  private async logResult(result: TestResult) {
    this.results.push(result);
    console.log(`\n=== ${result.page} ===`);
    console.log(`Elements found: ${result.elementsFound}`);
    console.log(`Elements clicked: ${result.elementsClicked}`);
    console.log(`Screenshots: ${result.screenshots.length}`);
    console.log(`HTML dumps: ${result.htmlDumps.length}`);
    
    if (result.errors.length > 0) {
      console.log(`\n❌ Errors (${result.errors.length}):`);
      result.errors.forEach(error => console.log(`  - ${error}`));
    }
    
    if (result.warnings.length > 0) {
      console.log(`\n⚠️  Warnings (${result.warnings.length}):`);
      result.warnings.forEach(warning => console.log(`  - ${warning}`));
    }
  }

  private async findAndClickElements(page: any, pageName: string): Promise<TestResult> {
    const result: TestResult = {
      page: pageName,
      timestamp: new Date().toISOString(),
      elementsFound: 0,
      elementsClicked: 0,
      errors: [],
      warnings: [],
      screenshots: [],
      htmlDumps: []
    };

    try {
      // Wait for page to load
      await page.waitForLoadState('networkidle');
      
      // Take initial screenshot
      result.screenshots.push(await this.takeScreenshot(page, `${pageName}_initial`));
      
      // Find all interactive elements
      const selectors = [
        'button:not([disabled])',
        'input[type="submit"]:not([disabled])',
        'input[type="button"]:not([disabled])',
        'a[role="button"]:not([disabled])',
        'a.btn:not([disabled])',
        'a.button:not([disabled])',
        '.btn:not([disabled])',
        '.button:not([disabled])',
        '[onclick]:not([disabled])',
        'select:not([disabled])',
        'input[type="checkbox"]:not([disabled])',
        'input[type="radio"]:not([disabled])',
        '.dropdown-toggle:not([disabled])',
        '.nav-link:not([disabled])',
        '.tab-link:not([disabled])',
        '.accordion-button:not([disabled])',
        '.expand-button:not([disabled])',
        '.toggle-button:not([disabled])'
      ];

      const allElements = await page.$$(selectors.join(', '));
      result.elementsFound = allElements.length;
      
      console.log(`\n🔍 Found ${allElements.length} interactive elements on ${pageName}`);

      // Process each element
      for (let i = 0; i < allElements.length; i++) {
        const element = allElements[i];
        
        try {
          // Get element info
          const tagName = await element.evaluate(el => el.tagName.toLowerCase());
          const text = await element.textContent() || '';
          const type = await element.getAttribute('type') || '';
          const className = await element.getAttribute('class') || '';
          const id = await element.getAttribute('id') || '';
          const href = await element.getAttribute('href') || '';
          
          const elementInfo = `${tagName}${type ? `[type="${type}"]` : ''}${id ? `#${id}` : ''}${className ? `.${className.split(' ')[0]}` : ''}${text ? ` "${text.trim().substring(0, 50)}"` : ''}`;
          
          console.log(`\n${i + 1}/${allElements.length}: Clicking ${elementInfo}`);
          
          // Check if element is visible and clickable
          const isVisible = await element.isVisible();
          if (!isVisible) {
            console.log(`  ⚠️  Element not visible, skipping`);
            result.warnings.push(`Element not visible: ${elementInfo}`);
            continue;
          }

          // Scroll element into view
          await element.scrollIntoViewIfNeeded();
          await page.waitForTimeout(500);

          // Take screenshot before click
          const beforeScreenshot = await this.takeScreenshot(page, `${pageName}_before_click_${i + 1}`);
          result.screenshots.push(beforeScreenshot);

          // Click the element
          await element.click({ timeout: 10000 });
          result.elementsClicked++;
          
          console.log(`  ✅ Clicked successfully`);
          
          // Wait for any potential changes
          await page.waitForTimeout(2000);
          
          // Check for new content, modals, or page changes
          const newElements = await page.$$(selectors.join(', '));
          if (newElements.length > allElements.length) {
            console.log(`  📈 New elements appeared: ${newElements.length - allElements.length}`);
            result.warnings.push(`New elements appeared after clicking ${elementInfo}: ${newElements.length - allElements.length} new elements`);
          }

          // Take screenshot after click
          const afterScreenshot = await this.takeScreenshot(page, `${pageName}_after_click_${i + 1}`);
          result.screenshots.push(afterScreenshot);

          // Check for errors or alerts
          const alerts = await page.$$('.alert, .error, .warning, .danger, .success');
          if (alerts.length > 0) {
            for (const alert of alerts) {
              const alertText = await alert.textContent();
              console.log(`  📢 Alert found: ${alertText}`);
              result.warnings.push(`Alert after clicking ${elementInfo}: ${alertText}`);
            }
          }

          // Check for modals
          const modals = await page.$$('.modal, .popup, .dialog, [role="dialog"]');
          if (modals.length > 0) {
            console.log(`  🪟 Modal detected, attempting to close`);
            result.warnings.push(`Modal appeared after clicking ${elementInfo}`);
            
            // Try to close modal
            const closeButtons = await page.$$('.modal .close, .modal .btn-close, .popup .close, [data-dismiss="modal"]');
            for (const closeBtn of closeButtons) {
              if (await closeBtn.isVisible()) {
                await closeBtn.click();
                await page.waitForTimeout(500);
                break;
              }
            }
          }

          // Check for page navigation
          const currentUrl = page.url();
          const originalUrl = await page.evaluate(() => window.location.href);
          
          // Wait a bit and check if URL changed
          await page.waitForTimeout(1000);
          const newUrl = page.url();
          
          if (newUrl !== originalUrl) {
            console.log(`  🔄 Page navigated to: ${newUrl}`);
            result.warnings.push(`Page navigation after clicking ${elementInfo}: ${newUrl}`);
            
            // Go back if possible
            try {
              await page.goBack();
              await page.waitForLoadState('networkidle');
              console.log(`  ↩️  Navigated back to: ${page.url()}`);
            } catch (navError) {
              console.log(`  ⚠️  Could not navigate back: ${navError}`);
              result.warnings.push(`Could not navigate back after clicking ${elementInfo}: ${navError}`);
            }
          }

        } catch (error) {
          const errorMsg = `Failed to click element ${i + 1}: ${error}`;
          console.log(`  ❌ ${errorMsg}`);
          result.errors.push(errorMsg);
          
          // Check if page context was destroyed
          if (error.message.includes('Execution context was destroyed') || 
              error.message.includes('Target page, context or browser has been closed')) {
            console.log(`  🔄 Page context destroyed, attempting to recover...`);
            result.warnings.push(`Page context destroyed after clicking element ${i + 1}, attempting recovery`);
            
            // Try to recover by refreshing the page
            try {
              await page.reload();
              await page.waitForLoadState('networkidle');
              console.log(`  ✅ Page recovered successfully`);
            } catch (recoveryError) {
              console.log(`  ❌ Could not recover page: ${recoveryError}`);
              result.errors.push(`Page recovery failed: ${recoveryError}`);
              break; // Exit the loop if we can't recover
            }
          } else {
            // Take error screenshot for other types of errors
            try {
              result.screenshots.push(await this.takeScreenshot(page, `${pageName}_error_click_${i + 1}`));
            } catch (screenshotError) {
              console.log(`  ⚠️  Could not take error screenshot: ${screenshotError}`);
            }
          }
        }
      }

      // Final screenshot and HTML dump
      result.screenshots.push(await this.takeScreenshot(page, `${pageName}_final`));
      result.htmlDumps.push(await this.dumpHTML(page, pageName));

    } catch (error) {
      result.errors.push(`Page exploration failed: ${error}`);
      result.screenshots.push(await this.takeScreenshot(page, `${pageName}_error`));
      result.htmlDumps.push(await this.dumpHTML(page, `${pageName}_error`));
    }

    return result;
  }

  async exploreWebApp(page: any) {
    console.log('🚀 Starting comprehensive web app exploration...');
    
    // First explore public pages without login
    console.log('\n🔓 Exploring public pages (without login)...');
    await page.goto('http://localhost:4405/');
    await page.waitForLoadState('networkidle');

    // Define public pages to explore first
    const publicPages = [
      { url: '/', name: 'Home Page (Public)' },
      { url: '/auth/login/', name: 'Login Page' },
      { url: '/auth/register/', name: 'Register Page' }
    ];

    // Explore public pages
    for (const publicPage of publicPages) {
      try {
        console.log(`\n📄 Exploring: ${publicPage.name} (${publicPage.url})`);
        await page.goto(`http://localhost:4405${publicPage.url}`);
        await page.waitForLoadState('networkidle');
        
        const result = await this.findAndClickElements(page, publicPage.name);
        await this.logResult(result);
        
      } catch (error) {
        console.log(`❌ Failed to explore ${publicPage.name}: ${error}`);
        this.results.push({
          page: publicPage.name,
          timestamp: new Date().toISOString(),
          elementsFound: 0,
          elementsClicked: 0,
          errors: [`Failed to load page: ${error}`],
          warnings: [],
          screenshots: [],
          htmlDumps: []
        });
      }
    }

    // Now login and explore protected pages
    console.log('\n🔐 Logging in to explore protected pages...');
    await page.goto('http://localhost:4405/auth/login/');
    await page.waitForLoadState('networkidle');
    
    // Try to login
    try {
      await page.fill('#id_username', 'admin');
      await page.fill('#id_password', 'temppass123');
      await page.click('input[type="submit"]');
      await page.waitForLoadState('networkidle');
      console.log('✅ Login successful');
    } catch (loginError) {
      console.log(`❌ Login failed: ${loginError}`);
      // Continue with public exploration if login fails
    }

    // Define protected pages to explore after login
    const protectedPages = [
      { url: '/dashboard/', name: 'Dashboard (Protected)' },
      { url: '/equipment/', name: 'Equipment List (Protected)' },
      { url: '/equipment/add/', name: 'Add Equipment' },
      { url: '/maintenance/', name: 'Maintenance List (Protected)' },
      { url: '/maintenance/add/', name: 'Add Maintenance' },
      { url: '/maintenance/schedules/', name: 'Maintenance Schedules' },
      { url: '/maintenance/activities/', name: 'Maintenance Activities' },
      { url: '/events/', name: 'Events Calendar (Protected)' },
      { url: '/events/add/', name: 'Add Event' },
      { url: '/customers/', name: 'Customers (Protected)' },
      { url: '/locations/', name: 'Locations (Protected)' },
      { url: '/profile/', name: 'User Profile (Protected)' },
      { url: '/settings/', name: 'Settings (Protected)' },
      { url: '/reports/', name: 'Reports (Protected)' },
      { url: '/system-health/', name: 'System Health (Protected)' }
    ];

    // Explore protected pages
    for (const protectedPage of protectedPages) {
      try {
        console.log(`\n📄 Exploring: ${protectedPage.name} (${protectedPage.url})`);
        await page.goto(`http://localhost:4405${protectedPage.url}`);
        await page.waitForLoadState('networkidle');
        
        const result = await this.findAndClickElements(page, protectedPage.name);
        await this.logResult(result);
        
      } catch (error) {
        console.log(`❌ Failed to explore ${protectedPage.name}: ${error}`);
        this.results.push({
          page: protectedPage.name,
          timestamp: new Date().toISOString(),
          elementsFound: 0,
          elementsClicked: 0,
          errors: [`Failed to load page: ${error}`],
          warnings: [],
          screenshots: [],
          htmlDumps: []
        });
      }
    }

    // Generate comprehensive report
    await this.generateReport();
  }

  private async generateReport() {
    const report = {
      timestamp: new Date().toISOString(),
      totalPages: this.results.length,
      totalElementsFound: this.results.reduce((sum, r) => sum + r.elementsFound, 0),
      totalElementsClicked: this.results.reduce((sum, r) => sum + r.elementsClicked, 0),
      totalErrors: this.results.reduce((sum, r) => sum + r.errors.length, 0),
      totalWarnings: this.results.reduce((sum, r) => sum + r.warnings.length, 0),
      totalScreenshots: this.results.reduce((sum, r) => sum + r.screenshots.length, 0),
      results: this.results
    };

    const reportPath = path.join(__dirname, 'webapp-exploration-report.json');
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));

    console.log('\n📊 COMPREHENSIVE WEB APP EXPLORATION REPORT');
    console.log('============================================');
    console.log(`Total pages explored: ${report.totalPages}`);
    console.log(`Total elements found: ${report.totalElementsFound}`);
    console.log(`Total elements clicked: ${report.totalElementsClicked}`);
    console.log(`Total errors: ${report.totalErrors}`);
    console.log(`Total warnings: ${report.totalWarnings}`);
    console.log(`Total screenshots: ${report.totalScreenshots}`);
    console.log(`\nDetailed report saved to: ${reportPath}`);
    
    if (report.totalErrors > 0) {
      console.log('\n🚨 CRITICAL ISSUES FOUND:');
      this.results.forEach(result => {
        if (result.errors.length > 0) {
          console.log(`\n${result.page}:`);
          result.errors.forEach(error => console.log(`  ❌ ${error}`));
        }
      });
    }
  }
}

test('Comprehensive Web App Exploration', async ({ page }) => {
  // Increase timeout for comprehensive exploration
  test.setTimeout(120000); // 2 minutes
  
  const explorer = new WebAppExplorer();
  await explorer.exploreWebApp(page);
}); 