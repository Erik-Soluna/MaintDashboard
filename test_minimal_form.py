#!/usr/bin/env python3
"""
Test minimal form submission to isolate the issue.
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

def test_minimal_submission(session):
    """Test with minimal required fields only."""
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
    
    # Calculate dates with proper time difference
    start_time = datetime.now() + timedelta(days=1, hours=1)
    end_time = start_time + timedelta(hours=2)
    
    # Try with minimal required fields only
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
    
    print("Testing minimal form submission...")
    print(f"Start time: {start_time.strftime('%Y-%m-%dT%H:%M')}")
    print(f"End time: {end_time.strftime('%Y-%m-%dT%H:%M')}")
    
    response = session.post(form_url, data=form_data, headers=headers, allow_redirects=False)
    
    print(f"Response status: {response.status_code}")
    
    if response.status_code == 302:
        print("SUCCESS: Form submitted successfully!")
        print(f"Redirect location: {response.headers.get('Location')}")
        return True
    else:
        print("FAIL: Form submission failed")
        
        # Look for specific error patterns
        if 'time' in response.text.lower() and 'validation' in response.text.lower():
            print("Time validation error detected")
        
        # Save response for debugging
        with open('minimal_form_response.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("Response saved to minimal_form_response.html")
        
        return False

def main():
    """Main function."""
    print("Test Minimal Form Submission")
    print("=" * 50)
    print(f"Target: {BASE_URL}")
    print("=" * 50)

    session = requests.Session()
    if not login_admin(session):
        print("FAIL: Admin login failed, cannot proceed.")
        return

    success = test_minimal_submission(session)
    
    if success:
        print("\nSUCCESS: Maintenance activity created!")
        print("Now check the dashboard to see if it appears in urgent/upcoming sections.")
    else:
        print("\nFAIL: Could not create maintenance activity.")
        print("Check minimal_form_response.html for error details.")

    print("\n" + "=" * 50)
    print("MINIMAL FORM TEST SUMMARY")
    print("=" * 50)
    print("SUCCESS: Minimal form test completed")
    print("=" * 50)

if __name__ == "__main__":
    main()
