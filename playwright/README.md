# Smart Test Runner for Maintenance Dashboard

A comprehensive Playwright-based testing system that can understand natural language requests and automatically test the maintenance dashboard application.

## 🚀 Quick Start

### Basic Usage

```bash
# Test with natural language request
node run_smart_test.js "Make a new equipment with all req fields and delete it"

# Test authentication
node run_smart_test.js "Test login and logout functionality"

# Test permissions
node run_smart_test.js "Test access control and permissions"

# Comprehensive testing
node run_smart_test.js "Explore all links and test everything"
```

### Direct Playwright Usage

```bash
# Set environment variable and run
TEST_REQUEST="Create equipment and maintenance" npx playwright test smart_test_runner.spec.ts --headed

# Run advanced test runner
TEST_REQUEST="Test CRUD operations" npx playwright test advanced_test_runner.spec.ts --headed
```

## 🧠 Natural Language Understanding

The Smart Test Runner can understand various types of requests:

### Equipment Operations
- "Create equipment" / "Make equipment" / "Add equipment"
- "Delete equipment" / "Remove equipment"
- "List equipment" / "View equipment"
- "Edit equipment" / "Update equipment"

### Maintenance Operations
- "Create maintenance" / "Make maintenance schedule"
- "List maintenance" / "View maintenance"
- "Edit maintenance" / "Update maintenance"

### Authentication & Security
- "Test login" / "Test authentication"
- "Test logout" / "Test sign out"
- "Test permissions" / "Test access control"
- "Test unauthorized access"

### General Testing
- "Explore all links" / "Test every page"
- "Test form validation"
- "Test error handling"
- "Comprehensive testing"

## 📋 Available Test Scenarios

### 1. Equipment CRUD
**Keywords**: equipment, crud, create, delete, update, item
**Actions**: create_equipment, list_equipment, edit_equipment, delete_equipment
**Requires Auth**: Yes

### 2. Maintenance Workflow
**Keywords**: maintenance, schedule, workflow, activity
**Actions**: create_maintenance, list_maintenance, edit_maintenance
**Requires Auth**: Yes

### 3. Authentication Test
**Keywords**: login, logout, auth, authenticate, session
**Actions**: test_login, test_logout, test_session
**Requires Auth**: No

### 4. Permission Test
**Keywords**: permission, access, unauthorized, protected, security
**Actions**: test_unauthorized_access, test_authorized_access
**Requires Auth**: No

### 5. Navigation Test
**Keywords**: explore, navigation, links, pages, every
**Actions**: explore_all_pages, test_navigation
**Requires Auth**: No

### 6. Form Validation
**Keywords**: form, validation, error, required, fields
**Actions**: test_form_validation, test_error_handling
**Requires Auth**: Yes

### 7. Data Integrity
**Keywords**: data, integrity, consistency, save, persist
**Actions**: test_data_save, test_data_retrieval
**Requires Auth**: Yes

## 🔧 Configuration

### Environment Variables

- `TEST_REQUEST`: Natural language test request
- `PLAYWRIGHT_BASE_URL`: Base URL for testing (default: http://localhost:4405)
- `PLAYWRIGHT_ADMIN_USERNAME`: Admin username (default: admin)
- `PLAYWRIGHT_ADMIN_PASSWORD`: Admin password (default: temppass123)

### Test Timeouts

- Default timeout: 5 minutes (300,000ms)
- Individual action timeout: 10 seconds
- Page load timeout: 30 seconds

## 📊 Test Results

### Generated Files

1. **Screenshots**: `playwright/screenshots/smart-tests/`
   - Before and after each action
   - Error screenshots
   - Form state screenshots

2. **HTML Dumps**: `playwright/html-dumps/smart-tests/`
   - Page HTML for debugging
   - Form state analysis
   - Error page analysis

3. **Reports**: `playwright/smart-test-report.json`
   - Comprehensive test results
   - Error and warning summaries
   - Performance metrics

### Report Structure

```json
{
  "timestamp": "2025-07-14T01:00:00.000Z",
  "totalTests": 5,
  "passedTests": 4,
  "failedTests": 1,
  "totalErrors": 2,
  "totalWarnings": 3,
  "totalScreenshots": 15,
  "results": [...]
}
```

## 🎯 Example Test Requests

### Equipment Management
```bash
# Create and delete equipment
node run_smart_test.js "Make a new equipment with all req fields and delete it"

# Full CRUD cycle
node run_smart_test.js "Create equipment, edit it, then delete it"

# Equipment listing
node run_smart_test.js "List all equipment and verify data"
```

### Maintenance Workflow
```bash
# Create maintenance
node run_smart_test.js "Create maintenance for equipment"

# Maintenance management
node run_smart_test.js "Create and list maintenance schedules"
```

### Security Testing
```bash
# Authentication testing
node run_smart_test.js "Test login and logout functionality"

# Permission testing
node run_smart_test.js "Test access control for protected pages"

# Security validation
node run_smart_test.js "Verify unauthorized access is blocked"
```

### Comprehensive Testing
```bash
# Full application test
node run_smart_test.js "Explore all links and test everything"

# Form validation
node run_smart_test.js "Test form validation and error handling"

# Data integrity
node run_smart_test.js "Test data saving and retrieval"
```

## 🔍 Advanced Features

### Smart Authentication
- Automatically handles login/logout
- Maintains session state across tests
- Tests both authenticated and unauthenticated states

### Permission Verification
- Tests protected page access
- Verifies redirect behavior
- Validates authorization rules

### Form Testing
- Fills required fields automatically
- Tests validation errors
- Handles form submissions

### Error Detection
- Captures screenshots on errors
- Logs detailed error information
- Provides debugging context

### Link Discovery
- Automatically finds and tests all links
- Prevents infinite loops
- Limits exploration scope

## 🛠️ Troubleshooting

### Common Issues

1. **Authentication Fails**
   - Verify admin credentials in environment
   - Check if Django server is running
   - Ensure login URL is correct

2. **Page Not Found**
   - Verify base URL configuration
   - Check if application is accessible
   - Ensure proper port configuration

3. **Form Submission Fails**
   - Check form field selectors
   - Verify required fields are filled
   - Check for validation errors

4. **Timeout Errors**
   - Increase timeout values
   - Check server performance
   - Verify network connectivity

### Debug Mode

Enable debug mode for detailed logging:

```bash
DEBUG=true node run_smart_test.js "your test request"
```

### Manual Testing

For manual verification, you can run individual test files:

```bash
# Basic exploration
npx playwright test admin_explore.spec.ts --headed

# Smart testing
npx playwright test smart_test_runner.spec.ts --headed

# Advanced testing
npx playwright test advanced_test_runner.spec.ts --headed
```

## 📈 Integration with CI/CD

### GitHub Actions Example

```yaml
name: Smart Testing
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-node@v2
        with:
          node-version: '18'
      - run: npm install
      - run: npx playwright install
      - run: |
          docker-compose up -d
          sleep 30
          node playwright/run_smart_test.js "Test all functionality"
      - uses: actions/upload-artifact@v2
        with:
          name: test-results
          path: playwright/screenshots/
```

## 🤝 Contributing

### Adding New Test Scenarios

1. Add scenario to `scenarios` array in `advanced_test_runner.spec.ts`
2. Implement corresponding action methods
3. Update natural language parser
4. Add documentation

### Extending Natural Language Support

1. Add keywords to scenario definitions
2. Update `parseNaturalLanguageRequest` method
3. Test with various request formats
4. Update documentation

## 📚 Related Files

- `smart_test_runner.spec.ts`: Basic smart testing
- `advanced_test_runner.spec.ts`: Advanced testing with scenarios
- `run_smart_test.js`: CLI interface
- `admin_explore.spec.ts`: Comprehensive admin exploration
- `calendar.spec.ts`: Calendar-specific testing

---

**Need help?** Check the test reports and screenshots for detailed debugging information. 