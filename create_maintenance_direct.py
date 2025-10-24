#!/usr/bin/env python3
"""
Create maintenance activities directly via Django shell command.
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

def create_maintenance_via_shell(session):
    """Create maintenance activities via Django shell command."""
    api_url = f"{BASE_URL}/api/migrations/"
    
    # Create a Python script to run in Django shell
    script_content = '''
from maintenance.models import MaintenanceActivity
from equipment.models import Equipment
from maintenance.models import MaintenanceActivityType
from django.contrib.auth.models import User
from datetime import datetime, timedelta

# Get equipment and activity type
equipment = Equipment.objects.filter(is_active=True).first()
activity_type = MaintenanceActivityType.objects.filter(is_active=True).first()
admin_user = User.objects.get(username='admin')

if equipment and activity_type:
    # Create urgent maintenance activities
    urgent_activities = [
        {
            'title': 'Urgent Transformer Inspection',
            'description': 'Urgent inspection required for transformer maintenance',
            'status': 'pending',
            'priority': 'high',
            'days_from_now': 2
        },
        {
            'title': 'Emergency Oil Analysis',
            'description': 'Emergency oil analysis for equipment failure investigation',
            'status': 'in_progress',
            'priority': 'high',
            'days_from_now': 1
        },
        {
            'title': 'Overdue Safety Check',
            'description': 'Overdue safety inspection that needs immediate attention',
            'status': 'overdue',
            'priority': 'high',
            'days_from_now': -1
        }
    ]
    
    # Create upcoming maintenance activities
    upcoming_activities = [
        {
            'title': 'Scheduled Filter Replacement',
            'description': 'Regular filter replacement as per maintenance schedule',
            'status': 'scheduled',
            'priority': 'medium',
            'days_from_now': 14
        },
        {
            'title': 'Monthly Equipment Cleaning',
            'description': 'Monthly cleaning and maintenance of equipment',
            'status': 'pending',
            'priority': 'low',
            'days_from_now': 21
        },
        {
            'title': 'Quarterly Calibration',
            'description': 'Quarterly calibration of measurement instruments',
            'status': 'scheduled',
            'priority': 'medium',
            'days_from_now': 28
        }
    ]
    
    created_count = 0
    
    # Create urgent activities
    for activity_data in urgent_activities:
        start_time = datetime.now() + timedelta(days=activity_data['days_from_now'])
        end_time = start_time + timedelta(hours=2)
        
        activity = MaintenanceActivity.objects.create(
            equipment=equipment,
            activity_type=activity_type,
            title=activity_data['title'],
            description=activity_data['description'],
            status=activity_data['status'],
            priority=activity_data['priority'],
            scheduled_start=start_time,
            scheduled_end=end_time,
            created_by=admin_user,
            updated_by=admin_user
        )
        created_count += 1
        print(f"Created: {activity.title} (Status: {activity.status}, Due: {start_time.strftime('%Y-%m-%d')})")
    
    # Create upcoming activities
    for activity_data in upcoming_activities:
        start_time = datetime.now() + timedelta(days=activity_data['days_from_now'])
        end_time = start_time + timedelta(hours=2)
        
        activity = MaintenanceActivity.objects.create(
            equipment=equipment,
            activity_type=activity_type,
            title=activity_data['title'],
            description=activity_data['description'],
            status=activity_data['status'],
            priority=activity_data['priority'],
            scheduled_start=start_time,
            scheduled_end=end_time,
            created_by=admin_user,
            updated_by=admin_user
        )
        created_count += 1
        print(f"Created: {activity.title} (Status: {activity.status}, Due: {start_time.strftime('%Y-%m-%d')})")
    
    print(f"Successfully created {created_count} maintenance activities")
else:
    print("ERROR: No equipment or activity type found")
'''
    
    # Save script to temporary file
    with open('create_maintenance_script.py', 'w') as f:
        f.write(script_content)
    
    # Execute the script via Django shell
    payload = {"command": "shell", "script": "create_maintenance_script.py"}
    headers = {
        'X-CSRFToken': session.cookies.get('csrftoken'),
        'Referer': BASE_URL,
        'Content-Type': 'application/json',
    }
    
    print("Creating maintenance activities via Django shell...")
    response = session.post(api_url, json=payload, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            print("SUCCESS: Maintenance activities created via shell")
            print(f"Output: {result.get('output', '')}")
            return True
        else:
            print(f"FAIL: Shell command error: {result.get('error')}")
            print(f"Output: {result.get('output', '')}")
            return False
    else:
        print(f"FAIL: Shell command returned status {response.status_code}")
        print(f"Response: {response.text[:500]}")
        return False

def main():
    """Main function."""
    print("Create Maintenance Activities via Shell")
    print("=" * 50)
    print(f"Target: {BASE_URL}")
    print("=" * 50)

    session = requests.Session()
    if not login_admin(session):
        print("FAIL: Admin login failed, cannot proceed.")
        return

    if not create_maintenance_via_shell(session):
        print("FAIL: Could not create maintenance activities via shell.")
        return

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
