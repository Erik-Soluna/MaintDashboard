#!/usr/bin/env python3
"""
Debug 403 error during login.
"""

import requests
import json
import re

# Configuration
BASE_URL = "https://dev.maintenance.errorlog.app"

def debug_403_error():
    """Debug the 403 error during login."""
    print("Debug 403 Error")
    print("=" * 50)
    print(f"Target: {BASE_URL}")
    print("=" * 50)
    
    session = requests.Session()
    
    try:
        # Step 1: Get login page and examine it
        print("\nStep 1: Getting login page...")
        login_url = f"{BASE_URL}/auth/login/"
        response = session.get(login_url, timeout=30)
        
        print(f"Login page status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
        
        if response.status_code != 200:
            print(f"FAIL: Login page returned status {response.status_code}")
            return False
        
        # Step 2: Look for CSRF token and form details
        print("\nStep 2: Analyzing login form...")
        
        # Extract CSRF token
        csrf_token = None
        patterns = [
            r'name="csrfmiddlewaretoken"\s+value="([^"]+)"',
            r'csrfmiddlewaretoken["\']?\s*[:=]\s*["\']([^"\']+)',
            r'<input[^>]*name=["\']csrfmiddlewaretoken["\'][^>]*value=["\']([^"\']+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response.text, re.IGNORECASE)
            if match:
                csrf_token = match.group(1)
                break
        
        if csrf_token:
            print(f"SUCCESS: CSRF token found: {csrf_token[:20]}...")
        else:
            print("FAIL: No CSRF token found")
            print("Form content preview:")
            # Look for form elements
            form_match = re.search(r'<form[^>]*>.*?</form>', response.text, re.DOTALL | re.IGNORECASE)
            if form_match:
                print(form_match.group(0)[:500] + "..." if len(form_match.group(0)) > 500 else form_match.group(0))
            else:
                print("No form found in response")
            return False
        
        # Step 3: Check for any error messages in the page
        print("\nStep 3: Checking for error messages...")
        error_patterns = [
            r'error[^>]*>([^<]+)',
            r'alert[^>]*>([^<]+)',
            r'warning[^>]*>([^<]+)',
            r'django_session.*does not exist',
            r'ProgrammingError',
            r'relation.*does not exist'
        ]
        
        found_errors = []
        for pattern in error_patterns:
            matches = re.findall(pattern, response.text, re.IGNORECASE)
            if matches:
                found_errors.extend(matches)
        
        if found_errors:
            print("Found potential error messages:")
            for error in found_errors[:5]:  # Show first 5 errors
                print(f"  - {error.strip()}")
        else:
            print("No obvious error messages found")
        
        # Step 4: Try login with proper headers
        print("\nStep 4: Attempting login with proper headers...")
        
        # Set proper headers
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': login_url,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        login_data = {
            'username': 'admin',
            'password': 'temppass123',
            'csrfmiddlewaretoken': csrf_token
        }
        
        response = session.post(login_url, data=login_data, headers=headers, timeout=30, allow_redirects=False)
        
        print(f"Login response status: {response.status_code}")
        print(f"Response headers:")
        for key, value in response.headers.items():
            if key.lower() in ['content-type', 'location', 'set-cookie']:
                print(f"  {key}: {value}")
        
        # Step 5: Analyze response content
        print("\nStep 5: Analyzing response content...")
        
        if response.status_code == 403:
            print("403 Forbidden response received")
            
            # Look for specific error messages
            content = response.text.lower()
            if 'csrf' in content:
                print("ERROR: CSRF token issue detected")
            elif 'permission' in content:
                print("ERROR: Permission issue detected")
            elif 'forbidden' in content:
                print("ERROR: Forbidden access")
            elif 'django_session' in content:
                print("ERROR: django_session table issue detected")
            else:
                print("ERROR: Unknown 403 cause")
            
            # Show response content preview
            print("Response content preview:")
            print(response.text[:1000] + "..." if len(response.text) > 1000 else response.text)
            
        elif response.status_code == 302:
            location = response.headers.get('Location', '')
            print(f"SUCCESS: Login successful! Redirected to: {location}")
            return True
            
        elif response.status_code == 200:
            if 'invalid' in response.text.lower() or 'incorrect' in response.text.lower():
                print("FAIL: Invalid credentials")
            else:
                print("SUCCESS: Login successful (no redirect)")
                return True
        else:
            print(f"Unexpected response status: {response.status_code}")
            print("Response content preview:")
            print(response.text[:500] + "..." if len(response.text) > 500 else response.text)
        
        return False
        
    except requests.exceptions.RequestException as e:
        print(f"FAIL: Request failed: {e}")
        return False

def test_direct_api_access():
    """Test direct API access to see if it's a session issue."""
    print("\n" + "=" * 50)
    print("Testing Direct API Access")
    print("=" * 50)
    
    try:
        # Test the migrations API
        api_url = f"{BASE_URL}/api/migrations/"
        payload = {"command": "showmigrations"}
        
        response = requests.post(api_url, json=payload, timeout=30)
        
        print(f"API response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("SUCCESS: API access working")
                return True
            else:
                print(f"FAIL: API error: {result.get('error')}")
        else:
            print(f"FAIL: API returned status {response.status_code}")
        
        return False
        
    except requests.exceptions.RequestException as e:
        print(f"FAIL: API request failed: {e}")
        return False

def main():
    """Main function."""
    # Debug 403 error
    login_success = debug_403_error()
    
    # Test API access
    api_success = test_direct_api_access()
    
    # Summary
    print("\n" + "=" * 50)
    print("DEBUG SUMMARY")
    print("=" * 50)
    
    if login_success:
        print("SUCCESS: Login is working!")
    else:
        print("FAIL: Login still has issues")
    
    if api_success:
        print("SUCCESS: API access is working")
    else:
        print("FAIL: API access has issues")
    
    if not login_success:
        print("\nTroubleshooting recommendations:")
        print("1. Check if django_session table exists")
        print("2. Verify CSRF settings in Django")
        print("3. Check session configuration")
        print("4. Look at container logs for detailed errors")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
