#!/usr/bin/env python3
"""
Debug form errors to see what's preventing submission.
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

def debug_form_submission(session):
    """Debug form submission to see the exact errors."""
    form_url = f"{BASE_URL}/maintenance/activities/add/"
    response = session.get(form_url)
    
    if response.status_code != 200:
        print(f"FAIL: Could not get form. Status: {response.status_code}")
        return
    
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
        print("FAIL: No CSRF token found")
        return
    
    # Get equipment and activity type
    equipment_select_match = re.search(r'<select[^>]*name="equipment"[^>]*>(.*?)</select>', response.text, re.DOTALL)
    activity_type_select_match = re.search(r'<select[^>]*name="activity_type"[^>]*>(.*?)</select>', response.text, re.DOTALL)
    
    if not equipment_select_match or not activity_type_select_match:
        print("FAIL: Could not find select fields")
        return
    
    equipment_html = equipment_select_match.group(1)
    activity_type_html = activity_type_select_match.group(1)
    
    equipment_options = re.findall(r'<option[^>]*value="([^"]+)"[^>]*>([^<]+)</option>', equipment_html)
    activity_type_options = re.findall(r'<option[^>]*value="([^"]+)"[^>]*>([^<]+)</option>', activity_type_html)
    
    equipment_id = None
    for value, text in equipment_options:
        if value and value != '':
            equipment_id = value
            break
    
    activity_type_id = None
    for value, text in activity_type_options:
        if value and value != '':
            activity_type_id = value
            break
    
    if not equipment_id or not activity_type_id:
        print(f"FAIL: Missing required fields - Equipment: {equipment_id}, Activity Type: {activity_type_id}")
        return
    
    # Calculate dates
    start_time = datetime.now() + timedelta(days=1)
    end_time = start_time + timedelta(hours=2)
    
    # Try form submission
    form_data = {
        'csrfmiddlewaretoken': csrf_token,
        'equipment': equipment_id,
        'activity_type': activity_type_id,
        'title': 'Test Activity',
        'description': 'Test description',
        'status': 'pending',
        'priority': 'medium',
        'scheduled_start': start_time.strftime('%Y-%m-%dT%H:%M'),
        'scheduled_end': end_time.strftime('%Y-%m-%dT%H:%M'),
    }
    
    headers = {
        'Referer': form_url,
        'X-CSRFToken': csrf_token,
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    
    print("Submitting form...")
    response = session.post(form_url, data=form_data, headers=headers, allow_redirects=False)
    
    print(f"Response status: {response.status_code}")
    
    if response.status_code == 200:
        print("Form returned 200 (validation errors)")
        
        # Look for error messages
        error_messages = re.findall(r'<div[^>]*class="[^"]*error[^"]*"[^>]*>([^<]+)</div>', response.text, re.IGNORECASE)
        if error_messages:
            print("Error messages found:")
            for error in error_messages:
                print(f"  - {error.strip()}")
        else:
            print("No error messages found in response")
        
        # Look for field-specific errors
        field_errors = re.findall(r'<div[^>]*class="[^"]*text-danger[^"]*"[^>]*>([^<]+)</div>', response.text, re.IGNORECASE)
        if field_errors:
            print("Field-specific errors found:")
            for error in field_errors:
                print(f"  - {error.strip()}")
        
        # Look for form validation errors
        validation_errors = re.findall(r'<ul[^>]*class="[^"]*errorlist[^"]*"[^>]*>(.*?)</ul>', response.text, re.DOTALL | re.IGNORECASE)
        if validation_errors:
            print("Validation error lists found:")
            for error_list in validation_errors:
                list_items = re.findall(r'<li[^>]*>([^<]+)</li>', error_list, re.IGNORECASE)
                for item in list_items:
                    print(f"  - {item.strip()}")
        
        # Save response to file for inspection
        with open('form_response.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("Response saved to form_response.html for inspection")
        
    elif response.status_code == 302:
        print("SUCCESS: Form submitted successfully (redirect)")
        print(f"Redirect location: {response.headers.get('Location')}")
    else:
        print(f"Unexpected response status: {response.status_code}")

def main():
    """Main function."""
    print("Debug Form Errors")
    print("=" * 50)
    print(f"Target: {BASE_URL}")
    print("=" * 50)

    session = requests.Session()
    if not login_admin(session):
        print("FAIL: Admin login failed, cannot proceed.")
        return

    debug_form_submission(session)

    print("\n" + "=" * 50)
    print("FORM ERRORS DEBUG SUMMARY")
    print("=" * 50)
    print("SUCCESS: Form errors debug completed")
    print("=" * 50)

if __name__ == "__main__":
    main()
