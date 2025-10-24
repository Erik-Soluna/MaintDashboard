#!/usr/bin/env python
"""
Simple script to clear all maintenance activities and calendar events.
This can be run directly or imported into Django shell.
"""

import os
import sys
import django

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maintenance_dashboard.settings')
django.setup()

from django.db import transaction
from maintenance.models import MaintenanceActivity, MaintenanceSchedule
from events.models import CalendarEvent

def clear_maintenance_data():
    """Clear all maintenance activities and calendar events."""
    try:
        with transaction.atomic():
            # Count existing records
            activity_count = MaintenanceActivity.objects.count()
            event_count = CalendarEvent.objects.count()
            schedule_count = MaintenanceSchedule.objects.count()
            
            print(f'Found {activity_count} maintenance activities, {event_count} calendar events, and {schedule_count} maintenance schedules')
            
            # Delete calendar events first (they reference maintenance activities)
            if event_count > 0:
                print('Deleting calendar events...')
                CalendarEvent.objects.all().delete()
                print(f'✅ Deleted {event_count} calendar events')
            
            # Delete maintenance activities
            if activity_count > 0:
                print('Deleting maintenance activities...')
                MaintenanceActivity.objects.all().delete()
                print(f'✅ Deleted {activity_count} maintenance activities')
            
            # Delete maintenance schedules
            if schedule_count > 0:
                print('Deleting maintenance schedules...')
                MaintenanceSchedule.objects.all().delete()
                print(f'✅ Deleted {schedule_count} maintenance schedules')
            
            print('\n🎉 Successfully cleared all maintenance data!')
            print('The system is now clean and ready for fresh data.')
            
    except Exception as e:
        print(f'❌ Error clearing maintenance data: {str(e)}')
        raise

if __name__ == '__main__':
    print('🧹 Clearing all maintenance activities and calendar events...')
    print('⚠️  This will permanently delete all maintenance data!')
    
    # Simple confirmation
    confirm = input('Type "YES" to confirm deletion: ')
    if confirm == 'YES':
        clear_maintenance_data()
    else:
        print('❌ Operation cancelled.')
