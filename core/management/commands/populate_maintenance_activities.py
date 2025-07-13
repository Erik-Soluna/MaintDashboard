"""
Management command to populate maintenance activities with calendar sync.
"""

from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from equipment.models import Equipment
from maintenance.models import MaintenanceActivity, MaintenanceActivityType
from events.models import CalendarEvent


class Command(BaseCommand):
    help = 'Populate database with maintenance activities and synchronized calendar events'

    def handle(self, *args, **options):
        self.stdout.write('Starting to populate maintenance activities...')
        
        # Get admin user
        admin_user = User.objects.get(username='admin')
        
        # Get equipment and activity types
        equipment_list = Equipment.objects.all()[:15]  # Use first 15 equipment items
        activity_types = MaintenanceActivityType.objects.all()[:8]  # Use first 8 activity types
        
        if not equipment_list:
            self.stdout.write('No equipment found. Please run populate_sample_data first.')
            return
        
        if not activity_types:
            self.stdout.write('No activity types found. Please run populate_activity_types first.')
            return
        
        activities_created = 0
        events_created = 0
        
        # Create completed activities (past)
        for i, equipment in enumerate(equipment_list[:8]):
            for j, activity_type in enumerate(activity_types[:4]):
                # Completed activity
                completed_date = datetime.now() - timedelta(days=30 + i*7 + j*3)
                activity, created = MaintenanceActivity.objects.get_or_create(
                    equipment=equipment,
                    activity_type=activity_type,
                    scheduled_start=completed_date,
                    defaults={
                        'title': f'{activity_type.name} - {equipment.name}',
                        'description': f'Completed {activity_type.name} for {equipment.name}',
                        'status': 'completed',
                        'priority': 'medium',
                        'scheduled_start': completed_date,
                        'scheduled_end': completed_date + timedelta(hours=activity_type.estimated_duration_hours),
                        'actual_start': completed_date,
                        'actual_end': completed_date + timedelta(hours=activity_type.estimated_duration_hours),
                        'assigned_to': admin_user,
                        'completion_notes': f'{activity_type.name} completed successfully. All parameters within normal range.',
                        'created_by': admin_user,
                    }
                )
                if created:
                    activities_created += 1
                    self.stdout.write(f'Created completed activity: {activity_type.name} for {equipment.name}')
                
                # Create corresponding calendar event
                event, created = CalendarEvent.objects.get_or_create(
                    title=f'{activity_type.name} - {equipment.name}',
                    event_date=completed_date.date(),
                    start_time=completed_date.time(),
                    equipment=equipment,
                    defaults={
                        'end_time': (completed_date + timedelta(hours=activity_type.estimated_duration_hours)).time(),
                        'description': f'Completed {activity_type.name} for {equipment.name}',
                        'event_type': 'maintenance',
                        'priority': 'medium',
                        'is_completed': True,
                        'completion_notes': 'Activity completed successfully. No issues detected.',
                        'created_by': admin_user,
                    }
                )
                if created:
                    events_created += 1
        
        # Create pending activities (future)
        for i, equipment in enumerate(equipment_list[8:12]):
            for j, activity_type in enumerate(activity_types[4:6]):
                # Pending activity
                scheduled_date = datetime.now() + timedelta(days=7 + i*3 + j*2)
                activity, created = MaintenanceActivity.objects.get_or_create(
                    equipment=equipment,
                    activity_type=activity_type,
                    scheduled_start=scheduled_date,
                    defaults={
                        'title': f'{activity_type.name} - {equipment.name}',
                        'description': f'Scheduled {activity_type.name} for {equipment.name}',
                        'status': 'pending',
                        'priority': 'medium',
                        'scheduled_start': scheduled_date,
                        'scheduled_end': scheduled_date + timedelta(hours=activity_type.estimated_duration_hours),
                        'assigned_to': admin_user,
                        'created_by': admin_user,
                    }
                )
                if created:
                    activities_created += 1
                    self.stdout.write(f'Created pending activity: {activity_type.name} for {equipment.name}')
                
                # Create corresponding calendar event
                event, created = CalendarEvent.objects.get_or_create(
                    title=f'{activity_type.name} - {equipment.name}',
                    event_date=scheduled_date.date(),
                    start_time=scheduled_date.time(),
                    equipment=equipment,
                    defaults={
                        'end_time': (scheduled_date + timedelta(hours=activity_type.estimated_duration_hours)).time(),
                        'description': f'Scheduled {activity_type.name} for {equipment.name}',
                        'event_type': 'maintenance',
                        'priority': 'medium',
                        'assigned_to': admin_user,
                        'created_by': admin_user,
                    }
                )
                if created:
                    events_created += 1
        
        # Create overdue activities (past due)
        for i, equipment in enumerate(equipment_list[12:]):
            for j, activity_type in enumerate(activity_types[6:8]):
                # Overdue activity
                overdue_date = datetime.now() - timedelta(days=15 + i*5 + j*2)
                activity, created = MaintenanceActivity.objects.get_or_create(
                    equipment=equipment,
                    activity_type=activity_type,
                    scheduled_start=overdue_date,
                    defaults={
                        'title': f'OVERDUE: {activity_type.name} - {equipment.name}',
                        'description': f'Overdue {activity_type.name} for {equipment.name}. Requires immediate attention.',
                        'status': 'overdue',
                        'priority': 'high',
                        'scheduled_start': overdue_date,
                        'scheduled_end': overdue_date + timedelta(hours=activity_type.estimated_duration_hours),
                        'assigned_to': admin_user,
                        'created_by': admin_user,
                    }
                )
                if created:
                    activities_created += 1
                    self.stdout.write(f'Created overdue activity: {activity_type.name} for {equipment.name}')
                
                # Create corresponding calendar event
                event, created = CalendarEvent.objects.get_or_create(
                    title=f'OVERDUE: {activity_type.name} - {equipment.name}',
                    event_date=overdue_date.date(),
                    start_time=overdue_date.time(),
                    equipment=equipment,
                    defaults={
                        'end_time': (overdue_date + timedelta(hours=activity_type.estimated_duration_hours)).time(),
                        'description': f'OVERDUE: {activity_type.name} for {equipment.name}. Requires immediate attention.',
                        'event_type': 'maintenance',
                        'priority': 'high',
                        'assigned_to': admin_user,
                        'created_by': admin_user,
                    }
                )
                if created:
                    events_created += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully populated maintenance data with:\n'
                f'- {activities_created} maintenance activities (completed, pending, overdue)\n'
                f'- {events_created} synchronized calendar events\n'
                f'- Activities and calendar events are properly linked'
            )
        ) 