"""
Management command to create global activity types.
Global activity types can be applied to any equipment category.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from maintenance.models import ActivityTypeCategory, MaintenanceActivityType
from core.models import EquipmentCategory


class Command(BaseCommand):
    help = 'Create global activity types that can be applied to any equipment category'

    def handle(self, *args, **options):
        self.stdout.write('Creating global activity types...')
        
        # Get or create a superuser for created_by field
        try:
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                user = User.objects.create_superuser('admin', 'admin@example.com', 'admin')
        except Exception as e:
            self.stdout.write(f'Warning: Could not get/create superuser: {e}')
            user = None
        
        # Create Global category
        global_category, created = ActivityTypeCategory.objects.get_or_create(
            name='Global',
            defaults={
                'description': 'General-purpose activities that can be applied to any equipment category',
                'color': '#FF6B35',  # Orange color for global
                'icon': 'fas fa-globe',
                'is_global': True,
                'sort_order': 0,  # Show first
                'created_by': user
            }
        )
        
        if created:
            self.stdout.write(f'Created global category: {global_category.name}')
        else:
            self.stdout.write(f'Global category already exists: {global_category.name}')
        
        # Define global activity types
        global_activity_types = [
            {
                'name': 'Physical Inspection',
                'description': 'General visual inspection of equipment condition, cleanliness, and basic functionality',
                'estimated_duration_hours': 1,
                'frequency_days': 30,
                'is_mandatory': True,
                'tools_required': 'Flashlight, inspection checklist',
                'parts_required': 'None',
                'safety_notes': 'Ensure equipment is properly shut down before inspection. Wear appropriate PPE.',
            },
            {
                'name': 'General Cleaning',
                'description': 'Basic cleaning and housekeeping of equipment and surrounding area',
                'estimated_duration_hours': 2,
                'frequency_days': 7,
                'is_mandatory': False,
                'tools_required': 'Cleaning supplies, rags, vacuum',
                'parts_required': 'None',
                'safety_notes': 'Use appropriate cleaning agents. Avoid getting liquids in electrical components.',
            },
            {
                'name': 'Safety Check',
                'description': 'Verify safety systems, emergency stops, and safety signage are functional',
                'estimated_duration_hours': 1,
                'frequency_days': 14,
                'is_mandatory': True,
                'tools_required': 'Safety checklist, test equipment',
                'parts_required': 'None',
                'safety_notes': 'Test safety systems carefully. Document any issues immediately.',
            },
            {
                'name': 'Documentation Review',
                'description': 'Review and update equipment documentation, manuals, and procedures',
                'estimated_duration_hours': 2,
                'frequency_days': 90,
                'is_mandatory': False,
                'tools_required': 'Documentation, computer',
                'parts_required': 'None',
                'safety_notes': 'Ensure documentation is accurate and up-to-date.',
            },
            {
                'name': 'Environmental Monitoring',
                'description': 'Check environmental conditions around equipment (temperature, humidity, etc.)',
                'estimated_duration_hours': 1,
                'frequency_days': 7,
                'is_mandatory': False,
                'tools_required': 'Thermometer, hygrometer, environmental monitoring equipment',
                'parts_required': 'None',
                'safety_notes': 'Record environmental readings accurately.',
            },
            {
                'name': 'General Maintenance',
                'description': 'General maintenance tasks not covered by specific activity types',
                'estimated_duration_hours': 4,
                'frequency_days': 30,
                'is_mandatory': False,
                'tools_required': 'General hand tools',
                'parts_required': 'As needed',
                'safety_notes': 'Follow standard safety procedures for the specific task.',
            },
        ]
        
        # Create global activity types
        created_count = 0
        for activity_data in global_activity_types:
            activity_type, created = MaintenanceActivityType.objects.get_or_create(
                name=activity_data['name'],
                category=global_category,
                defaults={
                    'description': activity_data['description'],
                    'estimated_duration_hours': activity_data['estimated_duration_hours'],
                    'frequency_days': activity_data['frequency_days'],
                    'is_mandatory': activity_data['is_mandatory'],
                    'tools_required': activity_data['tools_required'],
                    'parts_required': activity_data['parts_required'],
                    'safety_notes': activity_data['safety_notes'],
                    'created_by': user
                }
            )
            
            if created:
                self.stdout.write(f'Created global activity type: {activity_type.name}')
                created_count += 1
            else:
                self.stdout.write(f'Global activity type already exists: {activity_type.name}')
        
        # Make global activity types applicable to all equipment categories
        equipment_categories = EquipmentCategory.objects.filter(is_active=True)
        global_activity_types = MaintenanceActivityType.objects.filter(category=global_category)
        
        for activity_type in global_activity_types:
            # Add all equipment categories to applicable_equipment_categories
            activity_type.applicable_equipment_categories.add(*equipment_categories)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} global activity types. '
                f'All global activity types are now applicable to {equipment_categories.count()} equipment categories.'
            )
        )
        
        self.stdout.write('\nGlobal activity types created:')
        for activity_type in MaintenanceActivityType.objects.filter(category=global_category):
            self.stdout.write(f'  - {activity_type.name}: {activity_type.description[:50]}...') 