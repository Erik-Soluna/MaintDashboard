#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

class GitHubIssueReporter {
  constructor() {
    this.githubToken = process.env.GITHUB_TOKEN;
    this.githubRepo = process.env.GITHUB_REPO || 'erikw/MaintDashboard';
    this.githubOwner = process.env.GITHUB_OWNER || 'erikw';
    this.githubRepoName = process.env.GITHUB_REPO_NAME || 'MaintDashboard';
    
    if (!this.githubToken) {
      console.warn('⚠️  GITHUB_TOKEN not set. GitHub issue reporting will be disabled.');
      this.enabled = false;
    } else {
      this.enabled = true;
    }
  }

  async createIssue(testReport, failureDetails) {
    if (!this.enabled) {
      console.log('GitHub issue reporting disabled - no token provided');
      return null;
    }

    try {
      const issueTitle = this.generateIssueTitle(testReport);
      const issueBody = this.generateIssueBody(testReport, failureDetails);
      
      const issueData = {
        title: issueTitle,
        body: issueBody,
        labels: ['playwright-test-failure', 'automated', 'bug'],
        assignees: [],
        milestone: null
      };

      const response = await this.postToGitHub('/issues', issueData);
      
      if (response && response.number) {
        console.log(`✅ GitHub issue created: #${response.number}`);
        console.log(`🔗 Issue URL: ${response.html_url}`);
        return response;
      } else {
        console.error('❌ Failed to create GitHub issue:', response);
        return null;
      }
    } catch (error) {
      console.error('❌ Error creating GitHub issue:', error.message);
      return null;
    }
  }

  generateIssueTitle(testReport) {
    const failedTests = testReport.results.filter(r => !r.success);
    const totalFailed = failedTests.length;
    
    if (totalFailed === 1) {
      return `🚨 Playwright Test Failure: ${failedTests[0].testName}`;
    } else {
      return `🚨 Playwright Test Suite Failure: ${totalFailed} tests failed`;
    }
  }

  generateIssueBody(testReport, failureDetails) {
    const failedTests = testReport.results.filter(r => !r.success);
    const passedTests = testReport.results.filter(r => r.success);
    
    let body = `## 🚨 Playwright Test Failure Report\n\n`;
    body += `**Test Run:** ${new Date(testReport.timestamp).toLocaleString()}\n`;
    body += `**Environment:** Docker Container (${process.env.BASE_URL || 'http://web:8000'})\n\n`;
    
    body += `### 📊 Summary\n`;
    body += `- **Total Tests:** ${testReport.totalTests}\n`;
    body += `- **Passed:** ${testReport.passedTests} ✅\n`;
    body += `- **Failed:** ${testReport.failedTests} ❌\n`;
    body += `- **Total Errors:** ${testReport.totalErrors}\n`;
    body += `- **Total Warnings:** ${testReport.totalWarnings}\n\n`;
    
    if (failureDetails && failureDetails.request) {
      body += `### 🎯 Test Request\n`;
      body += `\`\`\`\n${failureDetails.request}\n\`\`\`\n\n`;
    }
    
    if (failedTests.length > 0) {
      body += `### ❌ Failed Tests\n\n`;
      failedTests.forEach((test, index) => {
        body += `#### ${index + 1}. ${test.testName}\n`;
        body += `**Timestamp:** ${new Date(test.timestamp).toLocaleString()}\n\n`;
        
        if (test.errors.length > 0) {
          body += `**Errors:**\n`;
          test.errors.forEach(error => {
            body += `- ${error}\n`;
          });
          body += `\n`;
        }
        
        if (test.warnings.length > 0) {
          body += `**Warnings:**\n`;
          test.warnings.forEach(warning => {
            body += `- ${warning}\n`;
          });
          body += `\n`;
        }
        
        if (test.screenshots.length > 0) {
          body += `**Screenshots:** ${test.screenshots.length} captured\n`;
        }
        
        if (test.htmlDumps.length > 0) {
          body += `**HTML Dumps:** ${test.htmlDumps.length} captured\n`;
        }
        
        if (test.data) {
          body += `**Additional Data:**\n\`\`\`json\n${JSON.stringify(test.data, null, 2)}\n\`\`\`\n`;
        }
        
        body += `---\n\n`;
      });
    }
    
    if (passedTests.length > 0) {
      body += `### ✅ Passed Tests\n`;
      passedTests.forEach(test => {
        body += `- ${test.testName}\n`;
      });
      body += `\n`;
    }
    
    body += `### 🔧 Environment Details\n`;
    body += `- **Base URL:** ${process.env.BASE_URL || 'http://web:8000'}\n`;
    body += `- **Container:** playwright_runner\n`;
    body += `- **Report File:** smart-test-report.json\n`;
    body += `- **Generated:** ${new Date().toISOString()}\n\n`;
    
    body += `### 📋 Next Steps\n`;
    body += `1. Review the failed test details above\n`;
    body += `2. Check screenshots and HTML dumps for visual clues\n`;
    body += `3. Verify the test environment is accessible\n`;
    body += `4. Run tests locally to reproduce the issue\n`;
    body += `5. Update test logic or fix underlying application issues\n\n`;
    
    body += `---\n`;
    body += `*This issue was automatically generated by the Playwright test runner.*\n`;
    
    return body;
  }

  async postToGitHub(endpoint, data) {
    const url = `https://api.github.com/repos/${this.githubOwner}/${this.githubRepoName}${endpoint}`;
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `token ${this.githubToken}`,
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
        'User-Agent': 'Playwright-Test-Runner'
      },
      body: JSON.stringify(data)
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`GitHub API error ${response.status}: ${errorText}`);
    }
    
    return await response.json();
  }

  async uploadScreenshots(issueNumber, screenshots) {
    if (!this.enabled || !screenshots || screenshots.length === 0) {
      return;
    }

    console.log(`📸 Uploading ${screenshots.length} screenshots to issue #${issueNumber}...`);
    
    for (const screenshot of screenshots) {
      try {
        if (fs.existsSync(screenshot)) {
          const imageData = fs.readFileSync(screenshot);
          const base64Data = imageData.toString('base64');
          
          const filename = path.basename(screenshot);
          const response = await this.postToGitHub(`/issues/${issueNumber}/comments`, {
            body: `## Screenshot: ${filename}\n\n![${filename}](data:image/png;base64,${base64Data})`
          });
          
          console.log(`✅ Uploaded screenshot: ${filename}`);
        }
      } catch (error) {
        console.error(`❌ Failed to upload screenshot ${screenshot}:`, error.message);
      }
    }
  }
}

module.exports = GitHubIssueReporter; 