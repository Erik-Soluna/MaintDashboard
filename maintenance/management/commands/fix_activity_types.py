"""
Management command to check and fix maintenance activity types.
Ensures all activity types have proper categories assigned.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from maintenance.models import MaintenanceActivityType, ActivityTypeCategory


class Command(BaseCommand):
    help = 'Check and fix maintenance activity types'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Fix activity types that are missing categories',
        )

    def handle(self, *args, **options):
        self.stdout.write('Checking maintenance activity types...')
        
        # Get or create admin user
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        
        # Get or create default categories
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
        
        # Check all activity types
        activity_types = MaintenanceActivityType.objects.all()
        
        self.stdout.write(f'Found {activity_types.count()} activity types:')
        
        for activity_type in activity_types:
            self.stdout.write(f'  - {activity_type.name} (Category: {activity_type.category.name if activity_type.category else "None"})')
            
            # Check if category is missing
            if not activity_type.category:
                if options['fix']:
                    # Assign category based on name
                    if 'inspection' in activity_type.name.lower():
                        activity_type.category = inspection_category
                    elif 'corrective' in activity_type.name.lower() or 'repair' in activity_type.name.lower():
                        activity_type.category = corrective_category
                    else:
                        activity_type.category = preventive_category
                    
                    activity_type.save()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'    Fixed: Assigned to {activity_type.category.name} category'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'    WARNING: Missing category - run with --fix to fix'
                        )
                    )
        
        # Show summary
        active_types = MaintenanceActivityType.objects.filter(is_active=True)
        self.stdout.write(f'\nActive activity types: {active_types.count()}')
        
        for category in ActivityTypeCategory.objects.filter(is_active=True):
            category_types = MaintenanceActivityType.objects.filter(category=category, is_active=True)
            self.stdout.write(f'  {category.name}: {category_types.count()} types')
        
        if not options['fix']:
            self.stdout.write(
                self.style.WARNING(
                    '\nRun with --fix to automatically assign missing categories'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    '\nActivity types have been checked and fixed!'
                )
            ) 