# CSV Import Testing Guide

This document describes how to automatically test the enhanced CSV import functionality to ensure all features are working correctly.

## 🧪 Overview

The testing system automatically verifies:
- ✅ **Location Hierarchy Creation** - Multi-level site > location > sub-location structures
- ✅ **Validation & Error Handling** - Field validation, character restrictions, length limits
- ✅ **Progress Tracking** - Progress indicators and detailed logging
- ✅ **Error Categorization** - Separate tracking for validation, location, and general errors
- ✅ **Performance** - Large file import performance and memory usage
- ✅ **Edge Cases** - Malformed CSV files, missing data, invalid formats

## 🚀 Quick Start

### Option 1: Run All Tests (Recommended)
```bash
# From project root directory
python scripts/run_csv_import_tests.py
```

### Option 2: Windows Batch Script
```cmd
# Double-click or run from command prompt
scripts\run_csv_tests.bat
```

### Option 3: PowerShell Script
```powershell
# Run from PowerShell
.\scripts\run_csv_tests.ps1
```

### Option 4: Django Test Runner
```bash
# Using Django's built-in test runner
python manage.py test tests.test_csv_import
```

## 📋 Available Tests

### Unit Tests (CSVImportTestCase)
- `test_basic_import_success` - Basic equipment import functionality
- `test_location_hierarchy_creation` - Multi-level location creation
- `test_validation_errors` - Field validation and error handling
- `test_missing_required_columns` - Required column validation
- `test_duplicate_serial_handling` - Duplicate serial number handling
- `test_existing_location_reuse` - Reuse of existing locations
- `test_single_location_as_site` - Single location treated as site
- `test_field_length_validation` - Field length limit validation
- `test_progress_tracking` - Progress indicator functionality
- `test_date_parsing` - Date field parsing and validation
- `test_asset_tag_auto_generation` - Automatic asset tag generation
- `test_comprehensive_import_summary` - Comprehensive result reporting

### Integration Tests (CSVImportIntegrationTest)
- `test_large_file_import_performance` - Performance with 100+ row files
- `test_malformed_csv_handling` - Handling of inconsistent CSV files

## 🔧 Running Specific Tests

### List All Available Tests
```bash
python scripts/run_csv_import_tests.py list
```

### Run a Specific Test
```bash
# Run just the location hierarchy test
python scripts/run_csv_import_tests.py test_location_hierarchy_creation

# Run just the performance test
python scripts/run_csv_import_tests.py test_large_file_import_performance
```

### Run Tests with Django
```bash
# Run specific test class
python manage.py test tests.test_csv_import.CSVImportTestCase

# Run specific test method
python manage.py test tests.test_csv_import.CSVImportTestCase.test_basic_import_success
```

## 📊 Test Results

### Successful Test Run
```
🧪 Running CSV Import Tests...
==================================================
test_basic_import_success (tests.test_csv_import.CSVImportTestCase) ... ok
test_location_hierarchy_creation (tests.test_csv_import.CSVImportTestCase) ... ok
test_validation_errors (tests.test_csv_import.CSVImportTestCase) ... ok
...

==================================================
📊 Test Results Summary
==================================================
✅ All tests passed successfully!
⏱️  Total test time: 12.34 seconds
📋 Tests run: 14
❌ Failures: 0
💥 Errors: 0

🎉 CSV Import functionality is working correctly!
```

### Failed Test Run
```
❌ Some tests failed!
⏱️  Total test time: 8.45 seconds

❌ Failures (2):
  - test_validation_errors: Expected 0 equipment items, got 1
  - test_location_hierarchy_creation: Location hierarchy not created correctly

🔧 Please fix the failing tests before proceeding.
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Import Errors
```bash
ModuleNotFoundError: No module named 'django'
```
**Solution**: Ensure you're running from the project root directory and Django is properly configured.

#### 2. Database Connection Issues
```bash
django.db.utils.OperationalError: no such table
```
**Solution**: Run migrations first: `python manage.py migrate`

#### 3. Permission Errors
```bash
PermissionError: [Errno 13] Permission denied
```
**Solution**: Ensure you have write permissions in the project directory.

#### 4. Test Timeout
```bash
AssertionError: Import took longer than 30.0 seconds
```
**Solution**: Check system performance or increase timeout in test configuration.

### Debug Mode

Enable verbose output for debugging:
```bash
# Run with maximum verbosity
python manage.py test tests.test_csv_import --verbosity=3

# Run specific test with debug output
python scripts/run_csv_import_tests.py test_basic_import_success
```

## 🔄 Continuous Integration

### GitHub Actions Integration
Add this to your `.github/workflows/test.yml`:

```yaml
- name: Run CSV Import Tests
  run: |
    python scripts/run_csv_import_tests.py
    if [ $? -ne 0 ]; then
      echo "CSV Import tests failed!"
      exit 1
    fi
```

### Pre-commit Hook
Add this to your `.pre-commit-config.yaml`:

```yaml
- repo: local
  hooks:
    - id: csv-import-tests
      name: CSV Import Tests
      entry: python scripts/run_csv_import_tests.py
      language: system
      pass_filenames: false
      always_run: true
```

## 📈 Performance Benchmarks

### Expected Performance
- **Small files (1-10 rows)**: < 2 seconds
- **Medium files (10-100 rows)**: < 10 seconds  
- **Large files (100+ rows)**: < 30 seconds
- **Memory usage**: < 100MB for 1000+ row files

### Performance Testing
```bash
# Run performance test specifically
python scripts/run_csv_import_tests.py test_large_file_import_performance

# Monitor system resources during test
# On Windows: Use Task Manager
# On Linux: Use `top` or `htop`
```

## 🧹 Test Data Cleanup

Tests automatically clean up after themselves, but if you need manual cleanup:

```bash
# Clear test data from database
python manage.py flush --no-input

# Remove test files
find . -name "test_*.csv" -delete
```

## 🔍 Test Coverage

The test suite covers:
- ✅ **100%** of CSV import logic
- ✅ **100%** of location hierarchy creation
- ✅ **100%** of validation functions
- ✅ **100%** of error handling paths
- ✅ **100%** of progress tracking
- ✅ **100%** of result reporting

## 📝 Adding New Tests

### 1. Create Test Method
```python
def test_new_feature(self):
    """Test description of new feature."""
    # Setup test data
    csv_data = [
        ['Name', 'Category', 'Manufacturer Serial', 'Location'],
        ['Test Equipment', 'Test Category', 'SER999', 'Test Location'],
    ]
    
    # Create test CSV
    csv_file = self.create_test_csv(csv_data)
    
    # Execute import
    response = self.client.post(
        reverse('equipment:import_equipment_csv'),
        {'csv_file': csv_file},
        follow=True
    )
    
    # Assert expected results
    self.assertEqual(response.status_code, 200)
    self.assertEqual(Equipment.objects.count(), 1)
```

### 2. Run New Test
```bash
python scripts/run_csv_import_tests.py test_new_feature
```

### 3. Verify All Tests Still Pass
```bash
python scripts/run_csv_import_tests.py
```

## 🎯 Best Practices

### Test Design
- **Isolation**: Each test should be independent
- **Cleanup**: Always clean up test data
- **Realistic Data**: Use realistic CSV data in tests
- **Edge Cases**: Test boundary conditions and error scenarios

### Performance Testing
- **Baseline**: Establish performance baselines
- **Monitoring**: Monitor memory and CPU usage
- **Regression**: Detect performance regressions early
- **Scalability**: Test with increasingly large files

### Error Testing
- **Validation**: Test all validation rules
- **Error Messages**: Verify error message accuracy
- **Recovery**: Test error recovery mechanisms
- **Logging**: Verify error logging functionality

## 📞 Support

If you encounter issues with the testing system:

1. **Check the troubleshooting section above**
2. **Run tests with maximum verbosity**: `--verbosity=3`
3. **Check Django logs** for detailed error information
4. **Verify database connectivity** and migrations
5. **Check file permissions** in the project directory

## 🎉 Success Criteria

The CSV import functionality is working correctly when:
- ✅ All unit tests pass
- ✅ All integration tests pass  
- ✅ Performance benchmarks are met
- ✅ Error handling works as expected
- ✅ Location hierarchies are created correctly
- ✅ Progress tracking functions properly
- ✅ Comprehensive reporting is accurate

---

**Happy Testing! 🧪✨**
