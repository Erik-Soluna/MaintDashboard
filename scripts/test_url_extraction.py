#!/usr/bin/env python3
"""
Test script for URL-based version extraction
"""

import sys
import os
import json

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up Django
import django
from django.conf import settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maintenance_dashboard.settings')
django.setup()

from core.url_version_extractor import URLVersionExtractor

def test_url_extraction():
    """Test URL extraction with sample URLs"""
    
    extractor = URLVersionExtractor()
    
    # Test URLs
    test_urls = [
        "https://github.com/microsoft/vscode",
        "https://github.com/django/django",
        "https://github.com/microsoft/vscode/commit/a1b2c3d",
        "https://gitlab.com/gitlab-org/gitlab",
    ]
    
    print("🧪 Testing URL-based Version Extraction")
    print("=" * 50)
    
    for url in test_urls:
        print(f"\n🔗 Testing URL: {url}")
        print("-" * 40)
        
        try:
            result = extractor.extract_from_url(url)
            
            if 'error' in result:
                print(f"❌ Error: {result['error']}")
                if 'supported' in result:
                    print(f"💡 Supported: {', '.join(result['supported'])}")
            else:
                print(f"✅ Success!")
                print(f"   Version: {result.get('version', 'N/A')}")
                print(f"   Commit: {result.get('commit_hash', 'N/A')}")
                print(f"   Branch: {result.get('branch', 'N/A')}")
                print(f"   Date: {result.get('commit_date', 'N/A')}")
                if 'commit_message' in result:
                    print(f"   Message: {result['commit_message']}")
                if 'source_url' in result:
                    print(f"   Source: {result['source_url']}")
                    
        except Exception as e:
            print(f"❌ Exception: {str(e)}")

if __name__ == "__main__":
    test_url_extraction()
