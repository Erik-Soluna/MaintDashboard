#!/usr/bin/env python3
"""
Debug form submission to see what's wrong with the maintenance form.
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

def debug_form(session):
    """Debug the maintenance form to see what's available."""
    form_url = f"{BASE_URL}/maintenance/activities/add/"
    response = session.get(form_url)
    
    if response.status_code != 200:
        print(f"FAIL: Could not get form. Status: {response.status_code}")
        return
    
    print("SUCCESS: Form accessible")
    
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
    
    if csrf_token:
        print(f"SUCCESS: CSRF token found: {csrf_token[:20]}...")
    else:
        print("FAIL: No CSRF token found")
    
    # Extract equipment options
    equipment_options = re.findall(r'<option[^>]*value="([^"]+)"[^>]*>([^<]+)</option>', response.text)
    print(f"\nEquipment options found: {len(equipment_options)}")
    for i, (value, text) in enumerate(equipment_options[:10]):  # Show first 10
        print(f"  {i+1}. Value: '{value}', Text: '{text.strip()}'")
    
    # Extract activity type options
    activity_type_options = re.findall(r'<option[^>]*value="([^"]+)"[^>]*>([^<]+)</option>', response.text)
    print(f"\nActivity type options found: {len(activity_type_options)}")
    for i, (value, text) in enumerate(activity_type_options[:10]):  # Show first 10
        print(f"  {i+1}. Value: '{value}', Text: '{text.strip()}'")
    
    # Look for form fields
    form_fields = re.findall(r'<input[^>]*name="([^"]+)"[^>]*>', response.text)
    print(f"\nForm input fields found: {len(form_fields)}")
    for field in form_fields:
        print(f"  - {field}")
    
    # Look for select fields
    select_fields = re.findall(r'<select[^>]*name="([^"]+)"[^>]*>', response.text)
    print(f"\nForm select fields found: {len(select_fields)}")
    for field in select_fields:
        print(f"  - {field}")
    
    # Look for textarea fields
    textarea_fields = re.findall(r'<textarea[^>]*name="([^"]+)"[^>]*>', response.text)
    print(f"\nForm textarea fields found: {len(textarea_fields)}")
    for field in textarea_fields:
        print(f"  - {field}")
    
    # Look for error messages
    if 'error' in response.text.lower():
        print("\nWARNING: Error messages found in form")
        error_messages = re.findall(r'<div[^>]*class="[^"]*error[^"]*"[^>]*>([^<]+)</div>', response.text, re.IGNORECASE)
        for error in error_messages:
            print(f"  Error: {error.strip()}")

def test_form_submission(session):
    """Test form submission with minimal data."""
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
    
    # Get first valid equipment and activity type
    equipment_options = re.findall(r'<option[^>]*value="([^"]+)"[^>]*>([^<]+)</option>', response.text)
    equipment_id = None
    for value, text in equipment_options:
        if value and value != '' and 'Dorothy' in text:
            equipment_id = value
            break
    
    activity_type_options = re.findall(r'<option[^>]*value="([^"]+)"[^>]*>([^<]+)</option>', response.text)
    activity_type_id = None
    for value, text in activity_type_options:
        if value and value != '' and ('Inspection' in text or 'Maintenance' in text):
            activity_type_id = value
            break
    
    if not equipment_id or not activity_type_id:
        print(f"FAIL: Missing required fields - Equipment: {equipment_id}, Activity Type: {activity_type_id}")
        return
    
    # Calculate dates
    start_time = datetime.now() + timedelta(days=1)
    end_time = start_time + timedelta(hours=2)
    
    # Try minimal form submission
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
    
    print(f"Submitting form with data:")
    for key, value in form_data.items():
        print(f"  {key}: {value}")
    
    response = session.post(form_url, data=form_data, headers=headers, allow_redirects=False)
    
    print(f"\nForm submission response:")
    print(f"Status: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    if response.status_code == 302:
        print("SUCCESS: Form submitted successfully (redirect)")
        print(f"Redirect location: {response.headers.get('Location')}")
    else:
        print("FAIL: Form submission failed")
        print(f"Response content (first 1000 chars): {response.text[:1000]}")
        
        # Look for error messages in the response
        if 'error' in response.text.lower():
            print("\nError messages found in response:")
            error_messages = re.findall(r'<div[^>]*class="[^"]*error[^"]*"[^>]*>([^<]+)</div>', response.text, re.IGNORECASE)
            for error in error_messages:
                print(f"  Error: {error.strip()}")

def main():
    """Main function."""
    print("Debug Form Submission")
    print("=" * 50)
    print(f"Target: {BASE_URL}")
    print("=" * 50)

    session = requests.Session()
    if not login_admin(session):
        print("FAIL: Admin login failed, cannot proceed.")
        return

    # Debug the form
    debug_form(session)
    
    # Test form submission
    print("\n" + "=" * 50)
    print("Testing form submission...")
    test_form_submission(session)

    print("\n" + "=" * 50)
    print("FORM DEBUG SUMMARY")
    print("=" * 50)
    print("SUCCESS: Form debug completed")
    print("=" * 50)

if __name__ == "__main__":
    main()
