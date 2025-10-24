
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
