"""
Management command to add new equipment categories.
"""

from django.core.management.base import BaseCommand, CommandError
from core.models import EquipmentCategory


class Command(BaseCommand):
    help = 'Add a new equipment category'

    def add_arguments(self, parser):
        parser.add_argument('name', type=str, help='Category name')
        parser.add_argument('--description', type=str, default='', help='Category description')
        parser.add_argument('--active', action='store_true', help='Set category as active (default: inactive)')

    def handle(self, *args, **options):
        name = options['name']
        description = options['description']
        is_active = options['active']

        # Check if category already exists
        if EquipmentCategory.objects.filter(name=name).exists():
            self.stdout.write(
                self.style.WARNING(f'Equipment category "{name}" already exists.')
            )
            return

        # Create the category
        try:
            category = EquipmentCategory.objects.create(
                name=name,
                description=description,
                is_active=is_active
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created equipment category "{name}" with ID {category.id}'
                )
            )
            
            # Display category details
            self.stdout.write(f'  Description: {description or "None"}')
            self.stdout.write(f'  Active: {is_active}')
            
        except Exception as e:
            raise CommandError(f'Failed to create equipment category: {str(e)}')
