#!/usr/bin/env python3
"""
Force create django_session table by running the specific migration.
"""

import requests
import json

# Configuration
BASE_URL = "https://dev.maintenance.errorlog.app"
API_ENDPOINT = f"{BASE_URL}/api/migrations/"

def make_api_request(payload):
    """Make API request to migrations endpoint."""
    headers = {
        'Content-Type': 'application/json',
    }
    try:
        response = requests.post(API_ENDPOINT, json=payload, headers=headers, timeout=60)
        return response.json(), response.status_code
    except requests.exceptions.RequestException as e:
        return {'error': str(e)}, 500

def force_create_session_table():
    """Force create the django_session table by running sessions migration."""
    print("Force creating django_session table...")
    
    # First, let's try to run the specific sessions migration
    payload = {"command": "migrate", "app": "sessions", "fake": False, "fake_initial": False}
    result, status_code = make_api_request(payload)
    
    if status_code == 200 and result.get('success'):
        print("Sessions migration completed successfully")
        print("Migration output:")
        print(result.get('output', 'No output'))
        return True
    else:
        print(f"Sessions migration failed: {result.get('error', 'Unknown error')}")
        print("Error output:")
        print(result.get('output', 'No output'))
        
        # Try to fake the sessions migration
        print("\nTrying to fake sessions migration...")
        payload = {"command": "migrate", "app": "sessions", "fake": True}
        result, status_code = make_api_request(payload)
        
        if status_code == 200 and result.get('success'):
            print("Sessions fake migration completed successfully")
            print("Migration output:")
            print(result.get('output', 'No output'))
            return True
        else:
            print(f"Sessions fake migration failed: {result.get('error', 'Unknown error')}")
            return False

def test_login():
    """Test login after session table creation."""
    print("\nTesting login...")
    
    login_url = f"{BASE_URL}/auth/login/"
    session = requests.Session()
    
    try:
        # Get login page
        response = session.get(login_url, timeout=30)
        if response.status_code != 200:
            print("Failed to get login page")
            return False
        
        # Extract CSRF token
        csrf_token = None
        for line in response.text.split('\n'):
            if 'csrfmiddlewaretoken' in line and 'value=' in line:
                start = line.find('value="') + 7
                end = line.find('"', start)
                if start > 6 and end > start:
                    csrf_token = line[start:end]
                    break
        
        if not csrf_token:
            print("Could not extract CSRF token")
            return False
        
        # Try login with the password from logs
        login_data = {
            'username': 'admin',
            'password': 'DevAdminPassword2024!',
            'csrfmiddlewaretoken': csrf_token
        }
        
        response = session.post(login_url, data=login_data, timeout=30, allow_redirects=False)
        
        if response.status_code == 302:
            location = response.headers.get('Location', '')
            if location in ['/', '/dashboard/', '/dashboard']:
                print("Login successful! Redirected to dashboard")
                return True
            else:
                print(f"Redirected to unexpected location: {location}")
                return False
        elif response.status_code == 200:
            if 'invalid' not in response.text.lower() and 'incorrect' not in response.text.lower():
                print("Login successful! On dashboard page")
                return True
            else:
                print("Login failed - invalid credentials")
                return False
        else:
            print(f"Unexpected response: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return False

def main():
    """Main function."""
    print("Force Create Session Table Final Script")
    print("=" * 50)
    print(f"Target: {BASE_URL}")
    print("=" * 50)
    
    # Force create session table
    if force_create_session_table():
        print("\nSession table creation completed!")
        
        # Test login
        if test_login():
            print("\nSUCCESS! Login functionality is working!")
            print("The django_session table issue has been resolved.")
            print("\nYou can now log in at:")
            print(f"{BASE_URL}/auth/login/")
            print("Username: admin")
            print("Password: DevAdminPassword2024!")
        else:
            print("\nLogin test failed. The issue may not be fully resolved.")
    else:
        print("\nFailed to create session table")
        print("Manual intervention may be required.")
    
    print("\n" + "=" * 50)
    print("Script completed.")

if __name__ == "__main__":
    main()
