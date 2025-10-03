#!/usr/bin/env python3
"""
Create test maintenance activities via API.
"""

import requests
import json

# Configuration
BASE_URL = "https://dev.maintenance.errorlog.app"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "temppass123"

def login_admin(session):
    """Login as admin user."""
    login_url = f"{BASE_URL}/auth/login/"
    response = session.get(login_url)
    if response.status_code != 200:
        print(f"FAIL: Could not get login page. Status: {response.status_code}")
        return False

    csrf_token = session.cookies.get('csrftoken')
    if not csrf_token:
        print("FAIL: CSRF token not found in login page.")
        return False

    login_data = {
        'username': ADMIN_USERNAME,
        'password': ADMIN_PASSWORD,
        'csrfmiddlewaretoken': csrf_token,
    }
    headers = {
        'Referer': login_url,
        'X-CSRFToken': csrf_token,
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    response = session.post(login_url, data=login_data, headers=headers, allow_redirects=False)

    if response.status_code == 302 and response.headers.get('Location') == '/':
        print("SUCCESS: Logged in successfully")
        return True
    else:
        print(f"FAIL: Login failed. Status: {response.status_code}")
        return False

def create_test_maintenance(session):
    """Create test maintenance activities via API."""
    api_url = f"{BASE_URL}/api/migrations/"
    payload = {"command": "create_test_maintenance", "force": True}
    headers = {
        'X-CSRFToken': session.cookies.get('csrftoken'),
        'Referer': BASE_URL,
        'Content-Type': 'application/json',
    }
    print("Creating test maintenance activities...")
    response = session.post(api_url, json=payload, headers=headers)
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            print("SUCCESS: Test maintenance activities created")
            print(f"Output: {result.get('output', '')}")
            return True
        else:
            print(f"FAIL: API error: {result.get('error')}")
            print(f"Output: {result.get('output', '')}")
            return False
    else:
        print(f"FAIL: API returned status {response.status_code}")
        print(f"Response: {response.text[:500]}")
        return False

def main():
    """Main function."""
    print("Create Test Maintenance Activities")
    print("=" * 50)
    print(f"Target: {BASE_URL}")
    print("=" * 50)

    session = requests.Session()
    if not login_admin(session):
        print("FAIL: Admin login failed, cannot proceed.")
        return

    if not create_test_maintenance(session):
        print("FAIL: Could not create test maintenance activities.")
        return

    print("\n" + "=" * 50)
    print("TEST MAINTENANCE ACTIVITIES SUMMARY")
    print("=" * 50)
    print("SUCCESS: Test maintenance activities have been created!")
    print("\nCreated activities:")
    print("- 3 urgent activities (due within 7 days)")
    print("- 3 upcoming activities (due within 30 days)")
    print("\nCheck the dashboard to see if they appear in the urgent and upcoming sections.")
    print("=" * 50)

if __name__ == "__main__":
    main()