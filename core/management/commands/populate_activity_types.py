"""
Management command to populate default activity types for maintenance.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from maintenance.models import ActivityTypeCategory, MaintenanceActivityType
from core.models import EquipmentCategory


class Command(BaseCommand):
    help = 'Populate database with default activity types and categories'

    def handle(self, *args, **options):
        self.stdout.write('Starting to populate default activity types...')
        
        # Get admin user
        admin_user = User.objects.get(username='admin')
        
        # Get equipment category
        equipment_category = EquipmentCategory.objects.get(name='Transformers')
        
        # Create activity type categories
        categories = []
        category_data = [
            ('Preventive Maintenance', 'Regular preventive maintenance activities', '#28a745', 'fas fa-shield-alt'),
            ('Inspection', 'Regular inspection and monitoring activities', '#17a2b8', 'fas fa-search'),
            ('Testing', 'Equipment testing and analysis activities', '#ffc107', 'fas fa-flask'),
            ('Corrective Maintenance', 'Corrective and repair activities', '#dc3545', 'fas fa-wrench'),
            ('Calibration', 'Calibration and adjustment activities', '#6f42c1', 'fas fa-cogs'),
        ]
        
        for name, description, color, icon in category_data:
            category, created = ActivityTypeCategory.objects.get_or_create(
                name=name,
                defaults={
                    'description': description,
                    'color': color,
                    'icon': icon,
                    'is_active': True,
                    'created_by': admin_user,
                }
            )
            categories.append(category)
            if created:
                self.stdout.write(f'Created category: {name}')
        
        # Create maintenance activity types
        activity_types = []
        type_data = [
            # Preventive Maintenance
            ('DGA Analysis', 'Dissolved Gas Analysis for transformers', 'Preventive Maintenance', 90, 2),
            ('Oil Testing', 'Oil quality and contamination testing', 'Preventive Maintenance', 30, 1),
            ('Visual Inspection', 'General visual inspection and cleaning', 'Preventive Maintenance', 7, 1),
            ('Thermal Imaging', 'Infrared thermal imaging scan', 'Preventive Maintenance', 30, 2),
            ('Electrical Testing', 'Electrical parameter testing', 'Preventive Maintenance', 90, 3),
            
            # Inspection
            ('Routine Inspection', 'Regular equipment inspection', 'Inspection', 7, 1),
            ('Safety Inspection', 'Safety-related inspection', 'Inspection', 30, 1),
            ('Environmental Inspection', 'Environmental condition inspection', 'Inspection', 14, 1),
            
            # Testing
            ('Load Testing', 'Equipment load testing', 'Testing', 180, 4),
            ('Performance Testing', 'Performance evaluation testing', 'Testing', 90, 3),
            ('Reliability Testing', 'Reliability assessment testing', 'Testing', 365, 5),
            
            # Corrective Maintenance
            ('Emergency Repair', 'Emergency repair activities', 'Corrective Maintenance', 0, 4),
            ('Component Replacement', 'Component replacement activities', 'Corrective Maintenance', 0, 6),
            ('System Repair', 'System-level repair activities', 'Corrective Maintenance', 0, 8),
            
            # Calibration
            ('Instrument Calibration', 'Instrument calibration activities', 'Calibration', 180, 2),
            ('System Calibration', 'System calibration activities', 'Calibration', 365, 4),
        ]
        
        for name, description, category_name, frequency_days, duration_hours in type_data:
            category = next(cat for cat in categories if cat.name == category_name)
            activity_type, created = MaintenanceActivityType.objects.get_or_create(
                name=name,
                defaults={
                    'category': category,
                    'description': description,
                    'estimated_duration_hours': duration_hours,
                    'frequency_days': frequency_days,
                    'is_mandatory': True,
                    'is_active': True,
                    'tools_required': 'Standard maintenance tools',
                    'parts_required': 'As needed based on inspection',
                    'safety_notes': 'Follow all safety protocols',
                    'created_by': admin_user,
                }
            )
            activity_type.applicable_equipment_categories.add(equipment_category)
            activity_types.append(activity_type)
            if created:
                self.stdout.write(f'Created activity type: {name} ({category_name})')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully populated activity types with:\n'
                f'- {len(categories)} activity type categories\n'
                f'- {len(activity_types)} maintenance activity types\n'
                f'- All types configured for Transformers equipment category'
            )
        ) 