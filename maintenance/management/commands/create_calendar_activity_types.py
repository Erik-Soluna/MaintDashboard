"""
Management command to create activity types that match calendar event types.
Creates the activity types shown in the calendar dropdown.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from maintenance.models import MaintenanceActivityType, ActivityTypeCategory


class Command(BaseCommand):
    help = 'Create activity types that match calendar event types'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of existing activity types',
        )

    def handle(self, *args, **options):
        self.stdout.write('Creating calendar activity types...')
        
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
        
        # Define calendar activity types
        calendar_activity_types = [
            {
                'name': 'Maintenance Activity',
                'category': preventive_category,
                'description': 'General maintenance activity',
                'estimated_duration_hours': 2,
                'frequency_days': 30,
                'is_mandatory': True,
            },
            {
                'name': 'Inspection',
                'category': inspection_category,
                'description': 'Equipment inspection and testing',
                'estimated_duration_hours': 1,
                'frequency_days': 7,
                'is_mandatory': True,
            },
            {
                'name': 'Calibration',
                'category': inspection_category,
                'description': 'Equipment calibration and adjustment',
                'estimated_duration_hours': 3,
                'frequency_days': 90,
                'is_mandatory': True,
            },
            {
                'name': 'Equipment Outage',
                'category': corrective_category,
                'description': 'Planned equipment outage for maintenance',
                'estimated_duration_hours': 8,
                'frequency_days': 365,
                'is_mandatory': False,
            },
            {
                'name': 'Equipment Upgrade',
                'category': corrective_category,
                'description': 'Equipment upgrade or modification',
                'estimated_duration_hours': 16,
                'frequency_days': 730,
                'is_mandatory': False,
            },
            {
                'name': 'Commissioning',
                'category': preventive_category,
                'description': 'Equipment commissioning and startup',
                'estimated_duration_hours': 4,
                'frequency_days': 3650,  # 10 years
                'is_mandatory': False,
            },
            {
                'name': 'Decommissioning',
                'category': corrective_category,
                'description': 'Equipment decommissioning and removal',
                'estimated_duration_hours': 8,
                'frequency_days': 3650,  # 10 years
                'is_mandatory': False,
            },
            {
                'name': 'Testing',
                'category': inspection_category,
                'description': 'Equipment testing and validation',
                'estimated_duration_hours': 2,
                'frequency_days': 30,
                'is_mandatory': True,
            },
            {
                'name': 'Other',
                'category': preventive_category,
                'description': 'Other maintenance activities',
                'estimated_duration_hours': 1,
                'frequency_days': 30,
                'is_mandatory': False,
            },
        ]
        
        # Create activity types
        for activity_data in calendar_activity_types:
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
                        f'Created activity type: {activity_data["name"]}'
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
                        f'Updated activity type: {activity_data["name"]}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created/updated {len(calendar_activity_types)} calendar activity types!'
            )
        ) 