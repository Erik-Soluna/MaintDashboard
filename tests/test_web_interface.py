#!/usr/bin/env python3
"""
Test script to verify the web interface for generate_pods works.
"""

import requests
import json

def test_generate_pods_web_interface():
    """Test the generate_pods web interface."""
    base_url = "http://localhost:4405"
    
    print("Testing generate_pods web interface...")
    
    # Test 1: Check if the locations settings page loads
    print("1. Testing locations settings page...")
    try:
        response = requests.get(f"{base_url}/core/settings/locations/")
        if response.status_code == 200:
            print("✅ Locations settings page loads successfully")
            if "Generate PODs" in response.text:
                print("✅ Generate PODs button is present")
            else:
                print("❌ Generate PODs button not found")
                return False
        else:
            print(f"❌ Locations settings page failed to load: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error accessing locations settings page: {e}")
        return False
    
    # Test 2: Test the generate_pods API endpoint
    print("\n2. Testing generate_pods API endpoint...")
    try:
        # First, we need to get a CSRF token by accessing the page
        session = requests.Session()
        response = session.get(f"{base_url}/core/settings/locations/")
        
        # Extract CSRF token from the page
        csrf_token = None
        if 'csrfmiddlewaretoken' in response.text:
            import re
            match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.text)
            if match:
                csrf_token = match.group(1)
        
        if not csrf_token:
            print("❌ Could not extract CSRF token")
            return False
        
        # Test the generate_pods endpoint
        headers = {
            'X-CSRFToken': csrf_token,
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        
        data = {
            'pod_count': '2',
            'mdcs_per_pod': '1',
            'force': 'false'
        }
        
        response = session.post(f"{base_url}/core/locations/generate-pods/", 
                              data=data, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ generate_pods API endpoint works successfully")
                print(f"   Output: {result.get('output', 'No output')}")
            else:
                print(f"❌ generate_pods API returned error: {result.get('error')}")
                return False
        else:
            print(f"❌ generate_pods API endpoint failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing generate_pods API: {e}")
        return False
    
    print("\n✅ All tests passed! The generate_pods functionality is working correctly.")
    return True

if __name__ == '__main__':
    success = test_generate_pods_web_interface()
    exit(0 if success else 1) 