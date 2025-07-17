"""
Management command to fix activity types missing categories.
"""

from django.core.management.base import BaseCommand
from maintenance.models import MaintenanceActivityType, ActivityTypeCategory
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Fix activity types that are missing categories'

    def handle(self, *args, **options):
        self.stdout.write('Checking for activity types missing categories...')
        
        # Get or create admin user
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.first()
        
        # Get or create default category
        default_category = ActivityTypeCategory.objects.filter(is_active=True).first()
        if not default_category:
            default_category = ActivityTypeCategory.objects.create(
                name='General',
                description='Default category for activity types',
                color='#007bff',
                icon='fas fa-wrench',
                is_active=True,
                created_by=admin_user
            )
            self.stdout.write(f'Created default category: {default_category.name}')
        
        # Find activity types without categories
        activity_types_without_category = MaintenanceActivityType.objects.filter(category__isnull=True)
        
        if activity_types_without_category.exists():
            self.stdout.write(f'Found {activity_types_without_category.count()} activity types without categories')
            
            for activity_type in activity_types_without_category:
                activity_type.category = default_category
                activity_type.save()
                self.stdout.write(f'  Fixed: {activity_type.name}')
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully fixed {activity_types_without_category.count()} activity types'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('All activity types already have categories')
            )
        
        # Summary
        total_activity_types = MaintenanceActivityType.objects.count()
        self.stdout.write(f'Total activity types: {total_activity_types}')
        self.stdout.write(f'Default category: {default_category.name}') 