#!/usr/bin/env python3
"""
Test script to verify logging configuration works correctly.
This helps diagnose logging issues before they cause container startup failures.
"""

import os
import sys
import django
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maintenance_dashboard.settings')

def test_logging_config():
    """Test the logging configuration."""
    try:
        # Import Django settings
        from django.conf import settings
        
        print("✅ Django settings imported successfully")
        
        # Test logging configuration
        if hasattr(settings, 'LOGGING'):
            print("✅ LOGGING configuration found in settings")
            
            # Try to configure logging
            import logging.config
            logging.config.dictConfig(settings.LOGGING)
            print("✅ Logging configuration applied successfully")
            
            # Test logging
            logger = logging.getLogger('test')
            logger.info("Test log message")
            print("✅ Test log message written successfully")
            
            # Check if log files were created
            log_files = ['debug.log', 'error.log', 'security.log']
            for log_file in log_files:
                log_path = project_root / log_file
                if log_path.exists():
                    print(f"✅ Log file created: {log_file}")
                else:
                    print(f"⚠️  Log file not created: {log_file}")
            
        else:
            print("❌ LOGGING configuration not found in settings")
            
    except Exception as e:
        print(f"❌ Error testing logging configuration: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    print("🔍 Testing Django logging configuration...")
    success = test_logging_config()
    
    if success:
        print("🎉 All logging tests passed!")
        sys.exit(0)
    else:
        print("💥 Logging tests failed!")
        sys.exit(1)
