"""
Management command to create test maintenance activities for dashboard testing.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from maintenance.models import MaintenanceActivity, MaintenanceActivityType
from equipment.models import Equipment
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Create test maintenance activities for dashboard testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force creation even if activities already exist',
        )

    def handle(self, *args, **options):
        force = options['force']
        
        self.stdout.write('Creating test maintenance activities...')
        
        # Check if activities already exist
        existing_count = MaintenanceActivity.objects.count()
        if existing_count > 0 and not force:
            self.stdout.write(
                self.style.WARNING(f'Found {existing_count} existing activities. Use --force to recreate.')
            )
            return
        
        # Get equipment and activity type
        equipment = Equipment.objects.filter(is_active=True).first()
        activity_type = MaintenanceActivityType.objects.filter(is_active=True).first()
        admin_user = User.objects.get(username='admin')
        
        if not equipment:
            self.stdout.write(self.style.ERROR('No active equipment found'))
            return
            
        if not activity_type:
            self.stdout.write(self.style.ERROR('No active activity type found'))
            return
        
        # Create urgent maintenance activities (due within 7 days)
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
        
        # Create upcoming maintenance activities (due within 30 days)
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
        self.stdout.write('Creating urgent maintenance activities...')
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
            self.stdout.write(f'  Created: {activity.title} (Status: {activity.status}, Due: {start_time.strftime("%Y-%m-%d")})')
        
        # Create upcoming activities
        self.stdout.write('Creating upcoming maintenance activities...')
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
            self.stdout.write(f'  Created: {activity.title} (Status: {activity.status}, Due: {start_time.strftime("%Y-%m-%d")})')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} maintenance activities!')
        )
