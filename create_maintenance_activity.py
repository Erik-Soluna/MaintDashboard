#!/usr/bin/env python3
"""
Create a maintenance activity with the correct field values.
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

def create_maintenance_activity(session, title, description, status, priority, days_from_now, hours_duration=2):
    """Create a maintenance activity."""
    form_url = f"{BASE_URL}/maintenance/activities/add/"
    response = session.get(form_url)
    
    if response.status_code != 200:
        print(f"FAIL: Could not get form. Status: {response.status_code}")
        return False
    
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
        print("FAIL: Could not extract CSRF token from form")
        return False
    
    # Get first equipment option (skip empty option)
    equipment_select_match = re.search(r'<select[^>]*name="equipment"[^>]*>(.*?)</select>', response.text, re.DOTALL)
    if not equipment_select_match:
        print("FAIL: Equipment select field not found")
        return False
    
    equipment_html = equipment_select_match.group(1)
    equipment_options = re.findall(r'<option[^>]*value="([^"]+)"[^>]*>([^<]+)</option>', equipment_html)
    
    equipment_id = None
    equipment_name = None
    for value, text in equipment_options:
        if value and value != '':
            equipment_id = value
            equipment_name = text.strip()
            break
    
    if not equipment_id:
        print("FAIL: No valid equipment found")
        return False
    
    # Get first activity type option (skip empty option)
    activity_type_select_match = re.search(r'<select[^>]*name="activity_type"[^>]*>(.*?)</select>', response.text, re.DOTALL)
    if not activity_type_select_match:
        print("FAIL: Activity type select field not found")
        return False
    
    activity_type_html = activity_type_select_match.group(1)
    activity_type_options = re.findall(r'<option[^>]*value="([^"]+)"[^>]*>([^<]+)</option>', activity_type_html)
    
    activity_type_id = None
    activity_type_name = None
    for value, text in activity_type_options:
        if value and value != '':
            activity_type_id = value
            activity_type_name = text.strip()
            break
    
    if not activity_type_id:
        print("FAIL: No valid activity type found")
        return False
    
    # Calculate dates
    start_time = datetime.now() + timedelta(days=days_from_now)
    end_time = start_time + timedelta(hours=hours_duration)
    
    form_data = {
        'csrfmiddlewaretoken': csrf_token,
        'equipment': equipment_id,
        'activity_type': activity_type_id,
        'title': title,
        'description': description,
        'status': status,
        'priority': priority,
        'scheduled_start': start_time.strftime('%Y-%m-%dT%H:%M'),
        'scheduled_end': end_time.strftime('%Y-%m-%dT%H:%M'),
    }
    
    headers = {
        'Referer': form_url,
        'X-CSRFToken': csrf_token,
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    
    print(f"Creating: {title}")
    print(f"  Equipment: {equipment_name} (ID: {equipment_id})")
    print(f"  Activity Type: {activity_type_name} (ID: {activity_type_id})")
    print(f"  Status: {status}, Priority: {priority}")
    print(f"  Due: {start_time.strftime('%Y-%m-%d %H:%M')}")
    
    response = session.post(form_url, data=form_data, headers=headers, allow_redirects=False)
    
    if response.status_code == 302:
        print(f"SUCCESS: Created '{title}'")
        return True
    else:
        print(f"FAIL: Could not create '{title}'. Status: {response.status_code}")
        
        # Look for error messages
        if 'error' in response.text.lower():
            error_messages = re.findall(r'<div[^>]*class="[^"]*error[^"]*"[^>]*>([^<]+)</div>', response.text, re.IGNORECASE)
            for error in error_messages:
                print(f"  Error: {error.strip()}")
        
        return False

def main():
    """Main function."""
    print("Create Maintenance Activities")
    print("=" * 50)
    print(f"Target: {BASE_URL}")
    print("=" * 50)

    session = requests.Session()
    if not login_admin(session):
        print("FAIL: Admin login failed, cannot proceed.")
        return

    # Create urgent maintenance activities (due within 7 days)
    print("\nCreating urgent maintenance activities...")
    create_maintenance_activity(
        session, 
        "Urgent Transformer Inspection", 
        "Urgent inspection required for transformer maintenance", 
        "pending", 
        "high", 
        2  # Due in 2 days
    )
    
    create_maintenance_activity(
        session, 
        "Emergency Oil Analysis", 
        "Emergency oil analysis for equipment failure investigation", 
        "in_progress", 
        "high", 
        1  # Due in 1 day
    )
    
    create_maintenance_activity(
        session, 
        "Overdue Safety Check", 
        "Overdue safety inspection that needs immediate attention", 
        "overdue", 
        "high", 
        -1  # Overdue by 1 day
    )

    # Create upcoming maintenance activities (due within 30 days)
    print("\nCreating upcoming maintenance activities...")
    create_maintenance_activity(
        session, 
        "Scheduled Filter Replacement", 
        "Regular filter replacement as per maintenance schedule", 
        "scheduled", 
        "medium", 
        14  # Due in 14 days
    )
    
    create_maintenance_activity(
        session, 
        "Monthly Equipment Cleaning", 
        "Monthly cleaning and maintenance of equipment", 
        "pending", 
        "low", 
        21  # Due in 21 days
    )
    
    create_maintenance_activity(
        session, 
        "Quarterly Calibration", 
        "Quarterly calibration of measurement instruments", 
        "scheduled", 
        "medium", 
        28  # Due in 28 days
    )

    print("\n" + "=" * 50)
    print("MAINTENANCE ACTIVITIES CREATION SUMMARY")
    print("=" * 50)
    print("SUCCESS: Maintenance activities creation completed!")
    print("\nCreated activities:")
    print("- 3 urgent activities (due within 7 days)")
    print("- 3 upcoming activities (due within 30 days)")
    print("\nCheck the dashboard to see if they appear in the urgent and upcoming sections.")
    print("=" * 50)

if __name__ == "__main__":
    main()
