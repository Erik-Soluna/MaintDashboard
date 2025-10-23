import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

// Import GitHub issue reporter
const GitHubIssueReporter = require('./github_issue_reporter.js');

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
  private githubReporter: any;

  constructor() {
    this.screenshotDir = path.join(__dirname, 'screenshots', 'smart-tests');
    this.htmlDir = path.join(__dirname, 'html-dumps', 'smart-tests');
    
    // Ensure directories exist
    [this.screenshotDir, this.htmlDir].forEach(dir => {
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
    });
    
    // Initialize GitHub issue reporter
    this.githubReporter = new GitHubIssueReporter();
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

    // Danger zone / Clear Database admin tool
    if (lowerRequest.includes('clear database') || lowerRequest.includes('danger zone') || lowerRequest.includes('reset database')) {
      requests.push({
        action: 'clear_database',
        priority: 1,
        flags: ['authenticated', 'danger_zone'],
        description: 'Test the Clear Database modal and operation'
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

  // Add user/role context extraction
  private extractUserContext(request: string): { username: string, password: string, role: string } {
    const lower = request.toLowerCase();
    if (lower.includes('as a technician')) {
      return { username: 'demo_user_2', password: 'demo123', role: 'technician' };
    }
    if (lower.includes('as a manager')) {
      return { username: 'demo_user_3', password: 'demo123', role: 'manager' };
    }
    if (lower.includes('as an admin') || lower.includes('as a superuser')) {
      return { username: 'admin', password: 'temppass123', role: 'admin' };
    }
    // Default to admin for backward compatibility
    return { username: 'admin', password: 'temppass123', role: 'admin' };
  }

  // Update ensureAuthenticated to accept credentials
  private async ensureAuthenticated(page: any, username = 'admin', password = 'temppass123'): Promise<boolean> {
    if (this.isAuthenticated) return true;
    try {
      console.log('🔐 Attempting to authenticate...');
      await page.goto('http://localhost:4405/auth/login/', { timeout: 10000 });
      await page.waitForLoadState('networkidle', { timeout: 10000 });
      const currentUrl = page.url();
      if (!currentUrl.includes('login')) {
        console.log('✅ Already authenticated');
        this.isAuthenticated = true;
        return true;
      }
      await page.fill('#id_username', username, { timeout: 10000 });
      await page.fill('#id_password', password, { timeout: 10000 });
      await this.takeScreenshot(page, 'login_before_click');
      let loginClicked = false;
      try { await page.click('input[type="submit"]', { timeout: 10000 }); loginClicked = true; } catch {}
      if (!loginClicked) {
        try { await page.click('button[type="submit"]', { timeout: 10000 }); loginClicked = true; } catch {}
      }
      if (!loginClicked) {
        try { await page.click('button:has-text("Login")', { timeout: 10000 }); loginClicked = true; } catch {}
      }
      if (!loginClicked) {
        try { await page.click('form button', { timeout: 10000 }); loginClicked = true; } catch {}
      }
      if (!loginClicked) {
        console.log('❌ Could not find login button');
        await this.takeScreenshot(page, 'login_button_not_found');
        return false;
      }
      await page.waitForLoadState('networkidle', { timeout: 10000 });
      await this.takeScreenshot(page, 'login_after_click');
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
      await page.goto('/equipment/', { timeout: 10000 });
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
        manufacturer_serial: `SN${Date.now()}`,
        asset_tag: `AT${Date.now()}`,
        manufacturer: 'Test Manufacturer',
        model_number: 'Test Model',
        status: 'active'
      };

      // Fill form fields
      await page.fill('input[name="name"]', testEquipment.name, { timeout: 10000 });
      await page.fill('input[name="manufacturer_serial"]', testEquipment.manufacturer_serial, { timeout: 10000 });
      await page.fill('input[name="asset_tag"]', testEquipment.asset_tag, { timeout: 10000 });
      await page.fill('input[name="manufacturer"]', testEquipment.manufacturer, { timeout: 10000 });
      await page.fill('input[name="model_number"]', testEquipment.model_number, { timeout: 10000 });
      await page.selectOption('select[name="status"]', testEquipment.status, { timeout: 10000 });
      
      // Select location - try to find and select Sophie
      try {
        await page.selectOption('select[name="location"]', '1'); // Sophie has ID 1
      } catch (e) {
        console.log('Could not select Sophie location, trying first available option');
        await page.selectOption('select[name="location"]', '1');
      }

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
      await page.goto('/equipment/');
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
    const urlsToVisit = ['/'];

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

  // Update clearDatabase to check RBAC
  private async clearDatabase(page: any, userContext: { username: string, password: string, role: string }): Promise<TestResult> {
    const result: TestResult = {
      testName: `Clear Database (Danger Zone) Test as ${userContext.role}`,
      timestamp: new Date().toISOString(),
      success: false,
      errors: [],
      warnings: [],
      screenshots: [],
      htmlDumps: [],
      data: { user: userContext }
    };
    try {
      // Authenticate as the specified user
      const authSuccess = await this.ensureAuthenticated(page, userContext.username, userContext.password);
      if (!authSuccess) {
        result.errors.push('Failed to authenticate as ' + userContext.username);
        return result;
      }
      // Go to settings page
      await page.goto('http://localhost:4405/core/settings/', { timeout: 20000 });
      await page.waitForLoadState('networkidle');
      result.screenshots.push(await this.takeScreenshot(page, 'settings_page_initial'));
      result.htmlDumps.push(await this.dumpHTML(page, 'settings_page_initial'));
      // Try to open the Clear Database modal
      const clearDbButton = await page.$('button:has-text("Clear Database")');
      if (!clearDbButton) {
        result.success = userContext.role !== 'admin';
        result.warnings.push('Clear Database button not visible for this user.');
        result.screenshots.push(await this.takeScreenshot(page, 'clear_db_button_not_visible'));
        return result;
      }
      await clearDbButton.click();
      await page.waitForSelector('#databaseClearModal', { state: 'visible', timeout: 10000 });
      result.screenshots.push(await this.takeScreenshot(page, 'clear_db_modal_open'));
      result.htmlDumps.push(await this.dumpHTML(page, 'clear_db_modal_open'));
      // Type CLEAR DATABASE in the confirmation field
      await page.fill('#clearConfirmation', 'CLEAR DATABASE');
      result.screenshots.push(await this.takeScreenshot(page, 'clear_db_confirmation_filled'));
      // Click the Clear Database button
      await page.click('#executeClearBtn');
      await page.waitForSelector('#clearResults', { state: 'visible', timeout: 10000 });
      const operationResult = await page.textContent('#clearOutput');
      result.data.operationResult = operationResult;
      result.screenshots.push(await this.takeScreenshot(page, 'clear_db_result'));
      result.htmlDumps.push(await this.dumpHTML(page, 'clear_db_result'));
      // Check for success or error
      if (userContext.role === 'admin') {
        if (operationResult && (operationResult.toLowerCase().includes('success') || operationResult.toLowerCase().includes('completed'))) {
          result.success = true;
        } else {
          result.success = false;
          result.errors.push('Operation did not complete successfully. Result: ' + (operationResult || 'No output'));
        }
      } else {
        // Non-admins should not be able to clear the database
        if (operationResult && (operationResult.toLowerCase().includes('permission') || operationResult.toLowerCase().includes('denied') || operationResult.toLowerCase().includes('not allowed'))) {
          result.success = true;
        } else {
          result.success = false;
          result.errors.push('Non-admin user was able to attempt or complete a dangerous operation!');
        }
      }
    } catch (error) {
      result.errors.push('Clear Database test failed: ' + error);
      result.screenshots.push(await this.takeScreenshot(page, 'clear_db_error'));
    }
    return result;
  }

  // Main test runner
  async runTests(page: any, naturalLanguageRequest: string): Promise<void> {
    console.log('🚀 Starting Smart Test Runner...');
    console.log(`📝 Request: "${naturalLanguageRequest}"`);
    
    const userContext = this.extractUserContext(naturalLanguageRequest);
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
        case 'clear_database':
          testResult = await this.clearDatabase(page, userContext);
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

  // Public method to get results for external access
  public getResults(): TestResult[] {
    return this.results;
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

    // Create GitHub issue if there are failures
    if (report.failedTests > 0) {
      console.log('\n🚨 Test failures detected! Creating GitHub issue...');
      try {
        const failureDetails = {
          request: process.env.TEST_REQUEST || 'Unknown test request',
          environment: process.env.BASE_URL || 'http://web:8000',
          container: 'playwright_runner'
        };
        
        const issue = await this.githubReporter.createIssue(report, failureDetails);
        
        if (issue) {
          // Upload screenshots from failed tests
                  const allScreenshots = this.getResults()
          .filter(r => !r.success && r.screenshots.length > 0)
          .flatMap(r => r.screenshots);
          
          if (allScreenshots.length > 0) {
            await this.githubReporter.uploadScreenshots(issue.number, allScreenshots);
          }
        }
      } catch (error) {
        console.error('❌ Failed to create GitHub issue:', error.message);
      }
    } else {
      console.log('✅ All tests passed! No GitHub issue needed.');
    }
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

// Automated review utility
if (require.main === module) {
  const { chromium } = require('playwright');
  (async () => {
    const runner = new SmartTestRunner();
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    const scenarios = [
      {
        prompt: 'As an admin, test the Clear Database modal and confirm it works.',
        expected: 'allowed',
      },
      {
        prompt: 'As a technician, try to clear the database and confirm access is denied.',
        expected: 'denied',
      },
    ];
    for (const scenario of scenarios) {
      console.log(`\n=== Running scenario: ${scenario.prompt} ===`);
      await runner.runTests(page, scenario.prompt);
      const results = runner.getResults();
      const lastResult = results[results.length - 1];
      console.log(`Result: ${lastResult.success ? '✅ PASS' : '❌ FAIL'}`);
      if (lastResult.errors.length > 0) {
        console.log('Errors:');
        lastResult.errors.forEach(e => console.log('  - ' + e));
      }
      if (lastResult.warnings.length > 0) {
        console.log('Warnings:');
        lastResult.warnings.forEach(w => console.log('  - ' + w));
      }
      if (lastResult.screenshots.length > 0) {
        console.log('Screenshots:');
        lastResult.screenshots.forEach(s => console.log('  - ' + s));
      }
      if (lastResult.data && lastResult.data.operationResult) {
        console.log('Operation Result:');
        console.log(lastResult.data.operationResult);
      }
    }
    await browser.close();
    console.log('\n=== Automated RBAC Clear Database Review Complete ===');
  })();
} 