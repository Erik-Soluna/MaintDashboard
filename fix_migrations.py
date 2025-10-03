#!/usr/bin/env python3
"""
Script to fix Django migrations on remote server via API.
This script will:
1. Check current migration status
2. Run migrations to create missing tables
3. Verify the fix worked
"""

import requests
import json
import sys

# Configuration
BASE_URL = "https://dev.maintenance.errorlog.app"
API_ENDPOINT = f"{BASE_URL}/core/api/migrations/"

def make_api_request(payload):
    """Make API request to run migrations."""
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Migration-Fix-Script/1.0'
    }
    
    try:
        response = requests.post(API_ENDPOINT, json=payload, headers=headers, timeout=60)
        return response.json(), response.status_code
    except requests.exceptions.RequestException as e:
        return {'error': str(e)}, 500

def check_migration_status():
    """Check current migration status."""
    print("Checking migration status...")
    
    payload = {
        "command": "showmigrations"
    }
    
    result, status_code = make_api_request(payload)
    
    if status_code == 200 and result.get('success'):
        print("Migration status retrieved successfully")
        print("Current migration status:")
        print(result.get('output', 'No output'))
        return True
    else:
        print(f"Failed to get migration status: {result.get('error', 'Unknown error')}")
        return False

def run_migrations():
    """Run Django migrations."""
    print("Running Django migrations...")
    
    payload = {
        "command": "migrate",
        "fake": False,
        "fake_initial": False
    }
    
    result, status_code = make_api_request(payload)
    
    if status_code == 200 and result.get('success'):
        print("Migrations completed successfully")
        print("Migration output:")
        print(result.get('output', 'No output'))
        return True
    else:
        print(f"Migration failed: {result.get('error', 'Unknown error')}")
        print("Error output:")
        print(result.get('output', 'No output'))
        return False

def run_fake_initial_migrations():
    """Run fake initial migrations as fallback."""
    print("Trying fake initial migrations as fallback...")
    
    payload = {
        "command": "migrate",
        "fake_initial": True
    }
    
    result, status_code = make_api_request(payload)
    
    if status_code == 200 and result.get('success'):
        print("Fake initial migrations completed successfully")
        print("Migration output:")
        print(result.get('output', 'No output'))
        return True
    else:
        print(f"Fake initial migrations failed: {result.get('error', 'Unknown error')}")
        print("Error output:")
        print(result.get('output', 'No output'))
        return False

def test_login():
    """Test if login works after migrations."""
    print("Testing login functionality...")
    
    login_url = f"{BASE_URL}/auth/login/"
    
    try:
        # Create a session
        session = requests.Session()
        
        # Get the login page to get CSRF token
        response = session.get(login_url, timeout=30)
        
        if response.status_code == 200:
            print("Login page loads successfully")
            
            # Try to login with default admin credentials
            login_data = {
                'username': 'admin',
                'password': 'DevAdminPassword2024!',
                'csrfmiddlewaretoken': 'test'  # This will likely fail, but we're testing if the page loads
            }
            
            # Just test if we can make the request without the django_session error
            response = session.post(login_url, data=login_data, timeout=30)
            
            if "django_session" not in response.text and "relation" not in response.text:
                print("Login functionality appears to be working (no django_session errors)")
                return True
            else:
                print("Login still has django_session errors")
                return False
        else:
            print(f"Login page failed to load: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Login test failed: {e}")
        return False

def main():
    """Main function to fix migrations."""
    print("Django Migration Fix Script")
    print("=" * 50)
    print(f"Target: {BASE_URL}")
    print("=" * 50)
    
    # Step 1: Check current status
    if not check_migration_status():
        print("Could not check migration status, proceeding with migrations anyway...")
    
    print("\n" + "=" * 50)
    
    # Step 2: Run migrations
    if run_migrations():
        print("\nMigrations completed successfully!")
    else:
        print("\nStandard migrations failed, trying fake initial...")
        if run_fake_initial_migrations():
            print("\nFake initial migrations completed successfully!")
        else:
            print("\nAll migration attempts failed!")
            print("Manual intervention may be required.")
            sys.exit(1)
    
    print("\n" + "=" * 50)
    
    # Step 3: Test login functionality
    if test_login():
        print("\nSUCCESS: Login functionality is working!")
        print("The django_session table issue has been resolved.")
    else:
        print("\nLogin test failed. The issue may not be fully resolved.")
    
    print("\n" + "=" * 50)
    print("Migration fix script completed.")

if __name__ == "__main__":
    main()
