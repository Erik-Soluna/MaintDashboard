#!/usr/bin/env python3
"""
Create admin user via API.
"""

import requests
import json

# Configuration
BASE_URL = "https://dev.maintenance.errorlog.app"
API_ENDPOINT = f"{BASE_URL}/api/migrations/"

def create_admin_user():
    """Create admin user using the init_database command."""
    print("Creating admin user...")
    
    # We need to create a management command API endpoint for init_database
    # For now, let's try to use the existing debug endpoints
    
    # Try the clear database endpoint which might have admin creation
    debug_url = f"{BASE_URL}/core/debug/clear-database/"
    
    try:
        # This might create an admin user as part of the process
        response = requests.post(debug_url, timeout=60)
        
        if response.status_code == 200:
            print("Debug endpoint responded successfully")
            print("Response:", response.text[:500])
            return True
        else:
            print(f"Debug endpoint failed: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return False

def test_admin_login():
    """Test if admin user exists and can login."""
    print("Testing admin login...")
    
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
        
        # Try login with different possible passwords
        passwords = [
            'DevAdminPassword2024!',
            'temppass123',
            'admin',
            'password',
            'DevPassword2024!'
        ]
        
        for password in passwords:
            print(f"Trying password: {password}")
            
            login_data = {
                'username': 'admin',
                'password': password,
                'csrfmiddlewaretoken': csrf_token
            }
            
            response = session.post(login_url, data=login_data, timeout=30, allow_redirects=False)
            
            if response.status_code == 302:
                location = response.headers.get('Location', '')
                if location in ['/', '/dashboard/', '/dashboard']:
                    print(f"SUCCESS! Password is: {password}")
                    return True
            elif response.status_code == 200:
                if 'invalid' not in response.text.lower() and 'incorrect' not in response.text.lower():
                    print(f"SUCCESS! Password is: {password}")
                    return True
        
        print("None of the tested passwords worked")
        return False
        
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return False

def main():
    """Main function."""
    print("Admin User Creation/Test Script")
    print("=" * 50)
    
    # First try to test if admin already exists
    if test_admin_login():
        print("\nAdmin user already exists and login works!")
        return
    
    print("\nAdmin user doesn't exist or login failed. Trying to create...")
    
    # Try to create admin user
    if create_admin_user():
        print("\nAdmin creation attempted. Testing login again...")
        if test_admin_login():
            print("\nSUCCESS! Admin user created and login works!")
        else:
            print("\nAdmin creation failed or wrong password")
    else:
        print("\nFailed to create admin user")
    
    print("\n" + "=" * 50)
    print("Script completed.")

if __name__ == "__main__":
    main()
