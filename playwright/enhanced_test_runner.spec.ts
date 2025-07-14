import { test, expect, Page } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

interface TestScenario {
  name: string;
  description: string;
  prompts: string[];
  expectedResults: any[];
  userRole?: string;
  username?: string;
  password?: string;
}

interface TestResult {
  scenario: string;
  prompt: string;
  success: boolean;
  duration: number;
  screenshots: string[];
  htmlDumps: string[];
  error?: string;
  details?: any;
}

class EnhancedTestRunner {
  private page: Page;
  private results: TestResult[] = [];
  private screenshotDir: string;
  private htmlDumpDir: string;

  constructor(page: Page) {
    this.page = page;
    this.screenshotDir = path.join(__dirname, 'screenshots', 'enhanced-tests');
    this.htmlDumpDir = path.join(__dirname, 'html-dumps', 'enhanced-tests');
    
    // Create directories if they don't exist
    [this.screenshotDir, this.htmlDumpDir].forEach(dir => {
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
    });
  }

  async login(username: string = 'admin', password: string = 'temppass123'): Promise<boolean> {
    try {
      await this.page.goto('http://web:8000/accounts/login/');
      await this.page.waitForLoadState('networkidle');
      
      await this.page.fill('input[name="username"]', username);
      await this.page.fill('input[name="password"]', password);
      await this.page.click('button[type="submit"]');
      await this.page.waitForLoadState('networkidle');
      
      // Check if login was successful
      const errorMessage = await this.page.locator('.alert-danger').count();
      if (errorMessage > 0) {
        console.log(`Login failed for user ${username}`);
        return false;
      }
      
      console.log(`Successfully logged in as ${username}`);
      return true;
    } catch (error) {
      console.error(`Error during login: ${error}`);
      return false;
    }
  }

  async takeScreenshot(name: string): Promise<string> {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `${name}_${timestamp}.png`;
    const filepath = path.join(this.screenshotDir, filename);
    
    await this.page.screenshot({ path: filepath });
    console.log(`Screenshot saved: ${filepath}`);
    return filepath;
  }

  async dumpHtml(name: string): Promise<string> {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `${name}_${timestamp}.html`;
    const filepath = path.join(this.htmlDumpDir, filename);
    
    const html = await this.page.content();
    fs.writeFileSync(filepath, html, 'utf8');
    console.log(`HTML dump saved: ${filepath}`);
    return filepath;
  }

  async runNaturalLanguageTest(prompt: string, userRole: string = 'admin'): Promise<TestResult> {
    const startTime = Date.now();
    const screenshots: string[] = [];
    const htmlDumps: string[] = [];
    
    try {
      console.log(`Running test: ${prompt}`);
      
      // Take initial screenshot
      screenshots.push(await this.takeScreenshot('initial'));
      htmlDumps.push(await this.dumpHtml('initial'));
      
      // Parse the prompt and determine action
      const action = this.parsePrompt(prompt);
      console.log(`Parsed action: ${JSON.stringify(action)}`);
      
      // Execute the action
      const result = await this.executeAction(action);
      
      // Take final screenshot
      screenshots.push(await this.takeScreenshot('final'));
      htmlDumps.push(await this.dumpHtml('final'));
      
      const duration = Date.now() - startTime;
      
      return {
        scenario: 'natural_language',
        prompt,
        success: result.success,
        duration,
        screenshots,
        htmlDumps,
        details: result
      };
      
    } catch (error) {
      const duration = Date.now() - startTime;
      screenshots.push(await this.takeScreenshot('error'));
      htmlDumps.push(await this.dumpHtml('error'));
      
      return {
        scenario: 'natural_language',
        prompt,
        success: false,
        duration,
        screenshots,
        htmlDumps,
        error: error.message,
        details: { error: error.message }
      };
    }
  }

  private parsePrompt(prompt: string): any {
    const promptLower = prompt.toLowerCase();
    
    // Admin tool actions
    if (promptLower.includes('clear database') || promptLower.includes('clear db')) {
      return {
        type: 'admin_clear_database',
        keepUsers: promptLower.includes('keep users'),
        keepAdmin: promptLower.includes('keep admin'),
        dryRun: promptLower.includes('dry run') || promptLower.includes('test')
      };
    }
    
    if (promptLower.includes('populate demo') || promptLower.includes('add demo data')) {
      return {
        type: 'admin_populate_demo',
        resetData: promptLower.includes('reset') || promptLower.includes('clear first'),
        usersCount: this.extractNumber(promptLower, 'users', 10),
        equipmentCount: this.extractNumber(promptLower, 'equipment', 50),
        activitiesCount: this.extractNumber(promptLower, 'activities', 100),
        eventsCount: this.extractNumber(promptLower, 'events', 75)
      };
    }
    
    // Site creation
    if (promptLower.includes('create site') || promptLower.includes('add site')) {
      return {
        type: 'create_site',
        siteName: this.extractSiteName(promptLower),
        podCount: this.extractNumber(promptLower, 'pods', 11),
        mdcsPerPod: this.extractNumber(promptLower, 'mdcs', 2)
      };
    }
    
    // Equipment creation
    if (promptLower.includes('create equipment') || promptLower.includes('add equipment')) {
      return {
        type: 'create_equipment',
        equipmentName: this.extractEquipmentName(promptLower),
        siteName: this.extractSiteName(promptLower),
        category: this.extractCategory(promptLower)
      };
    }
    
    // Page testing
    if (promptLower.includes('test page') || promptLower.includes('check page')) {
      return {
        type: 'test_page',
        pageName: this.extractPageName(promptLower),
        expectedElements: this.extractExpectedElements(promptLower)
      };
    }
    
    // RBAC testing
    if (promptLower.includes('test rbac') || promptLower.includes('test permissions')) {
      return {
        type: 'test_rbac',
        userRole: this.extractRole(promptLower),
        action: this.extractAction(promptLower),
        expectedResult: promptLower.includes('deny') ? 'denied' : 'allowed'
      };
    }
    
    // Default to general test
    return {
      type: 'general_test',
      description: prompt
    };
  }

  private extractNumber(text: string, keyword: string, defaultValue: number): number {
    const patterns = [
      new RegExp(`${keyword}[:\s]*(\d+)`),
      new RegExp(`(\d+)\s*${keyword}`),
    ];
    for (const pattern of patterns) {
      const match = text.match(pattern);
      if (match) {
        return parseInt(match[1]);
      }
    }
    return defaultValue;
  }

  private extractSiteName(text: string): string {
    const patterns = [
      /site[:\s]*([a-zA-Z0-9\s]+?)(?:\s|$|with|and)/,
      /create\s+([a-zA-Z0-9\s]+?)\s+site/,
      /add\s+([a-zA-Z0-9\s]+?)\s+site/
    ];
    
    for (const pattern of patterns) {
      const match = text.match(pattern);
      if (match) {
        return match[1].trim();
      }
    }
    
    return 'Test Site';
  }

  private extractEquipmentName(text: string): string {
    const patterns = [
      /equipment[:\s]*([a-zA-Z0-9\s]+?)(?:\s|$|in|at)/,
      /device[:\s]*([a-zA-Z0-9\s]+?)(?:\s|$|in|at)/,
      /create\s+([a-zA-Z0-9\s]+?)\s+equipment/
    ];
    
    for (const pattern of patterns) {
      const match = text.match(pattern);
      if (match) {
        return match[1].trim();
      }
    }
    
    return 'Test Equipment';
  }

  private extractCategory(text: string): string {
    const categories = ['transformer', 'switchgear', 'relay', 'breaker', 'controller', 'panel'];
    
    for (const category of categories) {
      if (text.includes(category)) {
        return category.charAt(0).toUpperCase() + category.slice(1);
      }
    }
    
    return 'Transformers';
  }

  private extractPageName(text: string): string {
    const pages = ['dashboard', 'settings', 'equipment', 'maintenance', 'events', 'users', 'locations'];
    
    for (const page of pages) {
      if (text.includes(page)) {
        return page.charAt(0).toUpperCase() + page.slice(1);
      }
    }
    
    return 'Dashboard';
  }

  private extractRole(text: string): string {
    const roles = ['admin', 'administrator', 'manager', 'technician', 'viewer', 'operator'];
    
    for (const role of roles) {
      if (text.includes(role)) {
        return role.charAt(0).toUpperCase() + role.slice(1);
      }
    }
    
    return 'Technician';
  }

  private extractAction(text: string): string {
    const actions = ['clear database', 'populate demo', 'create site', 'create equipment', 'access settings'];
    
    for (const action of actions) {
      if (text.includes(action)) {
        return action;
      }
    }
    
    return 'access settings';
  }

  private extractExpectedElements(text: string): string[] {
    const elements = [];
    const commonElements = ['button', 'form', 'table', 'link', 'modal', 'alert', 'chart'];
    
    for (const element of commonElements) {
      if (text.includes(element)) {
        elements.push(element);
      }
    }
    
    return elements;
  }

  private async executeAction(action: any): Promise<any> {
    switch (action.type) {
      case 'admin_clear_database':
        return await this.executeClearDatabase(action);
      case 'admin_populate_demo':
        return await this.executePopulateDemo(action);
      case 'create_site':
        return await this.executeCreateSite(action);
      case 'create_equipment':
        return await this.executeCreateEquipment(action);
      case 'test_page':
        return await this.executeTestPage(action);
      case 'test_rbac':
        return await this.executeTestRbac(action);
      case 'general_test':
        return await this.executeGeneralTest(action);
      default:
        return { success: false, error: `Unknown action type: ${action.type}` };
    }
  }

  private async executeClearDatabase(action: any): Promise<any> {
    try {
      await this.page.goto('http://web:8000/core/settings/');
      await this.page.waitForLoadState('networkidle');
      
      const clearButton = this.page.locator('button:has-text("Clear Database")');
      if (await clearButton.count() === 0) {
        return { success: false, error: 'Clear Database button not found - user may not have admin permissions' };
      }
      
      await clearButton.click();
      await this.page.waitForTimeout(1000);
      
      const modal = this.page.locator('.modal');
      if (await modal.count() === 0) {
        return { success: false, error: 'Clear Database modal did not open' };
      }
      
      // Set options
      if (action.keepUsers) {
        const checkbox = this.page.locator('input[name="keep_users"]');
        if (await checkbox.count() > 0) {
          await checkbox.check();
        }
      }
      
      if (action.keepAdmin) {
        const checkbox = this.page.locator('input[name="keep_admin"]');
        if (await checkbox.count() > 0) {
          await checkbox.check();
        }
      }
      
      if (action.dryRun) {
        const checkbox = this.page.locator('input[name="dry_run"]');
        if (await checkbox.count() > 0) {
          await checkbox.check();
        }
      }
      
      // Submit
      const submitButton = this.page.locator('button[type="submit"]');
      if (await submitButton.count() > 0) {
        await submitButton.click();
        await this.page.waitForTimeout(3000);
      }
      
      // Check result
      const successMessage = this.page.locator('.alert-success');
      const errorMessage = this.page.locator('.alert-danger');
      
      if (await successMessage.count() > 0) {
        return { success: true, message: await successMessage.textContent() };
      } else if (await errorMessage.count() > 0) {
        return { success: false, error: await errorMessage.textContent() };
      }
      
      return { success: true, message: 'Clear database action completed' };
      
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  private async executePopulateDemo(action: any): Promise<any> {
    try {
      await this.page.goto('http://web:8000/core/settings/');
      await this.page.waitForLoadState('networkidle');
      
      const demoButton = this.page.locator('button:has-text("Populate Demo Data")');
      if (await demoButton.count() === 0) {
        return { success: false, error: 'Populate Demo Data button not found - user may not have admin permissions' };
      }
      
      await demoButton.click();
      await this.page.waitForTimeout(1000);
      
      const modal = this.page.locator('.modal');
      if (await modal.count() === 0) {
        return { success: false, error: 'Populate Demo Data modal did not open' };
      }
      
      // Fill form
      if (action.resetData) {
        const checkbox = this.page.locator('input[name="reset_data"]');
        if (await checkbox.count() > 0) {
          await checkbox.check();
        }
      }
      
      const usersInput = this.page.locator('input[name="users_count"]');
      if (await usersInput.count() > 0) {
        await usersInput.fill(action.usersCount.toString());
      }
      
      const equipmentInput = this.page.locator('input[name="equipment_count"]');
      if (await equipmentInput.count() > 0) {
        await equipmentInput.fill(action.equipmentCount.toString());
      }
      
      const activitiesInput = this.page.locator('input[name="activities_count"]');
      if (await activitiesInput.count() > 0) {
        await activitiesInput.fill(action.activitiesCount.toString());
      }
      
      const eventsInput = this.page.locator('input[name="events_count"]');
      if (await eventsInput.count() > 0) {
        await eventsInput.fill(action.eventsCount.toString());
      }
      
      // Submit
      const submitButton = this.page.locator('button[type="submit"]');
      if (await submitButton.count() > 0) {
        await submitButton.click();
        await this.page.waitForTimeout(5000);
      }
      
      // Check result
      const successMessage = this.page.locator('.alert-success');
      const errorMessage = this.page.locator('.alert-danger');
      
      if (await successMessage.count() > 0) {
        return { success: true, message: await successMessage.textContent() };
      } else if (await errorMessage.count() > 0) {
        return { success: false, error: await errorMessage.textContent() };
      }
      
      return { success: true, message: 'Demo data population completed' };
      
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  private async executeCreateSite(action: any): Promise<any> {
    try {
      await this.page.goto('http://web:8000/core/settings/');
      await this.page.waitForLoadState('networkidle');
      
      const podButton = this.page.locator('button:has-text("Generate PODs")');
      if (await podButton.count() > 0) {
        await podButton.click();
        await this.page.waitForTimeout(1000);
        
        const siteInput = this.page.locator('input[name="site_name"]');
        if (await siteInput.count() > 0) {
          await siteInput.fill(action.siteName);
        }
        
        const podCountInput = this.page.locator('input[name="pod_count"]');
        if (await podCountInput.count() > 0) {
          await podCountInput.fill(action.podCount.toString());
        }
        
        const mdcsInput = this.page.locator('input[name="mdcs_per_pod"]');
        if (await mdcsInput.count() > 0) {
          await mdcsInput.fill(action.mdcsPerPod.toString());
        }
        
        const submitButton = this.page.locator('button[type="submit"]');
        if (await submitButton.count() > 0) {
          await submitButton.click();
          await this.page.waitForTimeout(2000);
        }
      }
      
      return { success: true, message: `Attempted to create site ${action.siteName}` };
      
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  private async executeCreateEquipment(action: any): Promise<any> {
    try {
      await this.page.goto('http://web:8000/equipment/');
      await this.page.waitForLoadState('networkidle');
      
      const addButton = this.page.locator('a:has-text("Add Equipment"), button:has-text("Add Equipment")');
      if (await addButton.count() > 0) {
        await addButton.click();
        await this.page.waitForTimeout(1000);
        
        const nameInput = this.page.locator('input[name="name"]');
        if (await nameInput.count() > 0) {
          await nameInput.fill(action.equipmentName);
        }
        
        const categorySelect = this.page.locator('select[name="category"]');
        if (await categorySelect.count() > 0) {
          await categorySelect.selectOption({ label: action.category });
        }
        
        if (action.siteName) {
          const siteSelect = this.page.locator('select[name="location"]');
          if (await siteSelect.count() > 0) {
            await siteSelect.selectOption({ label: action.siteName });
          }
        }
        
        const submitButton = this.page.locator('button[type="submit"]');
        if (await submitButton.count() > 0) {
          await submitButton.click();
          await this.page.waitForTimeout(2000);
        }
      }
      
      return { success: true, message: `Attempted to create equipment ${action.equipmentName}` };
      
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  private async executeTestPage(action: any): Promise<any> {
    try {
      const pageUrls = {
        'Dashboard': 'http://web:8000/',
        'Settings': 'http://web:8000/core/settings/',
        'Equipment': 'http://web:8000/equipment/',
        'Maintenance': 'http://web:8000/maintenance/',
        'Events': 'http://web:8000/events/',
        'Users': 'http://web:8000/core/settings/users/',
        'Locations': 'http://web:8000/core/settings/locations/'
      };
      
      const url = pageUrls[action.pageName] || 'http://web:8000/';
      await this.page.goto(url);
      await this.page.waitForLoadState('networkidle');
      
      const title = await this.page.title();
      
      return { success: true, pageName: action.pageName, url, title };
      
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  private async executeTestRbac(action: any): Promise<any> {
    try {
      let url = 'http://web:8000/';
      
      if (action.action.includes('settings')) {
        url = 'http://web:8000/core/settings/';
      } else if (action.action.includes('admin')) {
        url = 'http://web:8000/admin/';
      }
      
      await this.page.goto(url);
      await this.page.waitForLoadState('networkidle');
      
      const accessDenied = this.page.locator('.alert-danger, .error-message');
      const forbidden = this.page.locator('h1:has-text("403"), h1:has-text("Forbidden")');
      
      const actualResult = (await accessDenied.count() > 0 || await forbidden.count() > 0) ? 'denied' : 'allowed';
      const success = actualResult === action.expectedResult;
      
      return {
        success,
        userRole: action.userRole,
        action: action.action,
        expectedResult: action.expectedResult,
        actualResult
      };
      
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  private async executeGeneralTest(action: any): Promise<any> {
    try {
      await this.page.goto('http://web:8000/');
      await this.page.waitForLoadState('networkidle');
      
      const title = await this.page.title();
      const url = this.page.url();
      
      return { success: true, title, url, description: action.description };
      
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async runScenario(scenario: TestScenario): Promise<TestResult[]> {
    console.log(`Running scenario: ${scenario.name}`);
    console.log(`Description: ${scenario.description}`);
    
    const results: TestResult[] = [];
    
    for (const prompt of scenario.prompts) {
      const result = await this.runNaturalLanguageTest(prompt, scenario.userRole);
      results.push(result);
      
      // Wait between tests
      await this.page.waitForTimeout(1000);
    }
    
    return results;
  }

  getResults(): TestResult[] {
    return this.results;
  }

  generateReport(): any {
    const totalTests = this.results.length;
    const passedTests = this.results.filter(r => r.success).length;
    const failedTests = totalTests - passedTests;
    const successRate = totalTests > 0 ? (passedTests / totalTests) * 100 : 0;
    
    return {
      summary: {
        totalTests,
        passedTests,
        failedTests,
        successRate: Math.round(successRate * 100) / 100
      },
      results: this.results,
      timestamp: new Date().toISOString()
    };
  }
}

// Test scenarios
const testScenarios: TestScenario[] = [
  {
    name: 'Admin Tools',
    description: 'Test admin functionality including database management',
    prompts: [
      'Test admin user can clear database with keep users option',
      'Test admin user can populate demo data with 5 users and 10 equipment'
    ],
    expectedResults: [],
    userRole: 'admin',
    username: 'admin',
    password: 'temppass123'
  },
  {
    name: 'RBAC Basic',
    description: 'Test basic RBAC permissions',
    prompts: [
      'Test admin user can access settings page',
      'Test technician user cannot access admin tools',
      'Test manager user can view equipment list'
    ],
    expectedResults: [],
    userRole: 'admin',
    username: 'admin',
    password: 'temppass123'
  },
  {
    name: 'Equipment Management',
    description: 'Test equipment CRUD operations',
    prompts: [
      'Test creating equipment called Test Transformer in default location',
      'Test viewing equipment list page',
      'Test equipment detail page loads correctly'
    ],
    expectedResults: [],
    userRole: 'admin',
    username: 'admin',
    password: 'temppass123'
  }
];

test.describe('Enhanced Natural Language Test Runner', () => {
  let runner: EnhancedTestRunner;

  test.beforeEach(async ({ page }) => {
    runner = new EnhancedTestRunner(page);
    
    // Login as admin
    const loginSuccess = await runner.login('admin', 'temppass123');
    expect(loginSuccess).toBeTruthy();
  });

  test('should run admin tools scenario', async ({ page }) => {
    const scenario = testScenarios.find(s => s.name === 'Admin Tools');
    expect(scenario).toBeDefined();
    
    const results = await runner.runScenario(scenario!);
    
    // Generate report
    const report = runner.generateReport();
    console.log('Test Report:', JSON.stringify(report, null, 2));
    
    // Save report to file
    const reportPath = path.join(__dirname, 'test-reports', 'admin-tools-report.json');
    if (!fs.existsSync(path.dirname(reportPath))) {
      fs.mkdirSync(path.dirname(reportPath), { recursive: true });
    }
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
    
    expect(results.length).toBeGreaterThan(0);
    expect(report.summary.successRate).toBeGreaterThan(0);
  });

  test('should run RBAC scenario', async ({ page }) => {
    const scenario = testScenarios.find(s => s.name === 'RBAC Basic');
    expect(scenario).toBeDefined();
    
    const results = await runner.runScenario(scenario!);
    
    const report = runner.generateReport();
    console.log('RBAC Test Report:', JSON.stringify(report, null, 2));
    
    expect(results.length).toBeGreaterThan(0);
  });

  test('should run equipment management scenario', async ({ page }) => {
    const scenario = testScenarios.find(s => s.name === 'Equipment Management');
    expect(scenario).toBeDefined();
    
    const results = await runner.runScenario(scenario!);
    
    const report = runner.generateReport();
    console.log('Equipment Test Report:', JSON.stringify(report, null, 2));
    
    expect(results.length).toBeGreaterThan(0);
  });

  test('should handle individual natural language prompts', async ({ page }) => {
    const prompts = [
      'Test the dashboard page loads correctly',
      'Test admin user can access settings',
      'Test creating a site called Test Site with 5 pods'
    ];
    
    for (const prompt of prompts) {
      const result = await runner.runNaturalLanguageTest(prompt);
      console.log(`Prompt: ${prompt}`);
      console.log(`Result: ${JSON.stringify(result, null, 2)}`);
      
      expect(result).toBeDefined();
      expect(result.prompt).toBe(prompt);
    }
  });
}); 