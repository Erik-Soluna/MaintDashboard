#!/usr/bin/env python3
"""
Force create django_session table by directly creating it via SQL.
"""

import requests
import json

# Configuration
BASE_URL = "https://dev.maintenance.errorlog.app"

def create_session_table_direct():
    """Create django_session table directly via SQL."""
    print("Force Creating django_session Table Directly")
    print("=" * 50)
    print(f"Target: {BASE_URL}")
    print("=" * 50)
    
    # Step 1: Check current migration status
    print("\nStep 1: Checking current migration status...")
    api_url = f"{BASE_URL}/api/migrations/"
    
    try:
        payload = {"command": "showmigrations"}
        response = requests.post(api_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("SUCCESS: Migration status retrieved")
                output = result.get('output', '')
                
                # Look for sessions migration
                if 'sessions' in output:
                    print("Sessions migration status:")
                    for line in output.split('\n'):
                        if 'sessions' in line:
                            print(f"  {line.strip()}")
                else:
                    print("WARNING: No sessions migration found in output")
            else:
                print(f"FAIL: Migration status error: {result.get('error')}")
                return False
        else:
            print(f"FAIL: Migration status request failed: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"FAIL: Migration status request failed: {e}")
        return False
    
    # Step 2: Try to run sessions migration specifically
    print("\nStep 2: Running sessions migration...")
    
    try:
        payload = {"command": "migrate", "app": "sessions", "fake": False}
        response = requests.post(api_url, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("SUCCESS: Sessions migration completed")
                print("Migration output:")
                print(result.get('output', 'No output'))
            else:
                print(f"FAIL: Sessions migration error: {result.get('error')}")
                print("Error output:")
                print(result.get('output', 'No output'))
        else:
            print(f"FAIL: Sessions migration request failed: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"FAIL: Sessions migration request failed: {e}")
        return False
    
    # Step 3: Try to create the table directly via SQL
    print("\nStep 3: Creating django_session table directly...")
    
    try:
        # Create the django_session table SQL
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS django_session (
            session_key VARCHAR(40) NOT NULL PRIMARY KEY,
            session_data TEXT NOT NULL,
            expire_date TIMESTAMP WITH TIME ZONE NOT NULL
        );
        CREATE INDEX IF NOT EXISTS django_session_expire_date_idx ON django_session (expire_date);
        """
        
        payload = {
            "command": "dbshell",
            "sql": create_table_sql
        }
        
        response = requests.post(api_url, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("SUCCESS: django_session table created directly")
                print("SQL output:")
                print(result.get('output', 'No output'))
            else:
                print(f"FAIL: Direct table creation error: {result.get('error')}")
                print("Error output:")
                print(result.get('output', 'No output'))
        else:
            print(f"FAIL: Direct table creation request failed: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"FAIL: Direct table creation request failed: {e}")
    
    # Step 4: Test login again
    print("\nStep 4: Testing login after table creation...")
    
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
            if response.status_code == 500:
                print("500 Internal Server Error - likely still a database issue")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"FAIL: Login test failed: {e}")
        return False

def main():
    """Main function."""
    success = create_session_table_direct()
    
    print("\n" + "=" * 50)
    print("SESSION TABLE CREATION SUMMARY")
    print("=" * 50)
    
    if success:
        print("SUCCESS: django_session table issue resolved!")
        print("Login functionality should now work.")
        print("\nYou can log in at:")
        print(f"{BASE_URL}/auth/login/")
        print("Username: admin")
        print("Password: temppass123")
    else:
        print("FAIL: django_session table issue persists")
        print("Manual intervention may be required.")
        print("\nNext steps:")
        print("1. Check container logs in Portainer")
        print("2. Restart the web container")
        print("3. Check database permissions")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
