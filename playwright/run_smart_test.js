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

const BASE_URL = process.env.BASE_URL || 'http://localhost:8000';
const API_URL = `${BASE_URL.replace(/\/$/, '')}/core/api/playwright-debug/`;
const LOG_FILE = path.join(__dirname, 'runner.log');

function log(msg) {
  const line = `[${new Date().toISOString()}] ${msg}`;
  console.log(line);
  fs.appendFileSync(LOG_FILE, line + '\n');
}

async function runBasicTests() {
  log('Running basic Playwright tests...');
  try {
    execSync('npx playwright test playwright/admin_explore.spec.ts --reporter=list', { stdio: 'inherit' });
    execSync('npx playwright test playwright/focused_settings_test.spec.ts --reporter=list', { stdio: 'inherit' });
    log('Basic Playwright tests completed.');
  } catch (err) {
    log('Error running basic Playwright tests: ' + err.message);
  }
}

async function pollForTasks() {
  log('Polling for natural language Playwright tasks...');
  while (true) {
    try {
      const res = await fetch(API_URL);
      const data = await res.json();
      if (data.logs && data.logs.length > 0) {
        for (const log of data.logs) {
          if (log.status === 'pending') {
            logTask(`Starting task: ${log.prompt}`);
            try {
              // Run the smart test runner with the prompt
              execSync(`npx playwright test playwright/smart_test_runner.spec.ts --project=chromium --grep="${log.prompt.replace(/"/g, '')}" --reporter=list`, { stdio: 'inherit' });
              logTask(`Task succeeded: ${log.prompt}`);
              // Optionally, POST result back to API
            } catch (err) {
              logTask(`Task failed: ${log.prompt} - ${err.message}`);
              // Optionally, POST error back to API
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