#!/usr/bin/env python3
"""
Check if admin user exists and fix if needed.
"""

import requests
import json

# Configuration
BASE_URL = "https://dev.maintenance.errorlog.app"

def check_and_fix_admin_user():
    """Check if admin user exists and fix if needed."""
    print("Check and Fix Admin User")
    print("=" * 50)
    print(f"Target: {BASE_URL}")
    print("=" * 50)
    
    api_url = f"{BASE_URL}/api/migrations/"
    
    # Step 1: Try to create admin user
    print("\nStep 1: Creating admin user...")
    
    try:
        create_admin_url = f"{BASE_URL}/api/create-admin/"
        payload = {
            "username": "admin",
            "email": "admin@maintenance.local",
            "password": "temppass123"
        }
        
        response = requests.post(create_admin_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("SUCCESS: Admin user created successfully")
                print(f"Username: {result.get('username')}")
                print(f"Email: {result.get('email')}")
            else:
                print(f"FAIL: Admin user creation failed: {result.get('error')}")
                if "already exists" in result.get('error', ''):
                    print("Admin user already exists, trying to reset password...")
                    return reset_admin_password()
        else:
            print(f"FAIL: Admin user creation request failed: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"FAIL: Admin user creation request failed: {e}")
        return False
    
    # Step 2: Test login with created user
    print("\nStep 2: Testing login with created user...")
    return test_login()

def reset_admin_password():
    """Reset admin user password."""
    print("\nResetting admin user password...")
    
    try:
        reset_url = f"{BASE_URL}/api/reset-admin-password/"
        payload = {
            "username": "admin",
            "new_password": "temppass123"
        }
        
        response = requests.post(reset_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("SUCCESS: Admin password reset successfully")
                print(f"Username: {result.get('username')}")
                return test_login()
            else:
                print(f"FAIL: Password reset failed: {result.get('error')}")
                return False
        else:
            print(f"FAIL: Password reset request failed: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"FAIL: Password reset request failed: {e}")
        return False

def test_login():
    """Test login functionality."""
    print("\nTesting login...")
    
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
    success = check_and_fix_admin_user()
    
    print("\n" + "=" * 50)
    print("ADMIN USER FIX SUMMARY")
    print("=" * 50)
    
    if success:
        print("SUCCESS: Admin user is working!")
        print("Login functionality should now work.")
        print("\nYou can log in at:")
        print(f"{BASE_URL}/auth/login/")
        print("Username: admin")
        print("Password: temppass123")
    else:
        print("FAIL: Admin user issue persists")
        print("Manual intervention may be required.")
        print("\nNext steps:")
        print("1. Check container logs in Portainer")
        print("2. Restart the web container")
        print("3. Check database permissions")
        print("4. Try the original password: DevAdminPassword2024!")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
