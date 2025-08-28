"""
Management command to add new maintenance activity type categories.
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from maintenance.models import ActivityTypeCategory


class Command(BaseCommand):
    help = 'Add a new maintenance activity type category'

    def add_arguments(self, parser):
        parser.add_argument('name', type=str, help='Category name')
        parser.add_argument('--description', type=str, default='', help='Category description')
        parser.add_argument('--color', type=str, default='#007bff', help='Hex color code (default: #007bff)')
        parser.add_argument('--icon', type=str, default='fas fa-wrench', help='FontAwesome icon class (default: fas fa-wrench)')
        parser.add_argument('--sort-order', type=int, default=0, help='Sort order (default: 0)')
        parser.add_argument('--active', action='store_true', help='Set category as active (default: inactive)')
        parser.add_argument('--global', action='store_true', dest='is_global', help='Set as global category')

    def handle(self, *args, **options):
        name = options['name']
        description = options['description']
        color = options['color']
        icon = options['icon']
        sort_order = options['sort_order']
        is_active = options['active']
        is_global = options['is_global']

        # Check if category already exists
        if ActivityTypeCategory.objects.filter(name=name).exists():
            self.stdout.write(
                self.style.WARNING(f'Category "{name}" already exists.')
            )
            return

        # Create the category
        try:
            category = ActivityTypeCategory.objects.create(
                name=name,
                description=description,
                color=color,
                icon=icon,
                sort_order=sort_order,
                is_active=is_active,
                is_global=is_global
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created category "{name}" with ID {category.id}'
                )
            )
            
            # Display category details
            self.stdout.write(f'  Description: {description or "None"}')
            self.stdout.write(f'  Color: {color}')
            self.stdout.write(f'  Icon: {icon}')
            self.stdout.write(f'  Sort Order: {sort_order}')
            self.stdout.write(f'  Active: {is_active}')
            self.stdout.write(f'  Global: {is_global}')
            
        except Exception as e:
            raise CommandError(f'Failed to create category: {str(e)}')
