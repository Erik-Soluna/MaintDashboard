#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
// Patch for node-fetch import compatibility
let fetch;
try {
  fetch = require('node-fetch');
  if (fetch.default) fetch = fetch.default;
} catch (e) {
  console.error('Failed to require node-fetch:', e);
  process.exit(1);
}
const { execSync } = require('child_process');

// Import GitHub issue reporter
const GitHubIssueReporter = require('./github_issue_reporter.js');

const BASE_URL = process.env.BASE_URL || 'http://web:8000';
const API_URL = `${BASE_URL.replace(/\/$/, '')}/core/api/playwright-debug/`;
const LOG_FILE = path.join(__dirname, 'runner.log');

function log(msg) {
  const line = `[${new Date().toISOString()}] ${msg}`;
  console.log(line);
  fs.appendFileSync(LOG_FILE, line + '\n');
}

async function runBasicTests() {
  log('Skipping basic Playwright tests and going straight to task polling...');
  // Skip basic tests for now to avoid webServer issues
  return;
}

async function pollForTasks() {
  log('Polling for natural language Playwright tasks...');
  const githubReporter = new GitHubIssueReporter();
  
  while (true) {
    try {
      const res = await fetch(API_URL);
      const data = await res.json();
      if (data.logs && data.logs.length > 0) {
        for (const log of data.logs) {
          if (log.status === 'pending') {
            logTask(`Starting task: ${log.prompt}`);
            try {
              // Set the test request as environment variable
              process.env.TEST_REQUEST = log.prompt;
              
              // Run the smart test runner with the prompt
              execSync(`npx playwright test playwright/smart_test_runner.spec.ts --project=chromium --reporter=list`, { stdio: 'inherit' });
              logTask(`Task succeeded: ${log.prompt}`);
              
              // Check if test report exists and has failures
              const reportPath = path.join(__dirname, 'smart-test-report.json');
              if (fs.existsSync(reportPath)) {
                const report = JSON.parse(fs.readFileSync(reportPath, 'utf8'));
                if (report.failedTests > 0) {
                  logTask(`🚨 Test failures detected in report. GitHub issue creation handled by SmartTestRunner.`);
                }
              }
            } catch (err) {
              logTask(`Task failed: ${log.prompt} - ${err.message}`);
              
              // Create a failure report and GitHub issue for execution errors
              const failureReport = {
                timestamp: new Date().toISOString(),
                totalTests: 1,
                passedTests: 0,
                failedTests: 1,
                totalErrors: 1,
                totalWarnings: 0,
                totalScreenshots: 0,
                results: [{
                  testName: `Task Execution: ${log.prompt}`,
                  timestamp: new Date().toISOString(),
                  success: false,
                  errors: [`Playwright test execution failed: ${err.message}`],
                  warnings: [],
                  screenshots: [],
                  htmlDumps: []
                }]
              };
              
              try {
                const failureDetails = {
                  request: log.prompt,
                  environment: process.env.BASE_URL || 'http://web:8000',
                  container: 'playwright_runner',
                  executionError: true
                };
                
                await githubReporter.createIssue(failureReport, failureDetails);
              } catch (githubError) {
                logTask(`Failed to create GitHub issue for execution error: ${githubError.message}`);
              }
            }
          }
        }
      }
    } catch (err) {
      log('Error polling for tasks: ' + err.message);
    }
    await new Promise(r => setTimeout(r, 10000)); // Poll every 10s
  }
}

function logTask(msg) {
  log(msg);
}

(async () => {
  await runBasicTests();
  await pollForTasks();
})(); 