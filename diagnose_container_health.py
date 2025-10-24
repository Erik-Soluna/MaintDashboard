#!/usr/bin/env python3
"""
Diagnose container health issues by checking logs and status.
"""

import requests
import json
import time

# Configuration
BASE_URL = "https://dev.maintenance.errorlog.app"

def check_application_health():
    """Check if the application is responding."""
    print("Checking application health...")
    
    try:
        # Try to access the main page
        response = requests.get(BASE_URL, timeout=10)
        print(f"Main page status: {response.status_code}")
        
        if response.status_code == 200:
            print("SUCCESS: Application is responding")
            return True
        else:
            print(f"FAIL: Application returned status {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"FAIL: Application is not responding: {e}")
        return False

def check_login_page():
    """Check if the login page is accessible."""
    print("\nChecking login page...")
    
    try:
        login_url = f"{BASE_URL}/auth/login/"
        response = requests.get(login_url, timeout=10)
        print(f"Login page status: {response.status_code}")
        
        if response.status_code == 200:
            print("SUCCESS: Login page is accessible")
            
            # Check for django_session error in the response
            if 'django_session' in response.text and 'does not exist' in response.text:
                print("FAIL: django_session error found in login page")
                return False
            else:
                print("SUCCESS: No django_session error in login page")
                return True
        else:
            print(f"FAIL: Login page returned status {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"FAIL: Login page is not accessible: {e}")
        return False

def check_api_endpoints():
    """Check if API endpoints are working."""
    print("\nChecking API endpoints...")
    
    endpoints = [
        "/api/migrations/",
        "/version/",
        "/health/"
    ]
    
    working_endpoints = []
    broken_endpoints = []
    
    for endpoint in endpoints:
        try:
            url = f"{BASE_URL}{endpoint}"
            response = requests.get(url, timeout=10)
            print(f"{endpoint}: {response.status_code}")
            
            if response.status_code in [200, 405]:  # 405 is OK for POST-only endpoints
                working_endpoints.append(endpoint)
            else:
                broken_endpoints.append(endpoint)
                
        except requests.exceptions.RequestException as e:
            print(f"{endpoint}: ERROR - {e}")
            broken_endpoints.append(endpoint)
    
    print(f"\nWorking endpoints: {working_endpoints}")
    print(f"Broken endpoints: {broken_endpoints}")
    
    return len(broken_endpoints) == 0

def test_database_connection():
    """Test database connection via API."""
    print("\nTesting database connection...")
    
    try:
        # Try to get migration status
        api_url = f"{BASE_URL}/api/migrations/"
        payload = {"command": "showmigrations"}
        
        response = requests.post(api_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("SUCCESS: Database connection is working")
                print("Migration status retrieved successfully")
                return True
            else:
                print(f"FAIL: Database API error: {result.get('error')}")
                return False
        else:
            print(f"FAIL: Database API returned status {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"FAIL: Database connection test failed: {e}")
        return False

def check_specific_errors():
    """Check for specific error patterns."""
    print("\nChecking for specific error patterns...")
    
    error_patterns = [
        "django_session",
        "relation.*does not exist",
        "ProgrammingError",
        "OperationalError",
        "connection.*refused",
        "database.*error"
    ]
    
    try:
        # Check main page for errors
        response = requests.get(BASE_URL, timeout=10)
        page_content = response.text.lower()
        
        found_errors = []
        for pattern in error_patterns:
            if pattern in page_content:
                found_errors.append(pattern)
        
        if found_errors:
            print(f"FAIL: Found error patterns: {found_errors}")
            return False
        else:
            print("SUCCESS: No obvious error patterns found")
            return True
            
    except requests.exceptions.RequestException as e:
        print(f"FAIL: Error checking failed: {e}")
        return False

def main():
    """Main diagnostic function."""
    print("Container Health Diagnostic Script")
    print("=" * 50)
    print(f"Target: {BASE_URL}")
    print("=" * 50)
    
    # Run all diagnostic checks
    checks = [
        ("Application Health", check_application_health),
        ("Login Page", check_login_page),
        ("API Endpoints", check_api_endpoints),
        ("Database Connection", test_database_connection),
        ("Error Patterns", check_specific_errors)
    ]
    
    results = {}
    
    for check_name, check_func in checks:
        print(f"\n{'-' * 30}")
        print(f"Running: {check_name}")
        print(f"{'-' * 30}")
        
        try:
            result = check_func()
            results[check_name] = result
        except Exception as e:
            print(f"FAIL: Check failed with exception: {e}")
            results[check_name] = False
        
        time.sleep(1)  # Brief pause between checks
    
    # Summary
    print(f"\n{'=' * 50}")
    print("DIAGNOSTIC SUMMARY")
    print(f"{'=' * 50}")
    
    passed_checks = sum(1 for result in results.values() if result)
    total_checks = len(results)
    
    for check_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"{check_name}: {status}")
    
    print(f"\nOverall: {passed_checks}/{total_checks} checks passed")
    
    if passed_checks == total_checks:
        print("\nSUCCESS: All checks passed! The container appears to be healthy.")
    elif passed_checks >= total_checks * 0.6:
        print("\nWARNING: Most checks passed. Minor issues detected.")
    else:
        print("\nERROR: Multiple checks failed. Container has serious issues.")
        print("\nRecommended actions:")
        print("1. Check container logs in Portainer")
        print("2. Restart the web container")
        print("3. Check resource limits")
        print("4. Verify environment variables")
    
    print(f"\n{'=' * 50}")
    print("Diagnostic completed.")

if __name__ == "__main__":
    main()
