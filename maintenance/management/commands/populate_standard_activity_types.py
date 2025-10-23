"""
Management command to populate standard activity types for maintenance.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from maintenance.models import ActivityTypeCategory, MaintenanceActivityType
from core.models import EquipmentCategory


class Command(BaseCommand):
    help = 'Populate database with standard activity types and categories'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force creation even if activity types already exist',
        )

    def handle(self, *args, **options):
        force = options['force']
        
        self.stdout.write('Starting to populate standard activity types...')
        
        # Check if activity types already exist
        existing_count = MaintenanceActivityType.objects.count()
        if existing_count > 0 and not force:
            self.stdout.write(
                self.style.WARNING(f'Found {existing_count} existing activity types. Use --force to recreate.')
            )
            return
        
        # Get or create admin user
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={'is_staff': True, 'is_superuser': True}
        )
        
        # Create activity type categories
        categories = self.create_categories()
        
        # Create standard activity types
        self.create_activity_types(categories)
        
        self.stdout.write(
            self.style.SUCCESS('Successfully populated standard activity types!')
        )

    def create_categories(self):
        """Create standard activity type categories."""
        categories_data = [
            {
                'name': 'Inspection',
                'description': 'Visual and testing checks to assess equipment condition',
                'color': '#17a2b8',
                'icon': 'fas fa-search',
                'sort_order': 1,
            },
            {
                'name': 'Preventive Maintenance',
                'description': 'Regular preventive maintenance activities to prevent equipment failure',
                'color': '#28a745',
                'icon': 'fas fa-shield-alt',
                'sort_order': 2,
            },
            {
                'name': 'Emergency Maintenance',
                'description': 'Urgent repair and corrective actions for equipment issues',
                'color': '#dc3545',
                'icon': 'fas fa-exclamation-triangle',
                'sort_order': 3,
            },
            {
                'name': 'Testing',
                'description': 'Functional and performance testing activities',
                'color': '#ffc107',
                'icon': 'fas fa-flask',
                'sort_order': 4,
            },
            {
                'name': 'Calibration',
                'description': 'Equipment calibration and measurement verification',
                'color': '#6f42c1',
                'icon': 'fas fa-balance-scale',
                'sort_order': 5,
            },
            {
                'name': 'Cleaning',
                'description': 'Cleaning and housekeeping activities',
                'color': '#fd7e14',
                'icon': 'fas fa-broom',
                'sort_order': 6,
            },
        ]
        
        categories = {}
        for data in categories_data:
            category, created = ActivityTypeCategory.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            categories[data['name']] = category
            if created:
                self.stdout.write(f'  Created category: {category.name}')
            else:
                self.stdout.write(f'  Category already exists: {category.name}')
        
        return categories

    def create_activity_types(self, categories):
        """Create standard activity types."""
        activity_types_data = [
            # Inspection
            {
                'name': 'Routine Inspection',
                'category': categories['Inspection'],
                'description': 'Regular visual inspection of equipment condition and operation',
                'estimated_duration_hours': 1,
                'frequency_days': 7,
                'is_mandatory': True,
                'tools_required': 'Flashlight, inspection checklist',
                'parts_required': 'None',
                'safety_notes': 'Follow lockout/tagout procedures, wear appropriate PPE',
            },
            {
                'name': 'Safety Inspection',
                'category': categories['Inspection'],
                'description': 'Comprehensive safety inspection of equipment and surrounding area',
                'estimated_duration_hours': 2,
                'frequency_days': 30,
                'is_mandatory': True,
                'tools_required': 'Safety inspection checklist, measuring tools',
                'parts_required': 'Safety labels, warning signs (as needed)',
                'safety_notes': 'Equipment must be de-energized, follow all safety protocols',
            },
            {
                'name': 'Thermal Inspection',
                'category': categories['Inspection'],
                'description': 'Infrared thermal imaging inspection for hot spots and anomalies',
                'estimated_duration_hours': 3,
                'frequency_days': 90,
                'is_mandatory': False,
                'tools_required': 'Thermal imaging camera, inspection checklist',
                'parts_required': 'None',
                'safety_notes': 'Maintain safe distance, equipment can remain energized',
            },
            
            # Preventive Maintenance
            {
                'name': 'Oil Analysis',
                'category': categories['Preventive Maintenance'],
                'description': 'Oil sampling and analysis for contamination and degradation',
                'estimated_duration_hours': 1,
                'frequency_days': 90,
                'is_mandatory': True,
                'tools_required': 'Oil sampling kit, labels',
                'parts_required': 'Oil sample containers',
                'safety_notes': 'Follow proper sampling procedures, avoid contamination',
            },
            {
                'name': 'Filter Replacement',
                'category': categories['Preventive Maintenance'],
                'description': 'Replace air, oil, and fuel filters as per schedule',
                'estimated_duration_hours': 2,
                'frequency_days': 180,
                'is_mandatory': True,
                'tools_required': 'Basic hand tools, filter wrench',
                'parts_required': 'Replacement filters, gaskets',
                'safety_notes': 'De-energize equipment, follow lockout procedures',
            },
            {
                'name': 'Lubrication',
                'category': categories['Preventive Maintenance'],
                'description': 'Apply lubricants to moving parts and bearings',
                'estimated_duration_hours': 1,
                'frequency_days': 30,
                'is_mandatory': True,
                'tools_required': 'Grease gun, cleaning supplies',
                'parts_required': 'Appropriate lubricants',
                'safety_notes': 'Clean area before lubrication, use correct lubricant type',
            },
            
            # Emergency Maintenance
            {
                'name': 'Emergency Repair',
                'category': categories['Emergency Maintenance'],
                'description': 'Urgent repair to restore equipment operation',
                'estimated_duration_hours': 4,
                'frequency_days': 0,
                'is_mandatory': True,
                'tools_required': 'Emergency tool kit, diagnostic equipment',
                'parts_required': 'Emergency spare parts',
                'safety_notes': 'Follow emergency procedures, prioritize safety over speed',
            },
            {
                'name': 'Component Replacement',
                'category': categories['Emergency Maintenance'],
                'description': 'Replace failed or damaged components',
                'estimated_duration_hours': 6,
                'frequency_days': 0,
                'is_mandatory': True,
                'tools_required': 'Complete tool set, lifting equipment',
                'parts_required': 'Replacement components',
                'safety_notes': 'Equipment must be de-energized, use proper lifting techniques',
            },
            {
                'name': 'System Restoration',
                'category': categories['Emergency Maintenance'],
                'description': 'Restore system operation after failure',
                'estimated_duration_hours': 8,
                'frequency_days': 0,
                'is_mandatory': True,
                'tools_required': 'Complete tool set, testing equipment',
                'parts_required': 'System components, cables, connectors',
                'safety_notes': 'Follow system restoration procedures, test thoroughly',
            },
            
            # Testing
            {
                'name': 'Load Testing',
                'category': categories['Testing'],
                'description': 'Test equipment under various load conditions',
                'estimated_duration_hours': 4,
                'frequency_days': 365,
                'is_mandatory': True,
                'tools_required': 'Load testing equipment, monitoring devices',
                'parts_required': 'Test loads, connection cables',
                'safety_notes': 'Monitor equipment closely, follow load testing procedures',
            },
            {
                'name': 'Performance Testing',
                'category': categories['Testing'],
                'description': 'Evaluate equipment performance parameters',
                'estimated_duration_hours': 3,
                'frequency_days': 180,
                'is_mandatory': False,
                'tools_required': 'Performance monitoring equipment',
                'parts_required': 'None',
                'safety_notes': 'Document all measurements, compare with specifications',
            },
            {
                'name': 'Insulation Testing',
                'category': categories['Testing'],
                'description': 'Test electrical insulation resistance and integrity',
                'estimated_duration_hours': 2,
                'frequency_days': 365,
                'is_mandatory': True,
                'tools_required': 'Insulation resistance tester, test leads',
                'parts_required': 'None',
                'safety_notes': 'Equipment must be de-energized, follow testing procedures',
            },
            
            # Calibration
            {
                'name': 'Instrument Calibration',
                'category': categories['Calibration'],
                'description': 'Calibrate measurement instruments and sensors',
                'estimated_duration_hours': 2,
                'frequency_days': 365,
                'is_mandatory': True,
                'tools_required': 'Calibration equipment, reference standards',
                'parts_required': 'Calibration certificates',
                'safety_notes': 'Use traceable standards, document calibration results',
            },
            {
                'name': 'System Calibration',
                'category': categories['Calibration'],
                'description': 'Calibrate entire system for optimal performance',
                'estimated_duration_hours': 4,
                'frequency_days': 365,
                'is_mandatory': True,
                'tools_required': 'System calibration equipment, software',
                'parts_required': 'Calibration standards, documentation',
                'safety_notes': 'Follow system calibration procedures, verify accuracy',
            },
            
            # Cleaning
            {
                'name': 'Equipment Cleaning',
                'category': categories['Cleaning'],
                'description': 'Clean equipment surfaces and components',
                'estimated_duration_hours': 1,
                'frequency_days': 30,
                'is_mandatory': False,
                'tools_required': 'Cleaning supplies, brushes, rags',
                'parts_required': 'Cleaning solutions, protective coatings',
                'safety_notes': 'Use appropriate cleaning agents, protect electrical components',
            },
            {
                'name': 'Area Cleaning',
                'category': categories['Cleaning'],
                'description': 'Clean equipment area and remove debris',
                'estimated_duration_hours': 1,
                'frequency_days': 7,
                'is_mandatory': False,
                'tools_required': 'Cleaning supplies, vacuum, broom',
                'parts_required': 'Cleaning solutions, trash bags',
                'safety_notes': 'Maintain clear access paths, dispose of waste properly',
            },
        ]
        
        for data in activity_types_data:
            activity_type, created = MaintenanceActivityType.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            if created:
                self.stdout.write(f'  Created activity type: {activity_type.name}')
            else:
                self.stdout.write(f'  Activity type already exists: {activity_type.name}')
