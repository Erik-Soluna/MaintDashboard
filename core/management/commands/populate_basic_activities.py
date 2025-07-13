"""
Simplified management command to populate basic maintenance activities.
"""

from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from equipment.models import Equipment
from events.models import CalendarEvent


class Command(BaseCommand):
    help = 'Populate database with basic maintenance activities and calendar events'

    def handle(self, *args, **options):
        self.stdout.write('Starting to populate basic maintenance activities...')
        
        # Get admin user
        admin_user = User.objects.get(username='admin')
        
        # Get equipment
        equipment_list = Equipment.objects.all()[:15]  # Use first 15 equipment items
        
        if not equipment_list:
            self.stdout.write('No equipment found. Please run populate_sample_data first.')
            return
        
        activities_created = 0
        events_created = 0
        
        # Activity types for basic maintenance
        activity_types = [
            ('DGA Analysis', 'Dissolved Gas Analysis for transformers', 2),
            ('Oil Testing', 'Oil quality and contamination testing', 1),
            ('Visual Inspection', 'General visual inspection and cleaning', 1),
            ('Thermal Imaging', 'Infrared thermal imaging scan', 2),
            ('Electrical Testing', 'Electrical parameter testing', 3),
            ('Load Testing', 'Equipment load testing', 4),
            ('Performance Testing', 'Performance evaluation testing', 3),
            ('Reliability Testing', 'Reliability assessment testing', 5),
        ]
        
        # Create completed activities (past)
        for i, equipment in enumerate(equipment_list[:8]):
            for j, (activity_name, description, duration) in enumerate(activity_types[:4]):
                # Completed activity
                completed_date = datetime.now() - timedelta(days=30 + i*7 + j*3)
                
                # Create calendar event for completed activity
                event, created = CalendarEvent.objects.get_or_create(
                    title=f'{activity_name} - {equipment.name}',
                    event_date=completed_date.date(),
                    start_time=completed_date.time(),
                    equipment=equipment,
                    defaults={
                        'end_time': (completed_date + timedelta(hours=duration)).time(),
                        'description': f'Completed {activity_name} for {equipment.name}. {description}',
                        'event_type': 'maintenance',
                        'priority': 'medium',
                        'is_completed': True,
                        'completion_notes': f'{activity_name} completed successfully. All parameters within normal range.',
                        'created_by': admin_user,
                    }
                )
                if created:
                    events_created += 1
                    self.stdout.write(f'Created completed event: {activity_name} for {equipment.name}')
        
        # Create pending activities (future)
        for i, equipment in enumerate(equipment_list[8:12]):
            for j, (activity_name, description, duration) in enumerate(activity_types[4:6]):
                # Pending activity
                scheduled_date = datetime.now() + timedelta(days=7 + i*3 + j*2)
                
                # Create calendar event for pending activity
                event, created = CalendarEvent.objects.get_or_create(
                    title=f'{activity_name} - {equipment.name}',
                    event_date=scheduled_date.date(),
                    start_time=scheduled_date.time(),
                    equipment=equipment,
                    defaults={
                        'end_time': (scheduled_date + timedelta(hours=duration)).time(),
                        'description': f'Scheduled {activity_name} for {equipment.name}. {description}',
                        'event_type': 'maintenance',
                        'priority': 'medium',
                        'assigned_to': admin_user,
                        'created_by': admin_user,
                    }
                )
                if created:
                    events_created += 1
                    self.stdout.write(f'Created pending event: {activity_name} for {equipment.name}')
        
        # Create overdue activities (past due)
        for i, equipment in enumerate(equipment_list[12:]):
            for j, (activity_name, description, duration) in enumerate(activity_types[6:8]):
                # Overdue activity
                overdue_date = datetime.now() - timedelta(days=15 + i*5 + j*2)
                
                # Create calendar event for overdue activity
                event, created = CalendarEvent.objects.get_or_create(
                    title=f'OVERDUE: {activity_name} - {equipment.name}',
                    event_date=overdue_date.date(),
                    start_time=overdue_date.time(),
                    equipment=equipment,
                    defaults={
                        'end_time': (overdue_date + timedelta(hours=duration)).time(),
                        'description': f'OVERDUE: {activity_name} for {equipment.name}. {description} Requires immediate attention.',
                        'event_type': 'maintenance',
                        'priority': 'high',
                        'assigned_to': admin_user,
                        'created_by': admin_user,
                    }
                )
                if created:
                    events_created += 1
                    self.stdout.write(f'Created overdue event: {activity_name} for {equipment.name}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully populated basic maintenance data with:\n'
                f'- {events_created} calendar events (completed, pending, overdue)\n'
                f'- Events represent maintenance activities synchronized with calendar\n'
                f'- Includes overdue items for testing dashboard functionality'
            )
        ) 