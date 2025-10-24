#!/usr/bin/env python3
"""
Test if the clear_migrations command is available via the API.
"""

import requests
import json

# Configuration
BASE_URL = "https://dev.maintenance.errorlog.app"

def test_clear_migrations_availability():
    """Test if the clear_migrations command is available."""
    print("Test Clear Migrations Availability")
    print("=" * 50)
    print(f"Target: {BASE_URL}")
    print("=" * 50)
    
    api_url = f"{BASE_URL}/api/migrations/"
    
    # Test 1: Check if the API is responding
    print("\nTest 1: Checking API availability...")
    
    try:
        payload = {"command": "showmigrations"}
        response = requests.post(api_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("SUCCESS: API is responding")
            else:
                print(f"FAIL: API error: {result.get('error')}")
                return False
        else:
            print(f"FAIL: API returned status {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"FAIL: API request failed: {e}")
        return False
    
    # Test 2: Try to run clear_migrations command
    print("\nTest 2: Testing clear_migrations command...")
    
    try:
        payload = {"command": "clear_migrations"}
        response = requests.post(api_url, json=payload, timeout=60)
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Success: {result.get('success', False)}")
            print("Output:")
            print(result.get('output', 'No output'))
            print("Error:")
            print(result.get('error', 'No error'))
            return result.get('success', False)
        else:
            print(f"FAIL: Request failed with status {response.status_code}")
            print("Response content:")
            try:
                print(response.json())
            except:
                print(response.text)
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"FAIL: Request failed: {e}")
        return False

def main():
    """Main function."""
    success = test_clear_migrations_availability()
    
    print("\n" + "=" * 50)
    print("AVAILABILITY TEST SUMMARY")
    print("=" * 50)
    
    if success:
        print("SUCCESS: clear_migrations command is working!")
    else:
        print("FAIL: clear_migrations command is not working")
        print("\nPossible issues:")
        print("1. Command not deployed yet")
        print("2. Command has errors")
        print("3. API endpoint issue")
        print("4. Container restart needed")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
