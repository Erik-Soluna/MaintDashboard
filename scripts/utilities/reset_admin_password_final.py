#!/usr/bin/env python3
"""
Reset admin password using the API endpoint.
"""

import requests
import json

# Configuration
BASE_URL = "https://dev.maintenance.errorlog.app"
API_ENDPOINT = f"{BASE_URL}/api/reset-admin-password/"

def reset_admin_password():
    """Reset admin password via API."""
    print("Resetting admin password...")
    
    payload = {
        "username": "admin",
        "new_password": "temppass123"
    }
    
    headers = {
        'Content-Type': 'application/json',
    }
    
    try:
        response = requests.post(API_ENDPOINT, json=payload, headers=headers, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("Admin password reset successfully!")
                print(f"Username: {result.get('username')}")
                return True
            else:
                print(f"Failed to reset password: {result.get('error')}")
                return False
        else:
            print(f"API request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return False

def test_login_with_new_password():
    """Test login with the new password."""
    print("\nTesting login with new password...")
    
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
        
        # Try login with new password
        login_data = {
            'username': 'admin',
            'password': 'temppass123',
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
    print("Reset Admin Password Script")
    print("=" * 50)
    print(f"Target: {BASE_URL}")
    print("=" * 50)
    
    # Reset admin password
    if reset_admin_password():
        print("\nPassword reset successful!")
        
        # Test login
        if test_login_with_new_password():
            print("\nSUCCESS! Login functionality is working!")
            print("\nYou can now log in at:")
            print(f"{BASE_URL}/auth/login/")
            print("Username: admin")
            print("Password: temppass123")
        else:
            print("\nLogin test failed with new password.")
    else:
        print("\nFailed to reset admin password.")
    
    print("\n" + "=" * 50)
    print("Script completed.")

if __name__ == "__main__":
    main()
