#!/usr/bin/env python3
"""
Run the clear_migrations command to fix the database migration issues.
"""

import requests
import json
import time

# Configuration
BASE_URL = "https://dev.maintenance.errorlog.app"

def run_clear_migrations():
    """Run the clear_migrations command via API."""
    print("Run Clear Migrations Command")
    print("=" * 50)
    print(f"Target: {BASE_URL}")
    print("=" * 50)
    
    api_url = f"{BASE_URL}/api/migrations/"
    
    print("\nThis will:")
    print("1. Drop the django_migrations table")
    print("2. Drop all application tables")
    print("3. Remove all migration files")
    print("4. Create fresh migrations")
    print("5. Apply them properly")
    print("6. Create admin user")
    
    print("\nWARNING: This is a destructive operation!")
    print("All data will be lost!")
    
    # Wait a moment for the user to read
    time.sleep(3)
    
    print("\nRunning clear_migrations command...")
    
    try:
        payload = {"command": "clear_migrations"}
        response = requests.post(api_url, json=payload, timeout=300)  # 5 minute timeout
        
        if response.status_code == 200:
            result = response.json()
            print(f"Clear migrations result: {result.get('success', False)}")
            print("Clear migrations output:")
            print(result.get('output', 'No output'))
            
            if result.get('success'):
                print("\nSUCCESS: Clear migrations completed!")
                
                # Wait a moment for the system to settle
                print("Waiting for system to settle...")
                time.sleep(10)
                
                # Test login
                print("\nTesting login after clear migrations...")
                return test_login()
            else:
                print(f"\nFAIL: Clear migrations failed: {result.get('error')}")
                return False
        else:
            print(f"\nFAIL: Clear migrations request failed: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"\nFAIL: Clear migrations request failed: {e}")
        return False

def test_login():
    """Test login after clear migrations."""
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
    success = run_clear_migrations()
    
    print("\n" + "=" * 50)
    print("CLEAR MIGRATIONS SUMMARY")
    print("=" * 50)
    
    if success:
        print("SUCCESS: Clear migrations completed successfully!")
        print("Login functionality should now work.")
        print("\nYou can log in at:")
        print(f"{BASE_URL}/auth/login/")
        print("Username: admin")
        print("Password: temppass123")
        print("\nThe database migration issue has been resolved!")
    else:
        print("FAIL: Clear migrations did not resolve the issue")
        print("Manual intervention may be required.")
        print("\nNext steps:")
        print("1. Check container logs in Portainer")
        print("2. Restart the web container")
        print("3. Check if the clear_migrations command was deployed")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
