#!/usr/bin/env python3
"""
Test login with the correct password.
"""

import requests

# Configuration
BASE_URL = "https://dev.maintenance.errorlog.app"
LOGIN_URL = f"{BASE_URL}/auth/login/"

def test_login():
    """Test login with correct password."""
    print("Testing login with correct password...")
    print(f"Target: {BASE_URL}")
    print("=" * 50)
    
    # Create a session
    session = requests.Session()
    
    try:
        # Step 1: Get the login page to get CSRF token
        print("Step 1: Getting login page...")
        response = session.get(LOGIN_URL, timeout=30)
        
        if response.status_code != 200:
            print(f"Failed to get login page: {response.status_code}")
            return False
            
        print("Login page loaded successfully")
        
        # Extract CSRF token from the response
        csrf_token = None
        for line in response.text.split('\n'):
            if 'csrfmiddlewaretoken' in line and 'value=' in line:
                # Extract token from: <input type="hidden" name="csrfmiddlewaretoken" value="...">
                start = line.find('value="') + 7
                end = line.find('"', start)
                if start > 6 and end > start:
                    csrf_token = line[start:end]
                    break
        
        if not csrf_token:
            print("Could not extract CSRF token")
            return False
            
        print(f"CSRF token extracted: {csrf_token[:20]}...")
        
        # Step 2: Attempt login with correct password
        print("\nStep 2: Attempting login with correct password...")
        login_data = {
            'username': 'admin',
            'password': 'temppass123',  # Correct password
            'csrfmiddlewaretoken': csrf_token
        }
        
        response = session.post(LOGIN_URL, data=login_data, timeout=30, allow_redirects=False)
        
        print(f"Login response status: {response.status_code}")
        
        if response.status_code == 302:
            # Check if we're redirected to the dashboard (successful login)
            location = response.headers.get('Location', '')
            if location in ['/', '/dashboard/', '/dashboard']:
                print("Login successful! Redirected to dashboard")
                return True
            else:
                print(f"Redirected to unexpected location: {location}")
                return False
        elif response.status_code == 200:
            # Check if we're still on the login page (failed login)
            if 'login' in response.text.lower() and 'username' in response.text.lower():
                print("Login failed - still on login page")
                # Check for error messages
                if 'invalid' in response.text.lower() or 'incorrect' in response.text.lower():
                    print("   -> Invalid username or password")
                return False
            else:
                print("Login successful! On dashboard page")
                return True
        else:
            print(f"Unexpected response: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return False

def test_dashboard_access():
    """Test if we can access the dashboard after login."""
    print("\nStep 3: Testing dashboard access...")
    
    session = requests.Session()
    
    try:
        # First login
        response = session.get(LOGIN_URL, timeout=30)
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
        
        # Login with correct password
        login_data = {
            'username': 'admin',
            'password': 'temppass123',
            'csrfmiddlewaretoken': csrf_token
        }
        
        response = session.post(LOGIN_URL, data=login_data, timeout=30, allow_redirects=True)
        
        # Try to access dashboard
        dashboard_url = f"{BASE_URL}/dashboard/"
        response = session.get(dashboard_url, timeout=30)
        
        if response.status_code == 200:
            if 'dashboard' in response.text.lower() or 'maintenance' in response.text.lower():
                print("Dashboard access successful!")
                return True
            else:
                print("Dashboard page doesn't contain expected content")
                return False
        else:
            print(f"Dashboard access failed: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Dashboard test failed: {e}")
        return False

def main():
    """Main function to test login."""
    print("Correct Login Test Script")
    print("=" * 50)
    
    # Test login
    if test_login():
        print("\nLOGIN SUCCESS!")
        
        # Test dashboard access
        if test_dashboard_access():
            print("\nDASHBOARD ACCESS SUCCESS!")
            print("Full login functionality is working!")
            print("\nYou can now log in at:")
            print(f"{BASE_URL}/auth/login/")
            print("Username: admin")
            print("Password: temppass123")
        else:
            print("\nLogin worked but dashboard access failed")
    else:
        print("\nLOGIN FAILED!")
        print("Check credentials or server status")
    
    print("\n" + "=" * 50)
    print("Login test completed.")

if __name__ == "__main__":
    main()
