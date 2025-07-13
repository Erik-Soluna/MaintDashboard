"""
Management command to populate the database with sample maintenance data.
"""

from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Location
from equipment.models import Equipment
from maintenance.models import MaintenanceActivity, MaintenanceActivityType, MaintenanceSchedule
from events.models import CalendarEvent


class Command(BaseCommand):
    help = 'Populate database with sample maintenance activities and calendar events'

    def handle(self, *args, **options):
        self.stdout.write('Starting to populate maintenance data...')
        
        # Get admin user
        admin_user = User.objects.get(username='admin')
        
        # Get some equipment for maintenance activities
        equipment_list = Equipment.objects.all()[:10]  # Use first 10 equipment items
        
        if not equipment_list:
            self.stdout.write('No equipment found. Please run populate_sample_data first.')
            return
        
        # Create maintenance activity types
        activity_types = []
        type_data = [
            ('DGA Analysis', 'Dissolved Gas Analysis for transformers', 'quarterly'),
            ('Oil Testing', 'Oil quality and contamination testing', 'monthly'),
            ('Visual Inspection', 'General visual inspection and cleaning', 'weekly'),
            ('Thermal Imaging', 'Infrared thermal imaging scan', 'monthly'),
            ('Electrical Testing', 'Electrical parameter testing', 'quarterly'),
        ]
        
        for name, description, frequency in type_data:
            activity_type, created = MaintenanceActivityType.objects.get_or_create(
                name=name,
                defaults={
                    'description': description,
                    'estimated_duration': timedelta(hours=2),
                    'frequency': frequency,
                    'is_active': True,
                    'created_by': admin_user,
                }
            )
            activity_types.append(activity_type)
            if created:
                self.stdout.write(f'Created activity type: {name}')
        
        # Create maintenance schedules
        schedules = []
        for equipment in equipment_list:
            for activity_type in activity_types:
                # Create a schedule for each equipment-activity type combination
                schedule, created = MaintenanceSchedule.objects.get_or_create(
                    equipment=equipment,
                    activity_type=activity_type,
                    defaults={
                        'frequency': activity_type.frequency,
                        'next_due_date': datetime.now().date() + timedelta(days=30),
                        'is_active': True,
                        'created_by': admin_user,
                    }
                )
                schedules.append(schedule)
                if created:
                    self.stdout.write(f'Created schedule: {activity_type.name} for {equipment.name}')
        
        # Create maintenance activities (some completed, some pending)
        activities = []
        
        # Create some completed activities
        for i, equipment in enumerate(equipment_list[:5]):
            for j, activity_type in enumerate(activity_types[:3]):
                # Completed activity
                completed_date = datetime.now() - timedelta(days=30 + i*7 + j*3)
                activity, created = MaintenanceActivity.objects.get_or_create(
                    equipment=equipment,
                    activity_type=activity_type,
                    scheduled_start=completed_date,
                    defaults={
                        'status': 'completed',
                        'actual_start': completed_date,
                        'actual_end': completed_date + timedelta(hours=2),
                        'notes': f'Completed {activity_type.name} for {equipment.name}. All parameters within normal range.',
                        'assigned_to': admin_user,
                        'created_by': admin_user,
                    }
                )
                activities.append(activity)
                if created:
                    self.stdout.write(f'Created completed activity: {activity_type.name} for {equipment.name}')
                
                # Create corresponding calendar event
                event, created = CalendarEvent.objects.get_or_create(
                    title=f'{activity_type.name} - {equipment.name}',
                    event_date=completed_date.date(),
                    start_time=completed_date.time(),
                    equipment=equipment,
                    defaults={
                        'end_time': (completed_date + timedelta(hours=2)).time(),
                        'description': f'Completed {activity_type.name} for {equipment.name}',
                        'event_type': 'maintenance',
                        'created_by': admin_user,
                    }
                )
                if created:
                    self.stdout.write(f'Created calendar event for completed activity')
        
        # Create some pending activities
        for i, equipment in enumerate(equipment_list[5:8]):
            for j, activity_type in enumerate(activity_types[3:]):
                # Pending activity
                scheduled_date = datetime.now() + timedelta(days=7 + i*3 + j*2)
                activity, created = MaintenanceActivity.objects.get_or_create(
                    equipment=equipment,
                    activity_type=activity_type,
                    scheduled_start=scheduled_date,
                    defaults={
                        'status': 'pending',
                        'notes': f'Scheduled {activity_type.name} for {equipment.name}',
                        'assigned_to': admin_user,
                        'created_by': admin_user,
                    }
                )
                activities.append(activity)
                if created:
                    self.stdout.write(f'Created pending activity: {activity_type.name} for {equipment.name}')
                
                # Create corresponding calendar event
                event, created = CalendarEvent.objects.get_or_create(
                    title=f'{activity_type.name} - {equipment.name}',
                    event_date=scheduled_date.date(),
                    start_time=scheduled_date.time(),
                    equipment=equipment,
                    defaults={
                        'end_time': (scheduled_date + timedelta(hours=2)).time(),
                        'description': f'Scheduled {activity_type.name} for {equipment.name}',
                        'event_type': 'maintenance',
                        'created_by': admin_user,
                    }
                )
                if created:
                    self.stdout.write(f'Created calendar event for pending activity')
        
        # Create some overdue activities
        for i, equipment in enumerate(equipment_list[8:]):
            for j, activity_type in enumerate(activity_types[:2]):
                # Overdue activity
                overdue_date = datetime.now() - timedelta(days=15 + i*5 + j*2)
                activity, created = MaintenanceActivity.objects.get_or_create(
                    equipment=equipment,
                    activity_type=activity_type,
                    scheduled_start=overdue_date,
                    defaults={
                        'status': 'overdue',
                        'notes': f'Overdue {activity_type.name} for {equipment.name}. Requires immediate attention.',
                        'assigned_to': admin_user,
                        'created_by': admin_user,
                    }
                )
                activities.append(activity)
                if created:
                    self.stdout.write(f'Created overdue activity: {activity_type.name} for {equipment.name}')
                
                # Create corresponding calendar event
                event, created = CalendarEvent.objects.get_or_create(
                    title=f'OVERDUE: {activity_type.name} - {equipment.name}',
                    event_date=overdue_date.date(),
                    start_time=overdue_date.time(),
                    equipment=equipment,
                    defaults={
                        'end_time': (overdue_date + timedelta(hours=2)).time(),
                        'description': f'OVERDUE: {activity_type.name} for {equipment.name}. Requires immediate attention.',
                        'event_type': 'maintenance',
                        'created_by': admin_user,
                    }
                )
                if created:
                    self.stdout.write(f'Created calendar event for overdue activity')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully populated maintenance data with:\n'
                f'- {len(activity_types)} maintenance activity types\n'
                f'- {len(schedules)} maintenance schedules\n'
                f'- {len(activities)} maintenance activities (completed, pending, overdue)\n'
                f'- Corresponding calendar events for all activities'
            )
        ) 