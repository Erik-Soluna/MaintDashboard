"""
Simple management command to populate the database with basic maintenance data.
"""

from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from equipment.models import Equipment
from events.models import CalendarEvent


class Command(BaseCommand):
    help = 'Populate database with simple maintenance activities and calendar events'

    def handle(self, *args, **options):
        self.stdout.write('Starting to populate simple maintenance data...')
        
        # Get admin user
        admin_user = User.objects.get(username='admin')
        
        # Get some equipment for maintenance activities
        equipment_list = Equipment.objects.all()[:10]  # Use first 10 equipment items
        
        if not equipment_list:
            self.stdout.write('No equipment found. Please run populate_sample_data first.')
            return
        
        # Create simple calendar events for maintenance activities
        events_created = 0
        
        # Create some completed maintenance events
        for i, equipment in enumerate(equipment_list[:5]):
            for j in range(3):  # 3 events per equipment
                # Completed event
                completed_date = datetime.now() - timedelta(days=30 + i*7 + j*3)
                event, created = CalendarEvent.objects.get_or_create(
                    title=f'DGA Analysis - {equipment.name}',
                    event_date=completed_date.date(),
                    start_time=completed_date.time(),
                    equipment=equipment,
                    defaults={
                        'end_time': (completed_date + timedelta(hours=2)).time(),
                        'description': f'Completed DGA Analysis for {equipment.name}. All parameters within normal range.',
                        'event_type': 'maintenance',
                        'priority': 'medium',
                        'is_completed': True,
                        'completion_notes': 'Analysis completed successfully. No issues detected.',
                        'created_by': admin_user,
                    }
                )
                if created:
                    events_created += 1
                    self.stdout.write(f'Created completed event: DGA Analysis for {equipment.name}')
        
        # Create some pending maintenance events
        for i, equipment in enumerate(equipment_list[5:8]):
            for j in range(2):  # 2 events per equipment
                # Pending event
                scheduled_date = datetime.now() + timedelta(days=7 + i*3 + j*2)
                event, created = CalendarEvent.objects.get_or_create(
                    title=f'Oil Testing - {equipment.name}',
                    event_date=scheduled_date.date(),
                    start_time=scheduled_date.time(),
                    equipment=equipment,
                    defaults={
                        'end_time': (scheduled_date + timedelta(hours=1)).time(),
                        'description': f'Scheduled Oil Testing for {equipment.name}',
                        'event_type': 'maintenance',
                        'priority': 'medium',
                        'assigned_to': admin_user,
                        'created_by': admin_user,
                    }
                )
                if created:
                    events_created += 1
                    self.stdout.write(f'Created pending event: Oil Testing for {equipment.name}')
        
        # Create some overdue maintenance events
        for i, equipment in enumerate(equipment_list[8:]):
            for j in range(1):  # 1 event per equipment
                # Overdue event
                overdue_date = datetime.now() - timedelta(days=15 + i*5 + j*2)
                event, created = CalendarEvent.objects.get_or_create(
                    title=f'OVERDUE: Visual Inspection - {equipment.name}',
                    event_date=overdue_date.date(),
                    start_time=overdue_date.time(),
                    equipment=equipment,
                    defaults={
                        'end_time': (overdue_date + timedelta(hours=1)).time(),
                        'description': f'OVERDUE: Visual Inspection for {equipment.name}. Requires immediate attention.',
                        'event_type': 'maintenance',
                        'priority': 'high',
                        'assigned_to': admin_user,
                        'created_by': admin_user,
                    }
                )
                if created:
                    events_created += 1
                    self.stdout.write(f'Created overdue event: Visual Inspection for {equipment.name}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully populated simple maintenance data with:\n'
                f'- {events_created} calendar events (completed, pending, overdue)\n'
                f'- Events are synchronized between maintenance and calendar modules'
            )
        ) 