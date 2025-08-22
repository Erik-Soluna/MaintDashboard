#!/usr/bin/env python3
"""
CSV Import Test Runner
Automatically tests the enhanced CSV import functionality.
Run this script to verify all features are working correctly.
"""

import os
import sys
import django
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maintenance_dashboard.settings')
django.setup()

from django.test import TestCase
from django.test.runner import DiscoverRunner
from django.conf import settings


def run_csv_import_tests():
    """Run the CSV import tests and report results."""
    print("🧪 Running CSV Import Tests...")
    print("=" * 50)
    
    # Create test runner
    runner = DiscoverRunner(verbosity=2)
    
    # Run tests
    start_time = time.time()
    result = runner.run_tests(['tests.test_csv_import'])
    end_time = time.time()
    
    # Report results
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    if result.wasSuccessful():
        print("✅ All tests passed successfully!")
        print(f"⏱️  Total test time: {end_time - start_time:.2f} seconds")
        
        # Print test counts
        if hasattr(result, 'test_count'):
            print(f"📋 Tests run: {result.test_count}")
        if hasattr(result, 'failure_count'):
            print(f"❌ Failures: {result.failure_count}")
        if hasattr(result, 'error_count'):
            print(f"💥 Errors: {result.error_count}")
        
        print("\n🎉 CSV Import functionality is working correctly!")
        return True
    else:
        print("❌ Some tests failed!")
        print(f"⏱️  Total test time: {end_time - start_time:.2f} seconds")
        
        # Print detailed failure information
        if hasattr(result, 'failures'):
            print(f"\n❌ Failures ({len(result.failures)}):")
            for test, traceback in result.failures:
                print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip()}")
        
        if hasattr(result, 'errors'):
            print(f"\n💥 Errors ({len(result.errors)}):")
            for test, traceback in result.errors:
                print(f"  - {test}: {traceback.split('Exception:')[-1].strip()}")
        
        print("\n🔧 Please fix the failing tests before proceeding.")
        return False


def run_specific_test(test_name):
    """Run a specific test by name."""
    print(f"🧪 Running specific test: {test_name}")
    print("=" * 50)
    
    # Import the test module
    from tests.test_csv_import import CSVImportTestCase, CSVImportIntegrationTest
    
    # Find the test method
    test_method = None
    test_class = None
    
    for test_class in [CSVImportTestCase, CSVImportIntegrationTest]:
        if hasattr(test_class, test_name):
            test_method = getattr(test_class, test_name)
            break
    
    if not test_method:
        print(f"❌ Test method '{test_name}' not found!")
        return False
    
    # Create test instance and run the test
    test_instance = test_class()
    test_instance.setUp()
    
    try:
        test_method(test_instance)
        print(f"✅ Test '{test_name}' passed!")
        return True
    except Exception as e:
        print(f"❌ Test '{test_name}' failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        test_instance.tearDown()


def list_available_tests():
    """List all available test methods."""
    print("📋 Available CSV Import Tests:")
    print("=" * 50)
    
    from tests.test_csv_import import CSVImportTestCase, CSVImportIntegrationTest
    
    print("\n🔧 Unit Tests (CSVImportTestCase):")
    for attr_name in dir(CSVImportTestCase):
        if attr_name.startswith('test_'):
            print(f"  - {attr_name}")
    
    print("\n🔗 Integration Tests (CSVImportIntegrationTest):")
    for attr_name in dir(CSVImportIntegrationTest):
        if attr_name.startswith('test_'):
            print(f"  - {attr_name}")
    
    print(f"\n💡 Run a specific test with: python {__file__} <test_name>")
    print(f"💡 Run all tests with: python {__file__}")


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'list':
            list_available_tests()
        elif command == 'help':
            print("CSV Import Test Runner")
            print("Usage:")
            print(f"  python {__file__}           # Run all tests")
            print(f"  python {__file__} list      # List available tests")
            print(f"  python {__file__} <test>    # Run specific test")
            print(f"  python {__file__} help      # Show this help")
        elif command.startswith('test_'):
            success = run_specific_test(command)
            sys.exit(0 if success else 1)
        else:
            print(f"❌ Unknown command: {command}")
            print(f"💡 Use 'python {__file__} help' for usage information")
            sys.exit(1)
    else:
        # Run all tests
        success = run_csv_import_tests()
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
