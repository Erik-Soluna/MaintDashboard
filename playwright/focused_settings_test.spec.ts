import { test, expect } from '@playwright/test';

test.describe('Focused Settings and Playwright Debug Test', () => {
  test('Test Settings Page and Playwright Debug Functionality', async ({ page }) => {
    const baseUrl = 'http://localhost:4405';
    const adminUsername = 'admin';
    const adminPassword = 'temppass123';
    
    console.log('🚀 Starting focused settings and Playwright debug test...');
    
    try {
      // Navigate to the application
      console.log('📱 Navigating to application...');
      await page.goto(baseUrl, { timeout: 120000 }); // Increased timeout to 2 minutes
      
      // Wait for page to load
      await page.waitForLoadState('networkidle', { timeout: 60000 });
      
      // Check if we're on login page or already logged in
      const currentUrl = page.url();
      console.log(`📍 Current URL: ${currentUrl}`);
      
      if (currentUrl.includes('/auth/login') || currentUrl.includes('/login')) {
        console.log('🔐 Logging in as admin...');
        
        // Fill in login form
        await page.fill('input[name="username"]', adminUsername);
        await page.fill('input[name="password"]', adminPassword);
        
        // Click login button
        await page.click('button[type="submit"], input[type="submit"]');
        
        // Wait for redirect after login
        await page.waitForLoadState('networkidle', { timeout: 60000 });
        
        console.log(`📍 After login URL: ${page.url()}`);
      }
      
      // Navigate to settings page
      console.log('⚙️ Navigating to settings page...');
      await page.goto(`${baseUrl}/core/settings/`, { timeout: 120000 });
      await page.waitForLoadState('networkidle', { timeout: 60000 });
      
      console.log(`📍 Settings page URL: ${page.url()}`);
      
      // Take screenshot of settings page
      await page.screenshot({ path: 'playwright/screenshots/settings_page_initial.png' });
      console.log('📸 Screenshot saved: settings_page_initial.png');
      
      // Check if we can see the System Health & Diagnostics section
      console.log('🔍 Looking for System Health & Diagnostics section...');
      const healthSection = page.locator('text=System Health & Diagnostics');
      const healthSectionExists = await healthSection.isVisible({ timeout: 10000 });
      console.log(`✅ System Health section visible: ${healthSectionExists}`);
      
      if (healthSectionExists) {
        // Look for diagnostic buttons
        console.log('🔍 Looking for diagnostic buttons...');
        const diagnosticButtons = page.locator('.diagnostic-button');
        const buttonCount = await diagnosticButtons.count();
        console.log(`✅ Found ${buttonCount} diagnostic buttons`);
        
        // Test each diagnostic button
        for (let i = 0; i < buttonCount; i++) {
          const button = diagnosticButtons.nth(i);
          const buttonText = await button.textContent();
          console.log(`🔘 Testing button ${i + 1}: ${buttonText?.trim()}`);
          
          try {
            await button.click({ timeout: 10000 });
            console.log(`✅ Clicked button: ${buttonText?.trim()}`);
            
            // Wait a moment for any results to appear
            await page.waitForTimeout(2000);
            
            // Check if results appeared
            const resultsDiv = page.locator('#diagnosticResults');
            const resultsVisible = await resultsDiv.isVisible({ timeout: 5000 });
            console.log(`📊 Results visible: ${resultsVisible}`);
            
            if (resultsVisible) {
              const resultsText = await resultsDiv.textContent();
              console.log(`📋 Results preview: ${resultsText?.substring(0, 200)}...`);
            }
            
          } catch (error) {
            console.log(`❌ Error clicking button ${buttonText?.trim()}: ${error}`);
          }
        }
      }
      
      // Look for Playwright Debug section
      console.log('🐛 Looking for Playwright Debug section...');
      const playwrightSection = page.locator('text=Playwright Debug & Testing');
      const playwrightSectionExists = await playwrightSection.isVisible({ timeout: 10000 });
      console.log(`✅ Playwright Debug section visible: ${playwrightSectionExists}`);
      
      if (playwrightSectionExists) {
        // Test Playwright Debug form
        console.log('📝 Testing Playwright Debug form...');
        
        // Find the prompt textarea
        const promptTextarea = page.locator('#playwright-prompt');
        const textareaExists = await promptTextarea.isVisible({ timeout: 10000 });
        console.log(`✅ Prompt textarea visible: ${textareaExists}`);
        
        if (textareaExists) {
          // Fill in a test prompt
          const testPrompt = 'Test the equipment creation form and check for any errors';
          await promptTextarea.fill(testPrompt);
          console.log(`📝 Filled prompt: ${testPrompt}`);
          
          // Look for the submit button
          const submitButton = page.locator('button:has-text("Run Playwright Test")');
          const submitButtonExists = await submitButton.isVisible({ timeout: 10000 });
          console.log(`✅ Submit button visible: ${submitButtonExists}`);
          
          if (submitButtonExists) {
            // Click submit button
            console.log('🚀 Submitting Playwright test...');
            await submitButton.click({ timeout: 10000 });
            
            // Wait for response
            await page.waitForTimeout(3000);
            
            // Check for success message or error
            const logsDiv = page.locator('#playwrightLogs');
            const logsVisible = await logsDiv.isVisible({ timeout: 10000 });
            console.log(`📋 Logs div visible: ${logsVisible}`);
            
            if (logsVisible) {
              const logsText = await logsDiv.textContent();
              console.log(`📋 Logs content: ${logsText?.substring(0, 500)}...`);
              
              // Check for success or error messages
              const successMessage = page.locator('text=Playwright test submitted successfully');
              const errorMessage = page.locator('text=Error');
              
              const hasSuccess = await successMessage.isVisible({ timeout: 5000 });
              const hasError = await errorMessage.isVisible({ timeout: 5000 });
              
              console.log(`✅ Success message visible: ${hasSuccess}`);
              console.log(`❌ Error message visible: ${hasError}`);
            }
          }
          
          // Test refresh logs button
          console.log('🔄 Testing refresh logs button...');
          const refreshButton = page.locator('button:has-text("Refresh Logs")');
          const refreshButtonExists = await refreshButton.isVisible({ timeout: 10000 });
          console.log(`✅ Refresh button visible: ${refreshButtonExists}`);
          
          if (refreshButtonExists) {
            await refreshButton.click({ timeout: 10000 });
            console.log('✅ Clicked refresh logs button');
            
            // Wait for refresh
            await page.waitForTimeout(2000);
          }
        }
      }
      
      // Take final screenshot
      await page.screenshot({ path: 'playwright/screenshots/settings_page_final.png' });
      console.log('📸 Screenshot saved: settings_page_final.png');
      
      // Save page HTML for debugging
      const html = await page.content();
      const fs = require('fs');
      fs.writeFileSync('playwright/html-dumps/settings_page_debug.html', html);
      console.log('💾 HTML saved: settings_page_debug.html');
      
      console.log('✅ Focused settings test completed successfully!');
      
    } catch (error) {
      console.error('❌ Test failed:', error);
      
      // Take error screenshot
      await page.screenshot({ path: 'playwright/screenshots/settings_test_error.png' });
      console.log('📸 Error screenshot saved: settings_test_error.png');
      
      // Save error page HTML
      const html = await page.content();
      const fs = require('fs');
      fs.writeFileSync('playwright/html-dumps/settings_test_error.html', html);
      console.log('💾 Error HTML saved: settings_test_error.html');
      
      throw error;
    }
  });
}); 