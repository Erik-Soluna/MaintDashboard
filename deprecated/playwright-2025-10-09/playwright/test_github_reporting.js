#!/usr/bin/env node

const GitHubIssueReporter = require('./github_issue_reporter.js');

async function testGitHubReporting() {
  console.log('🧪 Testing GitHub Issue Reporting...\n');
  
  const reporter = new GitHubIssueReporter();
  
  if (!reporter.enabled) {
    console.log('❌ GitHub reporting is disabled - no token provided');
    console.log('💡 Set GITHUB_TOKEN environment variable to enable testing');
    return;
  }
  
  console.log('✅ GitHub reporting is enabled');
  console.log(`📦 Repository: ${reporter.githubOwner}/${reporter.githubRepoName}\n`);
  
  // Create a test report
  const testReport = {
    timestamp: new Date().toISOString(),
    totalTests: 3,
    passedTests: 1,
    failedTests: 2,
    totalErrors: 3,
    totalWarnings: 1,
    totalScreenshots: 2,
    results: [
      {
        testName: 'Test Login',
        timestamp: new Date().toISOString(),
        success: true,
        errors: [],
        warnings: [],
        screenshots: [],
        htmlDumps: []
      },
      {
        testName: 'Create Equipment',
        timestamp: new Date().toISOString(),
        success: false,
        errors: [
          'Element not found: #equipment-name',
          'Form submission failed: 500 Internal Server Error'
        ],
        warnings: ['Slow page load detected'],
        screenshots: ['/app/playwright/screenshots/smart-tests/test1.png'],
        htmlDumps: ['/app/playwright/html-dumps/smart-tests/test1.html'],
        data: {
          formData: { name: 'Test Equipment', location: 'Main Building' },
          responseCode: 500
        }
      },
      {
        testName: 'Delete Equipment',
        timestamp: new Date().toISOString(),
        success: false,
        errors: ['Confirmation dialog not found'],
        warnings: [],
        screenshots: ['/app/playwright/screenshots/smart-tests/test2.png'],
        htmlDumps: []
      }
    ]
  };
  
  const failureDetails = {
    request: 'Create equipment with all required fields and delete it',
    environment: 'http://web:8000',
    container: 'playwright_runner',
    testRun: 'automated-test'
  };
  
  try {
    console.log('📝 Creating test GitHub issue...');
    const issue = await reporter.createIssue(testReport, failureDetails);
    
    if (issue) {
      console.log(`✅ Test issue created successfully!`);
      console.log(`🔗 Issue URL: ${issue.html_url}`);
      console.log(`📊 Issue Number: #${issue.number}`);
      
      // Test screenshot upload (with a dummy screenshot)
      console.log('\n📸 Testing screenshot upload...');
      const dummyScreenshot = Buffer.from('fake-png-data').toString('base64');
      const tempScreenshotPath = '/tmp/test-screenshot.png';
      require('fs').writeFileSync(tempScreenshotPath, Buffer.from(dummyScreenshot, 'base64'));
      
      await reporter.uploadScreenshots(issue.number, [tempScreenshotPath]);
      console.log('✅ Screenshot upload test completed');
      
      // Clean up test issue
      console.log('\n🧹 Cleaning up test issue...');
      await reporter.postToGitHub(`/issues/${issue.number}`, {
        state: 'closed'
      });
      console.log('✅ Test issue closed');
      
    } else {
      console.log('❌ Failed to create test issue');
    }
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
    
    if (error.message.includes('401')) {
      console.log('💡 This might be an authentication issue. Check your GITHUB_TOKEN.');
    } else if (error.message.includes('404')) {
      console.log('💡 This might be a repository access issue. Check GITHUB_OWNER and GITHUB_REPO_NAME.');
    } else if (error.message.includes('403')) {
      console.log('💡 This might be a rate limit or permission issue.');
    }
  }
  
  console.log('\n🏁 GitHub reporting test completed');
}

// Run the test if this file is executed directly
if (require.main === module) {
  testGitHubReporting().catch(console.error);
}

module.exports = { testGitHubReporting }; 