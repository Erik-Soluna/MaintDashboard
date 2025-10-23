#!/usr/bin/env python3
"""
Debug dashboard activities to see why upcoming and urgent activities aren't showing.
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

def check_maintenance_activities(session):
    """Check what maintenance activities exist in the database."""
    print("\nChecking maintenance activities...")
    
    # Check maintenance activities list
    maintenance_url = f"{BASE_URL}/maintenance/activities/"
    response = session.get(maintenance_url)
    
    if response.status_code == 200:
        print("SUCCESS: Maintenance activities page accessible")
        
        # Look for maintenance activities in the HTML
        if 'maintenance-item' in response.text or 'activity-item' in response.text:
            print("SUCCESS: Found maintenance activities in the list")
            
            # Count maintenance items
            import re
            maintenance_items = re.findall(r'<div[^>]*class="[^"]*maintenance-item[^"]*"[^>]*>', response.text)
            if maintenance_items:
                print(f"SUCCESS: Found {len(maintenance_items)} maintenance activities")
            else:
                print("WARNING: No maintenance items found in the list")
        else:
            print("WARNING: No maintenance activities found in the list")
            
        # Check for "No activities" message
        if 'no activities' in response.text.lower() or 'no maintenance' in response.text.lower():
            print("WARNING: Page shows 'no activities' message")
            
    else:
        print(f"FAIL: Maintenance activities page not accessible. Status: {response.status_code}")

def check_dashboard_data(session):
    """Check the dashboard data directly."""
    print("\nChecking dashboard data...")
    
    dashboard_url = f"{BASE_URL}/"
    response = session.get(dashboard_url)
    
    if response.status_code == 200:
        print("SUCCESS: Dashboard accessible")
        
        # Check for urgent items section
        if 'urgent-section' in response.text:
            print("SUCCESS: Urgent section found in dashboard")
            
            # Check for urgent maintenance items
            if 'urgent-maintenance' in response.text or 'maintenance-item urgent' in response.text:
                print("SUCCESS: Urgent maintenance items found")
            else:
                print("WARNING: No urgent maintenance items found")
                
            # Check for "No urgent items" message
            if 'no urgent items' in response.text.lower():
                print("WARNING: Dashboard shows 'no urgent items' message")
        else:
            print("WARNING: Urgent section not found in dashboard")
            
        # Check for upcoming items section
        if 'upcoming-section' in response.text:
            print("SUCCESS: Upcoming section found in dashboard")
            
            # Check for upcoming maintenance items
            if 'upcoming-maintenance' in response.text or 'maintenance-item scheduled' in response.text:
                print("SUCCESS: Upcoming maintenance items found")
            else:
                print("WARNING: No upcoming maintenance items found")
                
            # Check for "No upcoming items" message
            if 'no upcoming items' in response.text.lower():
                print("WARNING: Dashboard shows 'no upcoming items' message")
        else:
            print("WARNING: Upcoming section not found in dashboard")
            
        # Check for debug information
        if 'debug' in response.text.lower():
            print("SUCCESS: Debug information found in dashboard")
            
    else:
        print(f"FAIL: Dashboard not accessible. Status: {response.status_code}")

def check_maintenance_form(session):
    """Check if we can access the maintenance form to create test data."""
    print("\nChecking maintenance form...")
    
    form_url = f"{BASE_URL}/maintenance/activities/add/"
    response = session.get(form_url)
    
    if response.status_code == 200:
        print("SUCCESS: Maintenance form accessible")
        
        # Check for activity type dropdown
        if 'activity_type' in response.text:
            print("SUCCESS: Activity type field found")
            
            # Check for activity type options
            if 'option' in response.text and 'value=' in response.text:
                print("SUCCESS: Activity type options found")
            else:
                print("WARNING: No activity type options found")
        else:
            print("WARNING: Activity type field not found")
            
        # Check for equipment dropdown
        if 'equipment' in response.text:
            print("SUCCESS: Equipment field found")
        else:
            print("WARNING: Equipment field not found")
            
    else:
        print(f"FAIL: Maintenance form not accessible. Status: {response.status_code}")

def create_test_maintenance_activity(session):
    """Create a test maintenance activity to see if it shows up on the dashboard."""
    print("\nCreating test maintenance activity...")
    
    # First get the form
    form_url = f"{BASE_URL}/maintenance/activities/add/"
    response = session.get(form_url)
    
    if response.status_code != 200:
        print(f"FAIL: Could not get maintenance form. Status: {response.status_code}")
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
    
    # Extract equipment options
    equipment_options = re.findall(r'<option[^>]*value="([^"]+)"[^>]*>([^<]+)</option>', response.text)
    if not equipment_options:
        print("WARNING: No equipment options found")
        return False
    
    # Get first equipment option (skip empty option)
    equipment_id = None
    for value, text in equipment_options:
        if value and value != '':
            equipment_id = value
            print(f"Using equipment: {text} (ID: {value})")
            break
    
    if not equipment_id:
        print("FAIL: No valid equipment found")
        return False
    
    # Extract activity type options
    activity_type_options = re.findall(r'<option[^>]*value="([^"]+)"[^>]*>([^<]+)</option>', response.text)
    if not activity_type_options:
        print("WARNING: No activity type options found")
        return False
    
    # Get first activity type option (skip empty option)
    activity_type_id = None
    for value, text in activity_type_options:
        if value and value != '':
            activity_type_id = value
            print(f"Using activity type: {text} (ID: {value})")
            break
    
    if not activity_type_id:
        print("FAIL: No valid activity type found")
        return False
    
    # Create test maintenance activity
    from datetime import datetime, timedelta
    tomorrow = datetime.now() + timedelta(days=1)
    next_week = datetime.now() + timedelta(days=7)
    
    form_data = {
        'csrfmiddlewaretoken': csrf_token,
        'equipment': equipment_id,
        'activity_type': activity_type_id,
        'title': 'Test Maintenance Activity',
        'description': 'This is a test maintenance activity created for debugging',
        'status': 'pending',
        'priority': 'medium',
        'scheduled_start': tomorrow.strftime('%Y-%m-%dT%H:%M'),
        'scheduled_end': next_week.strftime('%Y-%m-%dT%H:%M'),
    }
    
    headers = {
        'Referer': form_url,
        'X-CSRFToken': csrf_token,
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    
    response = session.post(form_url, data=form_data, headers=headers, allow_redirects=False)
    
    if response.status_code == 302:
        print("SUCCESS: Test maintenance activity created")
        return True
    else:
        print(f"FAIL: Could not create test maintenance activity. Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        return False

def main():
    """Main function."""
    print("Debug Dashboard Activities")
    print("=" * 50)
    print(f"Target: {BASE_URL}")
    print("=" * 50)

    session = requests.Session()
    if not login_admin(session):
        print("FAIL: Admin login failed, cannot proceed.")
        return

    # Check existing maintenance activities
    check_maintenance_activities(session)
    
    # Check dashboard data
    check_dashboard_data(session)
    
    # Check maintenance form
    check_maintenance_form(session)
    
    # Try to create a test maintenance activity
    if create_test_maintenance_activity(session):
        print("\nTest activity created. Checking dashboard again...")
        check_dashboard_data(session)

    print("\n" + "=" * 50)
    print("DASHBOARD ACTIVITIES DEBUG SUMMARY")
    print("=" * 50)
    print("SUCCESS: Debug completed")
    print("\nFindings:")
    print("- Checked maintenance activities list")
    print("- Checked dashboard urgent and upcoming sections")
    print("- Checked maintenance form accessibility")
    print("- Attempted to create test maintenance activity")
    print("\nNext steps:")
    print("1. Review the findings above")
    print("2. Check if maintenance activities exist in the database")
    print("3. Verify the dashboard queries are working correctly")
    print("4. Check if the issue is with date filtering or status filtering")
    print("=" * 50)

if __name__ == "__main__":
    main()
