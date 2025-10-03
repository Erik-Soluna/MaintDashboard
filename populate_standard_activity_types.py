#!/usr/bin/env python3
"""
Populate standard activity types via API.
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
        print(f"Response content: {response.text[:500]}")
        return False

def populate_standard_activity_types(session):
    """Populate standard activity types via API."""
    api_url = f"{BASE_URL}/api/migrations/"
    payload = {"command": "populate_standard_activity_types", "force": True}
    headers = {
        'X-CSRFToken': session.cookies.get('csrftoken'),
        'Referer': BASE_URL,
        'Content-Type': 'application/json',
    }
    print("Attempting to populate standard activity types...")
    response = session.post(api_url, json=payload, headers=headers)
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            print("SUCCESS: Standard activity types populated successfully")
            print(f"Output: {result.get('output', '')[:500]}...")
            return True
        else:
            print(f"FAIL: API error: {result.get('error')}")
            print(f"Output: {result.get('output', '')[:500]}...")
            return False
    else:
        print(f"FAIL: API returned status {response.status_code}")
        print(f"Response: {response.text[:500]}")
        return False

def main():
    """Main function."""
    print("Populate Standard Activity Types")
    print("=" * 50)
    print(f"Target: {BASE_URL}")
    print("=" * 50)

    session = requests.Session()
    if not login_admin(session):
        print("FAIL: Admin login failed, cannot proceed.")
        return

    if not populate_standard_activity_types(session):
        print("FAIL: Could not populate standard activity types via API.")
        print("You may need to run this command manually in the Django shell.")
        return

    print("\n" + "=" * 50)
    print("STANDARD ACTIVITY TYPES POPULATION SUMMARY")
    print("=" * 50)
    print("SUCCESS: Standard activity types have been populated!")
    print("\nThe following categories and activity types are now available:")
    print("- Inspection: Routine Inspection, Safety Inspection, Thermal Inspection")
    print("- Preventive Maintenance: Oil Analysis, Filter Replacement, Lubrication")
    print("- Emergency Maintenance: Emergency Repair, Component Replacement, System Restoration")
    print("- Testing: Load Testing, Performance Testing, Insulation Testing")
    print("- Calibration: Instrument Calibration, System Calibration")
    print("- Cleaning: Equipment Cleaning, Area Cleaning")
    print("\nYou can now use these in the maintenance activity form!")
    print("=" * 50)

if __name__ == "__main__":
    main()
