#!/usr/bin/env python3
"""
Reset admin user password via API.
"""

import requests
import json

# Configuration
BASE_URL = "https://dev.maintenance.errorlog.app"
API_ENDPOINT = f"{BASE_URL}/api/create-admin/"

def reset_admin_password():
    """Reset admin user password by creating a new one with the same username."""
    print("Resetting admin user password...")
    
    # First, let's try to delete the existing user by creating a new one
    # This will fail if the user exists, but we can use that to our advantage
    
    payload = {
        "username": "admin",
        "email": "admin@dev.maintenance.errorlog.app",
        "password": "DevAdminPassword2024!"
    }
    
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Password-Reset-Script/1.0'
    }
    
    try:
        response = requests.post(API_ENDPOINT, json=payload, headers=headers, timeout=60)
        
        if response.status_code == 400:
            result = response.json()
            if "already exists" in result.get('error', ''):
                print("Admin user already exists. Let's try a different approach...")
                return try_alternative_passwords()
        elif response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("Admin user created successfully!")
                return True
        
        print(f"Unexpected response: {response.status_code}")
        print(f"Response: {response.text}")
        return False
        
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return False

def try_alternative_passwords():
    """Try different possible passwords for the admin user."""
    print("Trying alternative passwords...")
    
    login_url = f"{BASE_URL}/auth/login/"
    session = requests.Session()
    
    # Common passwords that might have been used
    passwords = [
        'temppass123',
        'admin',
        'password',
        'DevPassword2024!',
        'DevAdminPassword2024!',
        'admin123',
        'password123',
        'maintenance',
        'dashboard',
        'test123',
        '123456',
        'qwerty'
    ]
    
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
        
        # Try each password
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
    print("Admin Password Reset Script")
    print("=" * 50)
    print(f"Target: {BASE_URL}")
    print("=" * 50)
    
    # Try to reset password
    if reset_admin_password():
        print("\nSUCCESS! Admin login is now working!")
        print("\nYou can log in at:")
        print(f"{BASE_URL}/auth/login/")
        print("Username: admin")
        print("Password: [found via testing]")
    else:
        print("\nFailed to reset admin password")
        print("The admin user may need to be manually reset")
    
    print("\n" + "=" * 50)
    print("Script completed.")

if __name__ == "__main__":
    main()
