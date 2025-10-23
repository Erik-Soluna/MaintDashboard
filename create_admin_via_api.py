#!/usr/bin/env python3
"""
Create admin user via API endpoint.
"""

import requests
import json
import time

# Configuration
BASE_URL = "https://dev.maintenance.errorlog.app"
API_ENDPOINT = f"{BASE_URL}/api/create-admin/"

def create_admin_user():
    """Create admin user via API."""
    print("Creating admin user via API...")
    
    payload = {
        "username": "admin",
        "email": "admin@dev.maintenance.errorlog.app",
        "password": "DevAdminPassword2024!"
    }
    
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Admin-Creation-Script/1.0'
    }
    
    try:
        response = requests.post(API_ENDPOINT, json=payload, headers=headers, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("Admin user created successfully!")
                print(f"Username: {result.get('username')}")
                print(f"Email: {result.get('email')}")
                return True
            else:
                print(f"Failed to create admin user: {result.get('error')}")
                return False
        else:
            print(f"API request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return False

def test_admin_login():
    """Test admin login after creation."""
    print("\nTesting admin login...")
    
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
        
        # Login
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
                print(f"Unexpected redirect: {location}")
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
    print("Admin User Creation Script")
    print("=" * 50)
    print(f"Target: {BASE_URL}")
    print("=" * 50)
    
    # Wait a moment for the server to update
    print("Waiting for server to update with new API endpoint...")
    time.sleep(10)
    
    # Create admin user
    if create_admin_user():
        print("\nAdmin user created successfully!")
        
        # Test login
        if test_admin_login():
            print("\nSUCCESS! Admin user created and login works!")
            print("\nYou can now log in at:")
            print(f"{BASE_URL}/auth/login/")
            print("Username: admin")
            print("Password: DevAdminPassword2024!")
        else:
            print("\nAdmin user created but login test failed")
    else:
        print("\nFailed to create admin user")
    
    print("\n" + "=" * 50)
    print("Script completed.")

if __name__ == "__main__":
    main()
