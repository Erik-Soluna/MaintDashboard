#!/usr/bin/env node

const { execSync } = require('child_process');
const path = require('path');

// Get the test request from command line arguments
const args = process.argv.slice(2);
const testRequest = args.join(' ');

if (!testRequest) {
  console.log('🚀 Smart Test Runner');
  console.log('===================');
  console.log('');
  console.log('Usage: node run_smart_test.js "your natural language request"');
  console.log('');
  console.log('Examples:');
  console.log('  node run_smart_test.js "Make a new equipment with all req fields and delete it"');
  console.log('  node run_smart_test.js "Test login and logout functionality"');
  console.log('  node run_smart_test.js "Explore all links and test permissions"');
  console.log('  node run_smart_test.js "Create maintenance for equipment"');
  console.log('  node run_smart_test.js "Test authentication and access control"');
  console.log('');
  console.log('Available test types:');
  console.log('  - Equipment: create, delete, list');
  console.log('  - Maintenance: create, list');
  console.log('  - Authentication: login, logout');
  console.log('  - Permissions: access control testing');
  console.log('  - Exploration: all links and pages');
  console.log('');
  process.exit(1);
}

console.log('🚀 Running Smart Test Runner...');
console.log(`📝 Request: "${testRequest}"`);
console.log('');

// Set the environment variable and run the test
process.env.TEST_REQUEST = testRequest;

try {
  const command = 'npx playwright test smart_test_runner.spec.ts --headed';
  console.log(`Executing: ${command}`);
  console.log('');
  
  execSync(command, { 
    stdio: 'inherit',
    cwd: __dirname 
  });
  
  console.log('');
  console.log('✅ Smart test completed!');
  console.log('📊 Check the generated reports in the playwright directory');
  
} catch (error) {
  console.error('❌ Test execution failed:', error.message);
  process.exit(1);
} 