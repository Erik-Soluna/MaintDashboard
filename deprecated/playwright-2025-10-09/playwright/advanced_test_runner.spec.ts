import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

interface TestScenario {
  name: string;
  description: string;
  keywords: string[];
  actions: string[];
  requiresAuth: boolean;
  priority: number;
}

interface TestResult {
  scenario: string;
  timestamp: string;
  success: boolean;
  errors: string[];
  warnings: string[];
  screenshots: string[];
  htmlDumps: string[];
  data?: any;
  duration: number;
}

class AdvancedTestRunner {
  private results: TestResult[] = [];
  private screenshotDir: string;
  private htmlDir: string;
  private isAuthenticated: boolean = false;
  private testData: any = {};

  // Predefined test scenarios
  private scenarios: TestScenario[] = [
    {
      name: 'equipment_crud',
      description: 'Create, read, update, and delete equipment',
      keywords: ['equipment', 'crud', 'create', 'delete', 'update', 'item'],
      actions: ['create_equipment', 'list_equipment', 'edit_equipment', 'delete_equipment'],
      requiresAuth: true,
      priority: 1
    },
    {
      name: 'maintenance_workflow',
      description: 'Create and manage maintenance schedules',
      keywords: ['maintenance', 'schedule', 'workflow', 'activity'],
      actions: ['create_maintenance', 'list_maintenance', 'edit_maintenance'],
      requiresAuth: true,
      priority: 2
    },
    {
      name: 'authentication_test',
      description: 'Test login, logout, and session management',
      keywords: ['login', 'logout', 'auth', 'authenticate', 'session'],
      actions: ['test_login', 'test_logout', 'test_session'],
      requiresAuth: false,
      priority: 1
    },
    {
      name: 'permission_test',
      description: 'Test access control and permissions',
      keywords: ['permission', 'access', 'unauthorized', 'protected', 'security'],
      actions: ['test_unauthorized_access', 'test_authorized_access'],
      requiresAuth: false,
      priority: 1
    },
    {
      name: 'navigation_test',
      description: 'Explore all pages and navigation',
      keywords: ['explore', 'navigation', 'links', 'pages', 'every'],
      actions: ['explore_all_pages', 'test_navigation'],
      requiresAuth: false,
      priority: 3
    },
    {
      name: 'form_validation',
      description: 'Test form validation and error handling',
      keywords: ['form', 'validation', 'error', 'required', 'fields'],
      actions: ['test_form_validation', 'test_error_handling'],
      requiresAuth: true,
      priority: 2
    },
    {
      name: 'data_integrity',
      description: 'Test data consistency and integrity',
      keywords: ['data', 'integrity', 'consistency', 'save', 'persist'],
      actions: ['test_data_save', 'test_data_retrieval'],
      requiresAuth: true,
      priority: 2
    }
  ];

  constructor() {
    this.screenshotDir = path.join(__dirname, 'screenshots', 'advanced-tests');
    this.htmlDir = path.join(__dirname, 'html-dumps', 'advanced-tests');
    
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

  // Advanced natural language processing
  private parseNaturalLanguageRequest(request: string): TestScenario[] {
    const lowerRequest = request.toLowerCase();
    const matchedScenarios: { scenario: TestScenario; score: number }[] = [];

    // Calculate relevance score for each scenario
    for (const scenario of this.scenarios) {
      let score = 0;
      
      // Check keyword matches
      for (const keyword of scenario.keywords) {
        if (lowerRequest.includes(keyword)) {
          score += 2; // Higher weight for keyword matches
        }
      }

      // Check for action words
      const actionWords = ['create', 'make', 'add', 'delete', 'remove', 'edit', 'update', 'test', 'check', 'verify'];
      for (const word of actionWords) {
        if (lowerRequest.includes(word)) {
          score += 1;
        }
      }

      // Check for specific entities
      const entities = ['equipment', 'maintenance', 'user', 'admin', 'login', 'permission'];
      for (const entity of entities) {
        if (lowerRequest.includes(entity)) {
          score += 1.5;
        }
      }

      // Boost score for comprehensive requests
      if (lowerRequest.includes('all') || lowerRequest.includes('everything') || lowerRequest.includes('comprehensive')) {
        score += 3;
      }

      if (score > 0) {
        matchedScenarios.push({ scenario, score });
      }
    }

    // Sort by score and return top matches
    return matchedScenarios
      .sort((a, b) => b.score - a.score)
      .slice(0, 3) // Limit to top 3 scenarios
      .map(item => item.scenario);
  }

  // Authentication management
  private async ensureAuthenticated(page: any): Promise<boolean> {
    if (this.isAuthenticated) return true;

    try {
      console.log('🔐 Attempting to authenticate...');
      await page.goto('http://localhost:4405/auth/login/');
      await page.waitForLoadState('networkidle');

      // Check if already logged in
      const currentUrl = page.url();
      if (!currentUrl.includes('login')) {
        console.log('✅ Already authenticated');
        this.isAuthenticated = true;
        return true;
      }

      // Fill login form
      await page.fill('#id_username', 'admin');
      await page.fill('#id_password', 'temppass123');
      await page.click('input[type="submit"]');
      await page.waitForLoadState('networkidle');

      // Verify login success
      const newUrl = page.url();
      if (!newUrl.includes('login')) {
        console.log('✅ Authentication successful');
        this.isAuthenticated = true;
        return true;
      } else {
        console.log('❌ Authentication failed');
        return false;
      }
    } catch (error) {
      console.log(`❌ Authentication error: ${error}`);
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
          await logoutElement.click();
          await page.waitForLoadState('networkidle');
          console.log('✅ Logout successful');
          this.isAuthenticated = false;
          return true;
        }
      }

      // If no logout button found, try to navigate to logout URL
      await page.goto('http://localhost:4405/auth/logout/');
      await page.waitForLoadState('networkidle');
      this.isAuthenticated = false;
      return true;
    } catch (error) {
      console.log(`❌ Logout error: ${error}`);
      return false;
    }
  }

  // Test implementations
  private async executeAction(page: any, action: string): Promise<Partial<TestResult>> {
    const startTime = Date.now();
    const result: Partial<TestResult> = {
      errors: [],
      warnings: [],
      screenshots: [],
      htmlDumps: []
    };

    try {
      switch (action) {
        case 'create_equipment':
          await this.createEquipment(page, result);
          break;
        case 'list_equipment':
          await this.listEquipment(page, result);
          break;
        case 'edit_equipment':
          await this.editEquipment(page, result);
          break;
        case 'delete_equipment':
          await this.deleteEquipment(page, result);
          break;
        case 'create_maintenance':
          await this.createMaintenance(page, result);
          break;
        case 'list_maintenance':
          await this.listMaintenance(page, result);
          break;
        case 'test_login':
          await this.testLogin(page, result);
          break;
        case 'test_logout':
          await this.testLogout(page, result);
          break;
        case 'test_unauthorized_access':
          await this.testUnauthorizedAccess(page, result);
          break;
        case 'test_authorized_access':
          await this.testAuthorizedAccess(page, result);
          break;
        case 'explore_all_pages':
          await this.exploreAllPages(page, result);
          break;
        case 'test_form_validation':
          await this.testFormValidation(page, result);
          break;
        case 'test_error_handling':
          await this.testErrorHandling(page, result);
          break;
        default:
          result.errors?.push(`Unknown action: ${action}`);
      }
    } catch (error) {
      result.errors?.push(`Action ${action} failed: ${error}`);
    }

    result.duration = Date.now() - startTime;
    return result;
  }

  // Individual action implementations
  private async createEquipment(page: any, result: Partial<TestResult>): Promise<void> {
    await this.ensureAuthenticated(page);
    
    await page.goto('http://localhost:4405/equipment/');
    await page.waitForLoadState('networkidle');
    
    result.screenshots?.push(await this.takeScreenshot(page, 'create_equipment_initial'));
    
    // Find and click add button
    const addButton = await page.$('a[href*="add"], a:has-text("Add Equipment"), button:has-text("Add Equipment")');
    if (!addButton) {
      result.errors?.push('Could not find Add Equipment button');
      return;
    }

    await addButton.click();
    await page.waitForLoadState('networkidle');
    
    result.screenshots?.push(await this.takeScreenshot(page, 'create_equipment_form'));

    // Fill form with test data
    const testData = {
      name: `Test Equipment ${Date.now()}`,
      model: 'Test Model',
      serial_number: `SN${Date.now()}`,
      location: 'Test Location',
      status: 'active'
    };

    await page.fill('input[name="name"]', testData.name);
    await page.fill('input[name="model"]', testData.model);
    await page.fill('input[name="serial_number"]', testData.serial_number);
    await page.fill('input[name="location"]', testData.location);
    
    // Try to select status if dropdown exists
    try {
      await page.selectOption('select[name="status"]', testData.status);
    } catch (e) {
      // Status dropdown might not exist
    }

    result.screenshots?.push(await this.takeScreenshot(page, 'create_equipment_filled'));

    // Submit form
    await page.click('input[type="submit"], button[type="submit"]');
    await page.waitForLoadState('networkidle');

    result.screenshots?.push(await this.takeScreenshot(page, 'create_equipment_submitted'));
    result.htmlDumps?.push(await this.dumpHTML(page, 'create_equipment'));
    result.data = testData;
  }

  private async listEquipment(page: any, result: Partial<TestResult>): Promise<void> {
    await this.ensureAuthenticated(page);
    
    await page.goto('http://localhost:4405/equipment/');
    await page.waitForLoadState('networkidle');
    
    result.screenshots?.push(await this.takeScreenshot(page, 'list_equipment'));
    result.htmlDumps?.push(await this.dumpHTML(page, 'list_equipment'));
  }

  private async editEquipment(page: any, result: Partial<TestResult>): Promise<void> {
    await this.ensureAuthenticated(page);
    
    await page.goto('http://localhost:4405/equipment/');
    await page.waitForLoadState('networkidle');
    
    // Find edit button for first equipment
    const editButton = await page.$('a[href*="edit"], a:has-text("Edit"), button:has-text("Edit")');
    if (!editButton) {
      result.warnings?.push('No edit buttons found');
      return;
    }

    await editButton.click();
    await page.waitForLoadState('networkidle');
    
    result.screenshots?.push(await this.takeScreenshot(page, 'edit_equipment'));
    result.htmlDumps?.push(await this.dumpHTML(page, 'edit_equipment'));
  }

  private async deleteEquipment(page: any, result: Partial<TestResult>): Promise<void> {
    await this.ensureAuthenticated(page);
    
    await page.goto('http://localhost:4405/equipment/');
    await page.waitForLoadState('networkidle');
    
    result.screenshots?.push(await this.takeScreenshot(page, 'delete_equipment_initial'));

    // Find delete button
    const deleteButton = await page.$('a[href*="delete"], button:has-text("Delete")');
    if (!deleteButton) {
      result.warnings?.push('No delete buttons found');
      return;
    }

    await deleteButton.click();
    await page.waitForLoadState('networkidle');
    
    result.screenshots?.push(await this.takeScreenshot(page, 'delete_equipment_confirmation'));

    // Handle confirmation
    const confirmButton = await page.$('button:has-text("Confirm"), button:has-text("Delete"), input[type="submit"]');
    if (confirmButton) {
      await confirmButton.click();
      await page.waitForLoadState('networkidle');
    }

    result.screenshots?.push(await this.takeScreenshot(page, 'delete_equipment_final'));
    result.htmlDumps?.push(await this.dumpHTML(page, 'delete_equipment'));
  }

  private async createMaintenance(page: any, result: Partial<TestResult>): Promise<void> {
    await this.ensureAuthenticated(page);
    
    await page.goto('http://localhost:4405/maintenance/');
    await page.waitForLoadState('networkidle');
    
    result.screenshots?.push(await this.takeScreenshot(page, 'create_maintenance_initial'));
    
    // Look for add maintenance button
    const addButton = await page.$('a[href*="add"], a:has-text("Add Maintenance"), button:has-text("Add Maintenance")');
    if (!addButton) {
      result.warnings?.push('No add maintenance button found');
      return;
    }

    await addButton.click();
    await page.waitForLoadState('networkidle');
    
    result.screenshots?.push(await this.takeScreenshot(page, 'create_maintenance_form'));
    result.htmlDumps?.push(await this.dumpHTML(page, 'create_maintenance'));
  }

  private async listMaintenance(page: any, result: Partial<TestResult>): Promise<void> {
    await this.ensureAuthenticated(page);
    
    await page.goto('http://localhost:4405/maintenance/');
    await page.waitForLoadState('networkidle');
    
    result.screenshots?.push(await this.takeScreenshot(page, 'list_maintenance'));
    result.htmlDumps?.push(await this.dumpHTML(page, 'list_maintenance'));
  }

  private async testLogin(page: any, result: Partial<TestResult>): Promise<void> {
    await page.goto('http://localhost:4405/auth/login/');
    await page.waitForLoadState('networkidle');
    
    result.screenshots?.push(await this.takeScreenshot(page, 'test_login_initial'));
    
    await page.fill('#id_username', 'admin');
    await page.fill('#id_password', 'temppass123');
    await page.click('input[type="submit"]');
    await page.waitForLoadState('networkidle');
    
    result.screenshots?.push(await this.takeScreenshot(page, 'test_login_submitted'));
    result.htmlDumps?.push(await this.dumpHTML(page, 'test_login'));
  }

  private async testLogout(page: any, result: Partial<TestResult>): Promise<void> {
    await this.logout(page);
    
    result.screenshots?.push(await this.takeScreenshot(page, 'test_logout'));
    result.htmlDumps?.push(await this.dumpHTML(page, 'test_logout'));
  }

  private async testUnauthorizedAccess(page: any, result: Partial<TestResult>): Promise<void> {
    await this.logout(page);
    
    const protectedPages = ['/dashboard/', '/equipment/', '/maintenance/', '/events/'];
    
    for (const pageUrl of protectedPages) {
      await page.goto(`http://localhost:4405${pageUrl}`);
      await page.waitForLoadState('networkidle');
      
      const currentUrl = page.url();
      if (!currentUrl.includes('login')) {
        result.warnings?.push(`${pageUrl} accessible without authentication`);
      }
      
      result.screenshots?.push(await this.takeScreenshot(page, `unauthorized_${pageUrl.replace(/\//g, '_')}`));
    }
    
    result.htmlDumps?.push(await this.dumpHTML(page, 'test_unauthorized_access'));
  }

  private async testAuthorizedAccess(page: any, result: Partial<TestResult>): Promise<void> {
    await this.ensureAuthenticated(page);
    
    const protectedPages = ['/dashboard/', '/equipment/', '/maintenance/', '/events/'];
    
    for (const pageUrl of protectedPages) {
      await page.goto(`http://localhost:4405${pageUrl}`);
      await page.waitForLoadState('networkidle');
      
      const currentUrl = page.url();
      if (currentUrl.includes('login')) {
        result.errors?.push(`${pageUrl} not accessible with authentication`);
      }
      
      result.screenshots?.push(await this.takeScreenshot(page, `authorized_${pageUrl.replace(/\//g, '_')}`));
    }
    
    result.htmlDumps?.push(await this.dumpHTML(page, 'test_authorized_access'));
  }

  private async exploreAllPages(page: any, result: Partial<TestResult>): Promise<void> {
    const visitedUrls = new Set<string>();
    const urlsToVisit = ['http://localhost:4405/'];
    
    while (urlsToVisit.length > 0 && visitedUrls.size < 30) {
      const currentUrl = urlsToVisit.shift()!;
      
      if (visitedUrls.has(currentUrl)) continue;
      visitedUrls.add(currentUrl);
      
      try {
        await page.goto(currentUrl);
        await page.waitForLoadState('networkidle');
        
        result.screenshots?.push(await this.takeScreenshot(page, `explore_${currentUrl.replace(/[^a-zA-Z0-9]/g, '_')}`));
        
        // Find new links
        const links = await page.$$('a[href]');
        for (const link of links) {
          const href = await link.getAttribute('href');
          if (href && href.startsWith('/') && !visitedUrls.has(`http://localhost:4405${href}`)) {
            urlsToVisit.push(`http://localhost:4405${href}`);
          }
        }
      } catch (error) {
        result.warnings?.push(`Error exploring ${currentUrl}: ${error}`);
      }
    }
    
    result.htmlDumps?.push(await this.dumpHTML(page, 'explore_all_pages'));
  }

  private async testFormValidation(page: any, result: Partial<TestResult>): Promise<void> {
    await this.ensureAuthenticated(page);
    
    // Test equipment form validation
    await page.goto('http://localhost:4405/equipment/add/');
    await page.waitForLoadState('networkidle');
    
    result.screenshots?.push(await this.takeScreenshot(page, 'form_validation_initial'));
    
    // Submit empty form to test validation
    await page.click('input[type="submit"], button[type="submit"]');
    await page.waitForLoadState('networkidle');
    
    result.screenshots?.push(await this.takeScreenshot(page, 'form_validation_errors'));
    result.htmlDumps?.push(await this.dumpHTML(page, 'form_validation'));
  }

  private async testErrorHandling(page: any, result: Partial<TestResult>): Promise<void> {
    // Test 404 page
    await page.goto('http://localhost:4405/nonexistent-page/');
    await page.waitForLoadState('networkidle');
    
    result.screenshots?.push(await this.takeScreenshot(page, 'error_handling_404'));
    result.htmlDumps?.push(await this.dumpHTML(page, 'error_handling'));
  }

  // Main test runner
  async runAdvancedTests(page: any, naturalLanguageRequest: string): Promise<void> {
    console.log('🚀 Starting Advanced Test Runner...');
    console.log(`📝 Request: "${naturalLanguageRequest}"`);
    
    const matchedScenarios = this.parseNaturalLanguageRequest(naturalLanguageRequest);
    console.log(`\n🔍 Matched ${matchedScenarios.length} test scenarios:`);
    matchedScenarios.forEach((scenario, index) => {
      console.log(`  ${index + 1}. ${scenario.description} (${scenario.actions.join(', ')})`);
    });

    for (const scenario of matchedScenarios) {
      console.log(`\n🎯 Executing scenario: ${scenario.description}`);
      
      for (const action of scenario.actions) {
        console.log(`  🔧 Running action: ${action}`);
        
        const startTime = Date.now();
        const actionResult = await this.executeAction(page, action);
        const duration = Date.now() - startTime;
        
        const testResult: TestResult = {
          scenario: scenario.name,
          timestamp: new Date().toISOString(),
          success: (actionResult.errors?.length || 0) === 0,
          errors: actionResult.errors || [],
          warnings: actionResult.warnings || [],
          screenshots: actionResult.screenshots || [],
          htmlDumps: actionResult.htmlDumps || [],
          data: actionResult.data,
          duration
        };

        this.results.push(testResult);
        
        console.log(`    ${testResult.success ? '✅' : '❌'} ${action} (${duration}ms)`);
        if (testResult.errors.length > 0) {
          console.log(`      Errors: ${testResult.errors.join(', ')}`);
        }
      }
    }

    await this.generateAdvancedReport();
  }

  private async generateAdvancedReport() {
    const report = {
      timestamp: new Date().toISOString(),
      totalScenarios: this.results.length,
      passedActions: this.results.filter(r => r.success).length,
      failedActions: this.results.filter(r => !r.success).length,
      totalErrors: this.results.reduce((sum, r) => sum + r.errors.length, 0),
      totalWarnings: this.results.reduce((sum, r) => sum + r.warnings.length, 0),
      totalScreenshots: this.results.reduce((sum, r) => sum + r.screenshots.length, 0),
      averageDuration: this.results.reduce((sum, r) => sum + r.duration, 0) / this.results.length,
      results: this.results
    };

    const reportPath = path.join(__dirname, 'advanced-test-report.json');
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));

    console.log('\n📊 ADVANCED TEST RUNNER REPORT');
    console.log('===============================');
    console.log(`Total scenarios: ${report.totalScenarios}`);
    console.log(`Passed actions: ${report.passedActions}`);
    console.log(`Failed actions: ${report.failedActions}`);
    console.log(`Total errors: ${report.totalErrors}`);
    console.log(`Total warnings: ${report.totalWarnings}`);
    console.log(`Total screenshots: ${report.totalScreenshots}`);
    console.log(`Average duration: ${Math.round(report.averageDuration)}ms`);
    console.log(`\nDetailed report saved to: ${reportPath}`);
  }
}

// Test function
test('Advanced Test Runner', async ({ page }) => {
  test.setTimeout(300000); // 5 minutes
  
  const runner = new AdvancedTestRunner();
  
  const testRequest = process.env.TEST_REQUEST || 
    "Make a new equipment with all req fields and delete it. Make a maintenance for the item.";
  
  await runner.runAdvancedTests(page, testRequest);
}); 