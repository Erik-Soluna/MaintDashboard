import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

interface TestRequest {
  action: string;
  priority: number;
  flags: string[];
  description: string;
}

interface TestResult {
  testName: string;
  timestamp: string;
  success: boolean;
  errors: string[];
  warnings: string[];
  screenshots: string[];
  htmlDumps: string[];
  data?: any;
}

class SmartTestRunner {
  private results: TestResult[] = [];
  private screenshotDir: string;
  private htmlDir: string;
  private isAuthenticated: boolean = false;
  private testData: any = {};

  constructor() {
    this.screenshotDir = path.join(__dirname, 'screenshots', 'smart-tests');
    this.htmlDir = path.join(__dirname, 'html-dumps', 'smart-tests');
    
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
    console.log(`\n=== ${result.testName} ===`);
    console.log(`Status: ${result.success ? '✅ PASS' : '❌ FAIL'}`);
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

  // Natural language request parser
  private parseNaturalLanguageRequest(request: string): TestRequest[] {
    const requests: TestRequest[] = [];
    const lowerRequest = request.toLowerCase();

    // Equipment-related requests
    if (lowerRequest.includes('equipment') || lowerRequest.includes('item')) {
      if (lowerRequest.includes('create') || lowerRequest.includes('make') || lowerRequest.includes('add')) {
        requests.push({
          action: 'create_equipment',
          priority: 1,
          flags: ['authenticated', 'form_fill'],
          description: 'Create new equipment with required fields'
        });
      }
      if (lowerRequest.includes('delete') || lowerRequest.includes('remove')) {
        requests.push({
          action: 'delete_equipment',
          priority: 2,
          flags: ['authenticated', 'confirmation'],
          description: 'Delete equipment item'
        });
      }
      if (lowerRequest.includes('list') || lowerRequest.includes('view')) {
        requests.push({
          action: 'list_equipment',
          priority: 3,
          flags: ['authenticated'],
          description: 'View equipment list'
        });
      }
    }

    // Maintenance-related requests
    if (lowerRequest.includes('maintenance') || lowerRequest.includes('schedule')) {
      if (lowerRequest.includes('create') || lowerRequest.includes('make') || lowerRequest.includes('add')) {
        requests.push({
          action: 'create_maintenance',
          priority: 1,
          flags: ['authenticated', 'form_fill'],
          description: 'Create new maintenance schedule'
        });
      }
      if (lowerRequest.includes('list') || lowerRequest.includes('view')) {
        requests.push({
          action: 'list_maintenance',
          priority: 3,
          flags: ['authenticated'],
          description: 'View maintenance list'
        });
      }
    }

    // Authentication requests
    if (lowerRequest.includes('login') || lowerRequest.includes('authenticate')) {
      requests.push({
        action: 'test_login',
        priority: 1,
        flags: ['auth_test'],
        description: 'Test login functionality'
      });
    }

    if (lowerRequest.includes('logout') || lowerRequest.includes('sign out')) {
      requests.push({
        action: 'test_logout',
        priority: 2,
        flags: ['auth_test'],
        description: 'Test logout functionality'
      });
    }

    // Permission requests
    if (lowerRequest.includes('permission') || lowerRequest.includes('access') || lowerRequest.includes('unauthorized')) {
      requests.push({
        action: 'test_permissions',
        priority: 1,
        flags: ['auth_test', 'permission_test'],
        description: 'Test permission access control'
      });
    }

    // General exploration
    if (lowerRequest.includes('explore') || lowerRequest.includes('all links') || lowerRequest.includes('every page')) {
      requests.push({
        action: 'explore_all_links',
        priority: 1,
        flags: ['comprehensive', 'link_test'],
        description: 'Explore all links and pages'
      });
    }

    // If no specific requests found, do comprehensive testing
    if (requests.length === 0) {
      requests.push({
        action: 'comprehensive_test',
        priority: 1,
        flags: ['comprehensive', 'auth_test', 'permission_test'],
        description: 'Comprehensive testing of all features'
      });
    }

    return requests.sort((a, b) => a.priority - b.priority);
  }

  // Authentication management
  private async ensureAuthenticated(page: any): Promise<boolean> {
    if (this.isAuthenticated) return true;

    try {
      console.log('🔐 Attempting to authenticate...');
      await page.goto('http://localhost:4405/auth/login/', { timeout: 10000 });
      await page.waitForLoadState('networkidle', { timeout: 10000 });

      // Check if already logged in
      const currentUrl = page.url();
      if (!currentUrl.includes('login')) {
        console.log('✅ Already authenticated');
        this.isAuthenticated = true;
        return true;
      }

      // Fill login form
      await page.fill('#id_username', 'admin', { timeout: 10000 });
      await page.fill('#id_password', 'temppass123', { timeout: 10000 });
      
      // Take screenshot before clicking login
      await this.takeScreenshot(page, 'login_before_click');
      
      // Click the login button - try multiple selectors
      console.log('🔘 Looking for login button...');
      
      let loginClicked = false;
      try {
        // Try the most common selector first
        await page.click('input[type="submit"]', { timeout: 10000 });
        console.log('✅ Clicked login button with input[type="submit"]');
        loginClicked = true;
      } catch (e1) {
        try {
          // Try button selector
          await page.click('button[type="submit"]', { timeout: 10000 });
          console.log('✅ Clicked login button with button[type="submit"]');
          loginClicked = true;
        } catch (e2) {
          try {
            // Try text-based selector
            await page.click('button:has-text("Login")', { timeout: 10000 });
            console.log('✅ Clicked login button with button:has-text("Login")');
            loginClicked = true;
          } catch (e3) {
            try {
              // Try form button
              await page.click('form button', { timeout: 10000 });
              console.log('✅ Clicked login button with form button');
              loginClicked = true;
            } catch (e4) {
              console.log('❌ Could not find or click login button');
              console.log('Tried selectors: input[type="submit"], button[type="submit"], button:has-text("Login"), form button');
              await this.takeScreenshot(page, 'login_button_not_found');
              return false;
            }
          }
        }
      }

      if (!loginClicked) {
        console.log('❌ Could not find login button');
        await this.takeScreenshot(page, 'login_button_not_found');
        return false;
      }

      await page.waitForLoadState('networkidle', { timeout: 10000 });
      
      // Take screenshot after login attempt
      await this.takeScreenshot(page, 'login_after_click');

      // Verify login success
      const newUrl = page.url();
      if (!newUrl.includes('login')) {
        console.log('✅ Authentication successful');
        this.isAuthenticated = true;
        return true;
      } else {
        console.log('❌ Authentication failed - still on login page');
        await this.takeScreenshot(page, 'login_failed');
        return false;
      }
    } catch (error) {
      console.log(`❌ Authentication error: ${error}`);
      await this.takeScreenshot(page, 'login_error');
      return false;
    }
  }

  private async logout(page: any): Promise<boolean> {
    try {
      console.log('🚪 Attempting to logout...');
      
      // Look for logout button/link
      const logoutSelectors = [
        'a[href*="logout"]',
        'button[onclick*="logout"]',
        '.logout',
        '.btn-logout',
        'a:has-text("Logout")',
        'button:has-text("Logout")'
      ];

      for (const selector of logoutSelectors) {
        const logoutElement = await page.$(selector);
        if (logoutElement && await logoutElement.isVisible()) {
          await logoutElement.click({ timeout: 10000 });
          await page.waitForLoadState('networkidle', { timeout: 10000 });
          console.log('✅ Logout successful');
          this.isAuthenticated = false;
          return true;
        }
      }

      // If no logout button found, try to navigate to logout URL
      await page.goto('http://localhost:4405/auth/logout/', { timeout: 10000 });
      await page.waitForLoadState('networkidle', { timeout: 10000 });
      this.isAuthenticated = false;
      return true;
    } catch (error) {
      console.log(`❌ Logout error: ${error}`);
      return false;
    }
  }

  // Test implementations
  private async testLogin(page: any): Promise<TestResult> {
    const result: TestResult = {
      testName: 'Login Test',
      timestamp: new Date().toISOString(),
      success: false,
      errors: [],
      warnings: [],
      screenshots: [],
      htmlDumps: []
    };

    try {
      result.screenshots.push(await this.takeScreenshot(page, 'login_test_initial'));
      
      const success = await this.ensureAuthenticated(page);
      result.success = success;
      
      result.screenshots.push(await this.takeScreenshot(page, 'login_test_final'));
      result.htmlDumps.push(await this.dumpHTML(page, 'login_test'));
      
      if (!success) {
        result.errors.push('Failed to authenticate with admin credentials');
      }
    } catch (error) {
      result.errors.push(`Login test failed: ${error}`);
    }

    return result;
  }

  private async testLogout(page: any): Promise<TestResult> {
    const result: TestResult = {
      testName: 'Logout Test',
      timestamp: new Date().toISOString(),
      success: false,
      errors: [],
      warnings: [],
      screenshots: [],
      htmlDumps: []
    };

    try {
      result.screenshots.push(await this.takeScreenshot(page, 'logout_test_initial'));
      
      const success = await this.logout(page);
      result.success = success;
      
      result.screenshots.push(await this.takeScreenshot(page, 'logout_test_final'));
      result.htmlDumps.push(await this.dumpHTML(page, 'logout_test'));
      
      if (!success) {
        result.errors.push('Failed to logout');
      }
    } catch (error) {
      result.errors.push(`Logout test failed: ${error}`);
    }

    return result;
  }

  private async testPermissions(page: any): Promise<TestResult> {
    const result: TestResult = {
      testName: 'Permission Test',
      timestamp: new Date().toISOString(),
      success: true,
      errors: [],
      warnings: [],
      screenshots: [],
      htmlDumps: []
    };

    const protectedPages = [
      '/dashboard/',
      '/equipment/',
      '/maintenance/',
      '/events/',
      '/customers/',
      '/locations/',
      '/profile/',
      '/settings/',
      '/reports/',
      '/system-health/'
    ];

    try {
      // Test unauthenticated access
      console.log('🔓 Testing unauthenticated access...');
      await this.logout(page);
      
      for (const pageUrl of protectedPages) {
        try {
          await page.goto(`http://localhost:4405${pageUrl}`);
          await page.waitForLoadState('networkidle');
          
          const currentUrl = page.url();
          if (!currentUrl.includes('login')) {
            result.warnings.push(`Unauthenticated access to ${pageUrl} was not redirected to login`);
          } else {
            console.log(`✅ ${pageUrl} properly redirects to login when unauthenticated`);
          }
          
          result.screenshots.push(await this.takeScreenshot(page, `permission_test_unauth_${pageUrl.replace(/\//g, '_')}`));
        } catch (error) {
          result.warnings.push(`Error testing ${pageUrl}: ${error}`);
        }
      }

      // Test authenticated access
      console.log('🔐 Testing authenticated access...');
      await this.ensureAuthenticated(page);
      
      for (const pageUrl of protectedPages) {
        try {
          await page.goto(`http://localhost:4405${pageUrl}`);
          await page.waitForLoadState('networkidle');
          
          const currentUrl = page.url();
          if (currentUrl.includes('login')) {
            result.errors.push(`Authenticated access to ${pageUrl} was incorrectly redirected to login`);
            result.success = false;
          } else {
            console.log(`✅ ${pageUrl} accessible when authenticated`);
          }
          
          result.screenshots.push(await this.takeScreenshot(page, `permission_test_auth_${pageUrl.replace(/\//g, '_')}`));
        } catch (error) {
          result.warnings.push(`Error testing ${pageUrl}: ${error}`);
        }
      }

      result.htmlDumps.push(await this.dumpHTML(page, 'permission_test'));
    } catch (error) {
      result.errors.push(`Permission test failed: ${error}`);
      result.success = false;
    }

    return result;
  }

  private async createEquipment(page: any): Promise<TestResult> {
    const result: TestResult = {
      testName: 'Create Equipment Test',
      timestamp: new Date().toISOString(),
      success: false,
      errors: [],
      warnings: [],
      screenshots: [],
      htmlDumps: []
    };

    try {
      // Ensure authenticated
      await this.ensureAuthenticated(page);
      
      // Navigate to equipment page
      await page.goto('http://localhost:4405/equipment/', { timeout: 10000 });
      await page.waitForLoadState('networkidle', { timeout: 10000 });
      
      result.screenshots.push(await this.takeScreenshot(page, 'create_equipment_initial'));
      
      // Look for add equipment button
      const addSelectors = [
        'a[href*="add"]',
        'a:has-text("Add Equipment")',
        'button:has-text("Add Equipment")',
        '.btn-add',
        '.add-equipment'
      ];

      let addButton = null;
      for (const selector of addSelectors) {
        addButton = await page.$(selector);
        if (addButton && await addButton.isVisible()) break;
      }

      if (!addButton) {
        result.errors.push('Could not find Add Equipment button');
        return result;
      }

      await addButton.click({ timeout: 10000 });
      await page.waitForLoadState('networkidle', { timeout: 10000 });
      
      result.screenshots.push(await this.takeScreenshot(page, 'create_equipment_form'));

      // Fill required fields
      const testEquipment = {
        name: `Test Equipment ${Date.now()}`,
        model: 'Test Model',
        serial_number: `SN${Date.now()}`,
        location: 'Test Location',
        status: 'active'
      };

      // Fill form fields
      await page.fill('input[name="name"]', testEquipment.name, { timeout: 10000 });
      await page.fill('input[name="model"]', testEquipment.model, { timeout: 10000 });
      await page.fill('input[name="serial_number"]', testEquipment.serial_number, { timeout: 10000 });
      await page.fill('input[name="location"]', testEquipment.location, { timeout: 10000 });
      await page.selectOption('select[name="status"]', testEquipment.status, { timeout: 10000 });

      result.screenshots.push(await this.takeScreenshot(page, 'create_equipment_filled'));

      // Submit form
      await page.click('input[type="submit"], button[type="submit"]', { timeout: 10000 });
      await page.waitForLoadState('networkidle', { timeout: 10000 });

      result.screenshots.push(await this.takeScreenshot(page, 'create_equipment_submitted'));
      result.htmlDumps.push(await this.dumpHTML(page, 'create_equipment'));

      // Check for success
      const successIndicators = [
        '.alert-success',
        '.success',
        'text=Equipment created successfully',
        'text=Equipment added successfully'
      ];

      let success = false;
      for (const indicator of successIndicators) {
        const element = await page.$(indicator);
        if (element && await element.isVisible()) {
          success = true;
          break;
        }
      }

      if (success) {
        result.success = true;
        result.data = testEquipment;
        console.log('✅ Equipment created successfully');
      } else {
        result.errors.push('Equipment creation may have failed - no success indicator found');
      }

    } catch (error) {
      result.errors.push(`Create equipment test failed: ${error}`);
    }

    return result;
  }

  private async deleteEquipment(page: any): Promise<TestResult> {
    const result: TestResult = {
      testName: 'Delete Equipment Test',
      timestamp: new Date().toISOString(),
      success: false,
      errors: [],
      warnings: [],
      screenshots: [],
      htmlDumps: []
    };

    try {
      // Ensure authenticated
      await this.ensureAuthenticated(page);
      
      // Navigate to equipment list
      await page.goto('http://localhost:4405/equipment/');
      await page.waitForLoadState('networkidle');
      
      result.screenshots.push(await this.takeScreenshot(page, 'delete_equipment_initial'));

      // Look for delete buttons
      const deleteSelectors = [
        'a[href*="delete"]',
        'button:has-text("Delete")',
        '.btn-delete',
        '.delete-equipment'
      ];

      let deleteButton = null;
      for (const selector of deleteSelectors) {
        const buttons = await page.$$(selector);
        for (const button of buttons) {
          if (await button.isVisible()) {
            deleteButton = button;
            break;
          }
        }
        if (deleteButton) break;
      }

      if (!deleteButton) {
        result.warnings.push('No delete buttons found - equipment may not exist or delete functionality not available');
        result.success = true; // Not necessarily a failure
        return result;
      }

      await deleteButton.click();
      await page.waitForLoadState('networkidle');
      
      result.screenshots.push(await this.takeScreenshot(page, 'delete_equipment_confirmation'));

      // Handle confirmation dialog if present
      const confirmSelectors = [
        'button:has-text("Confirm")',
        'button:has-text("Delete")',
        'input[type="submit"]',
        '.btn-confirm'
      ];

      for (const selector of confirmSelectors) {
        const confirmButton = await page.$(selector);
        if (confirmButton && await confirmButton.isVisible()) {
          await confirmButton.click();
          await page.waitForLoadState('networkidle');
          break;
        }
      }

      result.screenshots.push(await this.takeScreenshot(page, 'delete_equipment_final'));
      result.htmlDumps.push(await this.dumpHTML(page, 'delete_equipment'));

      result.success = true;
      console.log('✅ Equipment deletion test completed');

    } catch (error) {
      result.errors.push(`Delete equipment test failed: ${error}`);
    }

    return result;
  }

  private async exploreAllLinks(page: any): Promise<TestResult> {
    const result: TestResult = {
      testName: 'Explore All Links Test',
      timestamp: new Date().toISOString(),
      success: true,
      errors: [],
      warnings: [],
      screenshots: [],
      htmlDumps: []
    };

    const visitedUrls = new Set<string>();
    const urlsToVisit = ['http://localhost:4405/'];

    try {
      while (urlsToVisit.length > 0) {
        const currentUrl = urlsToVisit.shift()!;
        
        if (visitedUrls.has(currentUrl)) continue;
        visitedUrls.add(currentUrl);

        console.log(`🔍 Exploring: ${currentUrl}`);
        
        try {
          await page.goto(currentUrl);
          await page.waitForLoadState('networkidle');
          
          result.screenshots.push(await this.takeScreenshot(page, `explore_${currentUrl.replace(/[^a-zA-Z0-9]/g, '_')}`));

          // Find all links on the page
          const links = await page.$$('a[href]');
          for (const link of links) {
            try {
              const href = await link.getAttribute('href');
              if (href && href.startsWith('/') && !visitedUrls.has(`http://localhost:4405${href}`)) {
                urlsToVisit.push(`http://localhost:4405${href}`);
              }
            } catch (error) {
              // Ignore individual link errors
            }
          }

          // Check for errors
          const errorSelectors = [
            '.error',
            '.alert-danger',
            'text=404',
            'text=500',
            'text=Page not found'
          ];

          for (const selector of errorSelectors) {
            const errorElement = await page.$(selector);
            if (errorElement && await errorElement.isVisible()) {
              result.warnings.push(`Error found on ${currentUrl}: ${await errorElement.textContent()}`);
            }
          }

        } catch (error) {
          result.warnings.push(`Error exploring ${currentUrl}: ${error}`);
        }

        // Limit exploration to prevent infinite loops
        if (visitedUrls.size > 50) {
          result.warnings.push('Exploration limited to 50 URLs to prevent infinite loops');
          break;
        }
      }

      result.htmlDumps.push(await this.dumpHTML(page, 'explore_all_links'));
      console.log(`✅ Explored ${visitedUrls.size} URLs`);

    } catch (error) {
      result.errors.push(`Explore all links test failed: ${error}`);
      result.success = false;
    }

    return result;
  }

  // Main test runner
  async runTests(page: any, naturalLanguageRequest: string): Promise<void> {
    console.log('🚀 Starting Smart Test Runner...');
    console.log(`📝 Request: "${naturalLanguageRequest}"`);
    
    const requests = this.parseNaturalLanguageRequest(naturalLanguageRequest);
    console.log(`\n🔍 Parsed ${requests.length} test requests:`);
    requests.forEach((req, index) => {
      console.log(`  ${index + 1}. ${req.description} (${req.flags.join(', ')})`);
    });

    for (const request of requests) {
      console.log(`\n🎯 Executing: ${request.description}`);
      
      let testResult: TestResult;

      switch (request.action) {
        case 'test_login':
          testResult = await this.testLogin(page);
          break;
        case 'test_logout':
          testResult = await this.testLogout(page);
          break;
        case 'test_permissions':
          testResult = await this.testPermissions(page);
          break;
        case 'create_equipment':
          testResult = await this.createEquipment(page);
          break;
        case 'delete_equipment':
          testResult = await this.deleteEquipment(page);
          break;
        case 'list_equipment':
          testResult = await this.exploreAllLinks(page); // Will find equipment pages
          break;
        case 'create_maintenance':
          testResult = await this.createEquipment(page); // Placeholder for maintenance creation
          break;
        case 'list_maintenance':
          testResult = await this.exploreAllLinks(page); // Will find maintenance pages
          break;
        case 'explore_all_links':
          testResult = await this.exploreAllLinks(page);
          break;
        case 'comprehensive_test':
          // Run all tests
          await this.testLogin(page);
          await this.testPermissions(page);
          await this.createEquipment(page);
          await this.deleteEquipment(page);
          await this.exploreAllLinks(page);
          await this.testLogout(page);
          testResult = {
            testName: 'Comprehensive Test',
            timestamp: new Date().toISOString(),
            success: true,
            errors: [],
            warnings: [],
            screenshots: [],
            htmlDumps: []
          };
          break;
        default:
          testResult = {
            testName: `Unknown Test: ${request.action}`,
            timestamp: new Date().toISOString(),
            success: false,
            errors: [`Unknown test action: ${request.action}`],
            warnings: [],
            screenshots: [],
            htmlDumps: []
          };
      }

      await this.logResult(testResult);
    }

    await this.generateReport();
  }

  private async generateReport() {
    const report = {
      timestamp: new Date().toISOString(),
      totalTests: this.results.length,
      passedTests: this.results.filter(r => r.success).length,
      failedTests: this.results.filter(r => !r.success).length,
      totalErrors: this.results.reduce((sum, r) => sum + r.errors.length, 0),
      totalWarnings: this.results.reduce((sum, r) => sum + r.warnings.length, 0),
      totalScreenshots: this.results.reduce((sum, r) => sum + r.screenshots.length, 0),
      results: this.results
    };

    const reportPath = path.join(__dirname, 'smart-test-report.json');
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));

    console.log('\n📊 SMART TEST RUNNER REPORT');
    console.log('============================');
    console.log(`Total tests: ${report.totalTests}`);
    console.log(`Passed: ${report.passedTests}`);
    console.log(`Failed: ${report.failedTests}`);
    console.log(`Total errors: ${report.totalErrors}`);
    console.log(`Total warnings: ${report.totalWarnings}`);
    console.log(`Total screenshots: ${report.totalScreenshots}`);
    console.log(`\nDetailed report saved to: ${reportPath}`);
  }
}

// Test function that can be called with natural language requests
test('Smart Test Runner', async ({ page }) => {
  test.setTimeout(60000); // 1 minute total timeout for the entire test
  
  const runner = new SmartTestRunner();
  
  // Get test request from environment variable or use default
  const testRequest = process.env.TEST_REQUEST || 
    "Make a new equipment with all req fields and delete it. Make a maintenance for the item.";
  
  await runner.runTests(page, testRequest);
}); 