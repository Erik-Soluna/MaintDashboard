#!/usr/bin/env python3
"""
Test form fields to see what's actually being rendered.
"""

import requests
import json
from datetime import datetime, timedelta

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

def analyze_form_fields(session):
    """Analyze the form fields to understand the issue."""
    form_url = f"{BASE_URL}/maintenance/activities/add/"
    response = session.get(form_url)
    
    if response.status_code != 200:
        print(f"FAIL: Could not get form. Status: {response.status_code}")
        return
    
    print("SUCCESS: Form accessible")
    
    import re
    
    # Look for the equipment select field specifically
    equipment_select_match = re.search(r'<select[^>]*name="equipment"[^>]*>(.*?)</select>', response.text, re.DOTALL)
    if equipment_select_match:
        equipment_html = equipment_select_match.group(1)
        print("\nEquipment select field HTML:")
        print(equipment_html[:500] + "..." if len(equipment_html) > 500 else equipment_html)
        
        # Extract equipment options
        equipment_options = re.findall(r'<option[^>]*value="([^"]+)"[^>]*>([^<]+)</option>', equipment_html)
        print(f"\nEquipment options ({len(equipment_options)}):")
        for i, (value, text) in enumerate(equipment_options[:10]):
            print(f"  {i+1}. Value: '{value}', Text: '{text.strip()}'")
    else:
        print("FAIL: Equipment select field not found")
    
    # Look for the activity_type select field specifically
    activity_type_select_match = re.search(r'<select[^>]*name="activity_type"[^>]*>(.*?)</select>', response.text, re.DOTALL)
    if activity_type_select_match:
        activity_type_html = activity_type_select_match.group(1)
        print("\nActivity Type select field HTML:")
        print(activity_type_html[:500] + "..." if len(activity_type_html) > 500 else activity_type_html)
        
        # Extract activity type options
        activity_type_options = re.findall(r'<option[^>]*value="([^"]+)"[^>]*>([^<]+)</option>', activity_type_html)
        print(f"\nActivity Type options ({len(activity_type_options)}):")
        for i, (value, text) in enumerate(activity_type_options[:10]):
            print(f"  {i+1}. Value: '{value}', Text: '{text.strip()}'")
    else:
        print("FAIL: Activity Type select field not found")

def main():
    """Main function."""
    print("Test Form Fields")
    print("=" * 50)
    print(f"Target: {BASE_URL}")
    print("=" * 50)

    session = requests.Session()
    if not login_admin(session):
        print("FAIL: Admin login failed, cannot proceed.")
        return

    analyze_form_fields(session)

    print("\n" + "=" * 50)
    print("FORM FIELDS TEST SUMMARY")
    print("=" * 50)
    print("SUCCESS: Form fields analysis completed")
    print("=" * 50)

if __name__ == "__main__":
    main()
