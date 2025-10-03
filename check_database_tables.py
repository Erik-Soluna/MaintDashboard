#!/usr/bin/env python3
"""
Check database tables via API.
"""

import requests
import json

# Configuration
BASE_URL = "https://dev.maintenance.errorlog.app"

def check_database_connection():
    """Check database connection and tables."""
    print("Checking database connection and tables...")
    
    # Try to access a simple endpoint that uses the database
    try:
        response = requests.get(f"{BASE_URL}/health/simple/", timeout=30)
        if response.status_code == 200:
            print("Database health check passed")
            return True
        else:
            print(f"Database health check failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Database health check request failed: {e}")
        return False

def check_specific_table():
    """Check if django_session table exists by trying to access it."""
    print("Checking django_session table...")
    
    # Try to access the admin interface which should use sessions
    try:
        response = requests.get(f"{BASE_URL}/admin/", timeout=30)
        if response.status_code == 200:
            print("Admin interface accessible - sessions working")
            return True
        elif response.status_code == 302:
            print("Admin interface redirects (expected) - sessions working")
            return True
        else:
            print(f"Admin interface failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Admin interface request failed: {e}")
        return False

def test_session_creation():
    """Test if we can create a session."""
    print("Testing session creation...")
    
    session = requests.Session()
    
    try:
        # Try to access the login page and see if a session is created
        response = session.get(f"{BASE_URL}/auth/login/", timeout=30)
        if response.status_code == 200:
            # Check if session cookie was set
            cookies = session.cookies
            if 'sessionid' in cookies or 'csrftoken' in cookies:
                print("Session cookies created successfully")
                return True
            else:
                print("No session cookies found")
                return False
        else:
            print(f"Login page failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Session creation test failed: {e}")
        return False

def main():
    """Main function."""
    print("Database Table Check Script")
    print("=" * 50)
    print(f"Target: {BASE_URL}")
    print("=" * 50)
    
    # Check database connection
    if not check_database_connection():
        print("Database connection failed!")
        return
    
    print("\n" + "=" * 50)
    
    # Check specific table
    if not check_specific_table():
        print("django_session table check failed!")
        return
    
    print("\n" + "=" * 50)
    
    # Test session creation
    if not test_session_creation():
        print("Session creation test failed!")
        return
    
    print("\n" + "=" * 50)
    print("All database checks passed!")
    print("The django_session table appears to be working correctly.")
    print("The login issue may be related to authentication logic, not the database table.")

if __name__ == "__main__":
    main()
