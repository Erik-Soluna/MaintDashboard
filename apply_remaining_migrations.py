#!/usr/bin/env python3
"""
Apply the remaining migrations that are still pending.
"""

import requests
import json

# Configuration
BASE_URL = "https://dev.maintenance.errorlog.app"

def apply_remaining_migrations():
    """Apply the remaining migrations."""
    print("Apply Remaining Migrations")
    print("=" * 50)
    print(f"Target: {BASE_URL}")
    print("=" * 50)
    
    api_url = f"{BASE_URL}/api/migrations/"
    
    # Step 1: Check current migration status
    print("\nStep 1: Checking current migration status...")
    
    try:
        payload = {"command": "showmigrations"}
        response = requests.post(api_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("SUCCESS: Migration status retrieved")
                print("Current migration status:")
                print(result.get('output', 'No output'))
            else:
                print(f"FAIL: Migration status error: {result.get('error')}")
                return False
        else:
            print(f"FAIL: Migration status request failed: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"FAIL: Migration status request failed: {e}")
        return False
    
    # Step 2: Apply remaining migrations
    print("\nStep 2: Applying remaining migrations...")
    
    try:
        payload = {"command": "migrate"}
        response = requests.post(api_url, json=payload, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            print(f"SUCCESS: Migrations applied")
            print("Migration output:")
            print(result.get('output', 'No output'))
        else:
            print(f"FAIL: Migration request failed: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"FAIL: Migration request failed: {e}")
        return False
    
    # Step 3: Verify migration status after applying
    print("\nStep 3: Verifying migration status after applying...")
    
    try:
        payload = {"command": "showmigrations"}
        response = requests.post(api_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("SUCCESS: Migration status verified")
                print("Final migration status:")
                print(result.get('output', 'No output'))
            else:
                print(f"FAIL: Migration status verification error: {result.get('error')}")
                return False
        else:
            print(f"FAIL: Migration status verification request failed: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"FAIL: Migration status verification request failed: {e}")
        return False
    
    # Step 4: Test login after applying migrations
    print("\nStep 4: Testing login after applying migrations...")
    
    try:
        session = requests.Session()
        
        # Get login page
        login_url = f"{BASE_URL}/auth/login/"
        response = session.get(login_url, timeout=30)
        
        if response.status_code != 200:
            print(f"FAIL: Could not get login page: {response.status_code}")
            return False
        
        # Extract CSRF token
        import re
        csrf_token = None
        patterns = [
            r'name="csrfmiddlewaretoken"\s+value="([^"]+)"',
            r'csrfmiddlewaretoken["\']?\s*[:=]\s*["\']([^"\']+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response.text, re.IGNORECASE)
            if match:
                csrf_token = match.group(1)
                break
        
        if not csrf_token:
            print("FAIL: Could not extract CSRF token")
            return False
        
        # Try login
        login_data = {
            'username': 'admin',
            'password': 'temppass123',
            'csrfmiddlewaretoken': csrf_token
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': login_url,
        }
        
        response = session.post(login_url, data=login_data, headers=headers, timeout=30, allow_redirects=False)
        
        print(f"Login response status: {response.status_code}")
        
        if response.status_code == 302:
            location = response.headers.get('Location', '')
            print(f"SUCCESS: Login successful! Redirected to: {location}")
            return True
        elif response.status_code == 200:
            if 'invalid' not in response.text.lower() and 'incorrect' not in response.text.lower():
                print("SUCCESS: Login successful (no redirect)")
                return True
            else:
                print("FAIL: Invalid credentials")
                return False
        else:
            print(f"FAIL: Login failed with status {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"FAIL: Login test failed: {e}")
        return False

def main():
    """Main function."""
    success = apply_remaining_migrations()
    
    print("\n" + "=" * 50)
    print("REMAINING MIGRATIONS SUMMARY")
    print("=" * 50)
    
    if success:
        print("SUCCESS: All remaining migrations applied successfully!")
        print("Login functionality should now work.")
        print("\nYou can log in at:")
        print(f"{BASE_URL}/auth/login/")
        print("Username: admin")
        print("Password: temppass123")
        print("\nThe database migration issue has been completely resolved!")
    else:
        print("FAIL: Some migrations may still be pending")
        print("Manual intervention may be required.")
        print("\nNext steps:")
        print("1. Check container logs in Portainer")
        print("2. Restart the web container")
        print("3. Check if all migrations were applied")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
