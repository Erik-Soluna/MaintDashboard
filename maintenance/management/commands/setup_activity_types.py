"""
Management command to set up default activity type categories and templates.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from maintenance.models import ActivityTypeCategory, ActivityTypeTemplate, MaintenanceActivityType
from core.models import EquipmentCategory


class Command(BaseCommand):
    help = 'Set up default activity type categories and templates'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset all activity type categories and templates',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.reset_data()
        
        self.create_default_categories()
        self.create_default_templates()
        
        self.stdout.write(
            self.style.SUCCESS('Successfully set up default activity type categories and templates!')
        )

    def reset_data(self):
        """Reset all activity type data."""
        self.stdout.write('Resetting activity type data...')
        
        with transaction.atomic():
            MaintenanceActivityType.objects.all().delete()
            ActivityTypeTemplate.objects.all().delete()
            ActivityTypeCategory.objects.all().delete()
        
        self.stdout.write(self.style.WARNING('All activity type data has been reset.'))

    def create_default_categories(self):
        """Create default activity type categories."""
        self.stdout.write('Creating default activity type categories...')
        
        categories = [
            {
                'name': 'Preventive',
                'description': 'Regular maintenance activities to prevent equipment failure',
                'color': '#28a745',
                'icon': 'fas fa-wrench',
                'sort_order': 1,
            },
            {
                'name': 'Corrective',
                'description': 'Repair and fix activities to restore equipment function',
                'color': '#ffc107',
                'icon': 'fas fa-tools',
                'sort_order': 2,
            },
            {
                'name': 'Inspection',
                'description': 'Visual and testing checks to assess equipment condition',
                'color': '#17a2b8',
                'icon': 'fas fa-search',
                'sort_order': 3,
            },
            {
                'name': 'Cleaning',
                'description': 'Cleaning and housekeeping activities',
                'color': '#6f42c1',
                'icon': 'fas fa-broom',
                'sort_order': 4,
            },
            {
                'name': 'Calibration',
                'description': 'Calibration and adjustment activities',
                'color': '#fd7e14',
                'icon': 'fas fa-balance-scale',
                'sort_order': 5,
            },
            {
                'name': 'Testing',
                'description': 'Functional and performance testing',
                'color': '#e83e8c',
                'icon': 'fas fa-vial',
                'sort_order': 6,
            },
        ]
        
        for category_data in categories:
            category, created = ActivityTypeCategory.objects.get_or_create(
                name=category_data['name'],
                defaults=category_data
            )
            
            if created:
                self.stdout.write(f'  Created category: {category.name}')
            else:
                self.stdout.write(f'  Category already exists: {category.name}')

    def create_default_templates(self):
        """Create default activity type templates for each equipment category."""
        self.stdout.write('Creating default activity type templates...')
        
        # Get all equipment categories
        equipment_categories = EquipmentCategory.objects.filter(is_active=True)
        activity_categories = ActivityTypeCategory.objects.all()
        
        if not equipment_categories.exists():
            self.stdout.write(self.style.WARNING('No equipment categories found. Please create equipment categories first.'))
            return
        
        # Define template patterns for different equipment types
        template_patterns = {
            'preventive': {
                'category_name': 'Preventive',
                'templates': [
                    {
                        'name': 'Annual Inspection',
                        'description': 'Comprehensive annual inspection and maintenance',
                        'estimated_duration_hours': 4,
                        'frequency_days': 365,
                        'is_mandatory': True,
                        'default_tools_required': 'Standard toolkit, measuring instruments, safety equipment',
                        'default_safety_notes': 'Ensure equipment is de-energized and properly locked out',
                        'checklist_template': 'Visual inspection of all components\nCheck all connections and fasteners\nTest operational controls\nVerify safety systems\nClean and lubricate as needed\nDocument findings and recommendations',
                    },
                    {
                        'name': 'Monthly Check',
                        'description': 'Monthly operational check and minor maintenance',
                        'estimated_duration_hours': 1,
                        'frequency_days': 30,
                        'is_mandatory': True,
                        'default_tools_required': 'Basic toolkit, cleaning supplies',
                        'default_safety_notes': 'Follow standard safety procedures',
                        'checklist_template': 'Visual inspection\nCheck operation\nClean equipment\nVerify readings\nCheck for abnormal conditions',
                    },
                ],
            },
            'inspection': {
                'category_name': 'Inspection',
                'templates': [
                    {
                        'name': 'Weekly Visual Inspection',
                        'description': 'Weekly visual inspection for early problem detection',
                        'estimated_duration_hours': 0.5,
                        'frequency_days': 7,
                        'is_mandatory': False,
                        'default_tools_required': 'Flashlight, inspection checklist',
                        'default_safety_notes': 'No special safety requirements',
                        'checklist_template': 'Check for leaks\nInspect for damage\nVerify proper operation\nCheck cleanliness\nNote any unusual conditions',
                    },
                ],
            },
            'cleaning': {
                'category_name': 'Cleaning',
                'templates': [
                    {
                        'name': 'Quarterly Deep Clean',
                        'description': 'Thorough cleaning and decontamination',
                        'estimated_duration_hours': 2,
                        'frequency_days': 90,
                        'is_mandatory': False,
                        'default_tools_required': 'Cleaning supplies, brushes, rags, vacuum',
                        'default_parts_required': 'Cleaning chemicals, filters (if applicable)',
                        'default_safety_notes': 'Use appropriate PPE, ensure proper ventilation',
                        'checklist_template': 'Remove dust and debris\nClean all surfaces\nReplace filters if needed\nCheck for corrosion\nApply protective coatings if needed',
                    },
                ],
            },
        }
        
        # Create templates for each equipment category
        for equipment_category in equipment_categories:
            self.stdout.write(f'  Creating templates for {equipment_category.name}...')
            
            for pattern_key, pattern_data in template_patterns.items():
                try:
                    activity_category = activity_categories.get(name=pattern_data['category_name'])
                    
                    for template_data in pattern_data['templates']:
                        template_name = f"{equipment_category.name} - {template_data['name']}"
                        
                        template, created = ActivityTypeTemplate.objects.get_or_create(
                            name=template_name,
                            equipment_category=equipment_category,
                            defaults={
                                'category': activity_category,
                                'description': template_data['description'],
                                'estimated_duration_hours': template_data['estimated_duration_hours'],
                                'frequency_days': template_data['frequency_days'],
                                'is_mandatory': template_data['is_mandatory'],
                                'default_tools_required': template_data['default_tools_required'],
                                'default_parts_required': template_data.get('default_parts_required', ''),
                                'default_safety_notes': template_data['default_safety_notes'],
                                'checklist_template': template_data['checklist_template'],
                                'sort_order': 0,
                            }
                        )
                        
                        if created:
                            self.stdout.write(f'    Created template: {template_name}')
                        else:
                            self.stdout.write(f'    Template already exists: {template_name}')
                            
                except ActivityTypeCategory.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'    Category "{pattern_data["category_name"]}" not found')
                    )
                    continue

    def create_sample_activity_types(self):
        """Create some sample activity types from templates."""
        self.stdout.write('Creating sample activity types...')
        
        # Get some templates to create activity types from
        templates = ActivityTypeTemplate.objects.all()[:5]  # Just create a few samples
        
        for template in templates:
            activity_type_name = f"{template.name} (Sample)"
            
            # Check if activity type already exists
            if MaintenanceActivityType.objects.filter(name=activity_type_name).exists():
                continue
            
            activity_type = MaintenanceActivityType.objects.create(
                name=activity_type_name,
                category=template.category,
                template=template,
                description=template.description,
                estimated_duration_hours=template.estimated_duration_hours,
                frequency_days=template.frequency_days,
                is_mandatory=template.is_mandatory,
                tools_required=template.default_tools_required,
                parts_required=template.default_parts_required,
                safety_notes=template.default_safety_notes,
            )
            
            # Add equipment category association
            activity_type.applicable_equipment_categories.add(template.equipment_category)
            
            self.stdout.write(f'  Created activity type: {activity_type_name}')