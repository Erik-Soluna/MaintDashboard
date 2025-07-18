"""
Management command to sync calendar event types with maintenance activity types.
Creates maintenance activity types that match the calendar event types.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from maintenance.models import MaintenanceActivityType, ActivityTypeCategory
from events.models import CalendarEvent


class Command(BaseCommand):
    help = 'Sync calendar event types with maintenance activity types'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of existing activity types',
        )

    def handle(self, *args, **options):
        self.stdout.write('Syncing calendar event types with maintenance activity types...')
        
        # Get or create admin user
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        
        # Get or create categories
        preventive_category, _ = ActivityTypeCategory.objects.get_or_create(
            name='Preventive',
            defaults={
                'description': 'Preventive maintenance activities',
                'color': '#28a745',
                'icon': 'fas fa-shield-alt',
                'is_global': True,
            }
        )
        
        inspection_category, _ = ActivityTypeCategory.objects.get_or_create(
            name='Inspection',
            defaults={
                'description': 'Inspection and testing activities',
                'color': '#17a2b8',
                'icon': 'fas fa-search',
                'is_global': True,
            }
        )
        
        corrective_category, _ = ActivityTypeCategory.objects.get_or_create(
            name='Corrective',
            defaults={
                'description': 'Corrective maintenance activities',
                'color': '#dc3545',
                'icon': 'fas fa-wrench',
                'is_global': True,
            }
        )
        
        # Map calendar event types to maintenance activity types
        calendar_to_maintenance_map = {
            'maintenance': {
                'name': 'Maintenance Activity',
                'category': preventive_category,
                'description': 'General maintenance activity',
                'estimated_duration_hours': 2,
                'frequency_days': 30,
                'is_mandatory': True,
            },
            'inspection': {
                'name': 'Inspection',
                'category': inspection_category,
                'description': 'Equipment inspection and testing',
                'estimated_duration_hours': 1,
                'frequency_days': 7,
                'is_mandatory': True,
            },
            'calibration': {
                'name': 'Calibration',
                'category': inspection_category,
                'description': 'Equipment calibration and adjustment',
                'estimated_duration_hours': 3,
                'frequency_days': 90,
                'is_mandatory': True,
            },
            'outage': {
                'name': 'Equipment Outage',
                'category': corrective_category,
                'description': 'Planned equipment outage for maintenance',
                'estimated_duration_hours': 8,
                'frequency_days': 365,
                'is_mandatory': False,
            },
            'upgrade': {
                'name': 'Equipment Upgrade',
                'category': corrective_category,
                'description': 'Equipment upgrade or modification',
                'estimated_duration_hours': 16,
                'frequency_days': 730,
                'is_mandatory': False,
            },
            'commissioning': {
                'name': 'Commissioning',
                'category': preventive_category,
                'description': 'Equipment commissioning and startup',
                'estimated_duration_hours': 4,
                'frequency_days': 3650,  # 10 years
                'is_mandatory': False,
            },
            'decommissioning': {
                'name': 'Decommissioning',
                'category': corrective_category,
                'description': 'Equipment decommissioning and removal',
                'estimated_duration_hours': 8,
                'frequency_days': 3650,  # 10 years
                'is_mandatory': False,
            },
            'testing': {
                'name': 'Testing',
                'category': inspection_category,
                'description': 'Equipment testing and validation',
                'estimated_duration_hours': 2,
                'frequency_days': 30,
                'is_mandatory': True,
            },
            'other': {
                'name': 'Other',
                'category': preventive_category,
                'description': 'Other maintenance activities',
                'estimated_duration_hours': 1,
                'frequency_days': 30,
                'is_mandatory': False,
            },
        }
        
        # Create or update activity types for each calendar event type
        for calendar_type, activity_data in calendar_to_maintenance_map.items():
            # Check if activity type already exists with this name
            activity_type, created = MaintenanceActivityType.objects.get_or_create(
                name=activity_data['name'],
                defaults={
                    'category': activity_data['category'],
                    'description': activity_data['description'],
                    'estimated_duration_hours': activity_data['estimated_duration_hours'],
                    'frequency_days': activity_data['frequency_days'],
                    'is_mandatory': activity_data['is_mandatory'],
                    'is_active': True,
                    'tools_required': 'Standard toolkit',
                    'safety_notes': 'Follow standard safety procedures',
                    'created_by': admin_user,
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created activity type: {activity_data["name"]} (from calendar type: {calendar_type})'
                    )
                )
            elif options['force']:
                # Update existing activity type
                activity_type.category = activity_data['category']
                activity_type.description = activity_data['description']
                activity_type.estimated_duration_hours = activity_data['estimated_duration_hours']
                activity_type.frequency_days = activity_data['frequency_days']
                activity_type.is_mandatory = activity_data['is_mandatory']
                activity_type.is_active = True
                activity_type.save()
                self.stdout.write(
                    self.style.WARNING(
                        f'Updated activity type: {activity_data["name"]} (from calendar type: {calendar_type})'
                    )
                )
            else:
                self.stdout.write(
                    f'Activity type already exists: {activity_data["name"]} (from calendar type: {calendar_type})'
                )
        
        # Show summary
        self.stdout.write('\nSummary:')
        self.stdout.write(f'Calendar event types: {len(CalendarEvent.EVENT_TYPES)}')
        self.stdout.write(f'Maintenance activity types: {MaintenanceActivityType.objects.count()}')
        self.stdout.write(f'Active maintenance activity types: {MaintenanceActivityType.objects.filter(is_active=True).count()}')
        
        self.stdout.write(
            self.style.SUCCESS(
                '\nCalendar event types have been synced with maintenance activity types!'
            )
        ) 