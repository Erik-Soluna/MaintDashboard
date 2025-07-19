"""
Ensure default activity types exist in the database.
This command checks for default activity types and creates them if missing.
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Ensure default activity types exist in the database'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating data',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of all default activity types (will delete existing ones)',
        )

    def handle(self, *args, **options):
        if options['dry_run']:
            self.stdout.write(
                self.style.SUCCESS('DRY RUN: Would ensure default activity types:')
            )
            self.stdout.write('  - Checking for default categories')
            self.stdout.write('  - Checking for default activity types')
            if options['force']:
                self.stdout.write('  - Force recreation: YES (would delete existing)')
            return
            
        self.stdout.write(
            self.style.SUCCESS('Ensuring default activity types exist...')
        )
        
        try:
            with transaction.atomic():
                # Get or create admin user for created_by field
                admin_user = User.objects.filter(is_superuser=True).first()
                if not admin_user:
                    admin_user = User.objects.filter(is_staff=True).first()
                if not admin_user:
                    self.stdout.write(self.style.WARNING('No admin user found, using first user'))
                    admin_user = User.objects.first()
                
                if options['force']:
                    self.stdout.write('Force mode: Clearing existing default activity types...')
                    self.clear_default_activity_types()
                
                # Ensure default categories exist
                categories = self.ensure_default_categories(admin_user)
                
                # Ensure default activity types exist
                activity_types = self.ensure_default_activity_types(categories, admin_user)
                
                self.stdout.write(
                    self.style.SUCCESS('Default activity types ensured successfully!')
                )
                self.stdout.write(f'  Categories: {len(categories)}')
                self.stdout.write(f'  Activity Types: {len(activity_types)}')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error ensuring default activity types: {str(e)}')
            )
            raise CommandError(f'Operation failed: {str(e)}')

    def clear_default_activity_types(self):
        """Clear existing default activity types and categories."""
        try:
            from maintenance.models import MaintenanceActivityType, ActivityTypeCategory
            
            # Delete activity types with default names
            default_names = [
                'PM-001', 'PM-002', 'PM-003', 'PM-004', 'PM-005',
                'INS-001', 'INS-002', 'INS-003',
                'CAL-001', 'CAL-002',
                'COR-001', 'COR-002',
                'SAF-001', 'SAF-002',
                'General Maintenance'
            ]
            
            deleted_count = MaintenanceActivityType.objects.filter(name__in=default_names).delete()[0]
            self.stdout.write(f'  Deleted {deleted_count} default activity types')
            
            # Delete default categories
            default_categories = [
                'Preventive Maintenance', 'Corrective Maintenance', 
                'Inspection', 'Calibration', 'Safety'
            ]
            
            deleted_categories = ActivityTypeCategory.objects.filter(name__in=default_categories).delete()[0]
            self.stdout.write(f'  Deleted {deleted_categories} default categories')
            
        except ImportError:
            self.stdout.write(self.style.WARNING('Maintenance app not available, skipping clear operation'))

    def ensure_default_categories(self, admin_user):
        """Ensure default activity type categories exist."""
        try:
            from maintenance.models import ActivityTypeCategory
            
            categories_data = [
                {
                    'name': 'Preventive Maintenance',
                    'description': 'Regular preventive maintenance activities',
                    'color': '#28a745',
                    'icon': 'fas fa-tools',
                    'sort_order': 1,
                },
                {
                    'name': 'Corrective Maintenance',
                    'description': 'Corrective and repair activities',
                    'color': '#dc3545',
                    'icon': 'fas fa-wrench',
                    'sort_order': 2,
                },
                {
                    'name': 'Inspection',
                    'description': 'Inspection and testing activities',
                    'color': '#17a2b8',
                    'icon': 'fas fa-search',
                    'sort_order': 3,
                },
                {
                    'name': 'Calibration',
                    'description': 'Calibration and measurement activities',
                    'color': '#ffc107',
                    'icon': 'fas fa-balance-scale',
                    'sort_order': 4,
                },
                {
                    'name': 'Safety',
                    'description': 'Safety-related activities',
                    'color': '#fd7e14',
                    'icon': 'fas fa-shield-alt',
                    'sort_order': 5,
                },
            ]
            
            categories = {}
            for data in categories_data:
                category, created = ActivityTypeCategory.objects.get_or_create(
                    name=data['name'],
                    defaults={
                        'description': data['description'],
                        'color': data['color'],
                        'icon': data['icon'],
                        'sort_order': data['sort_order'],
                        'is_active': True,
                        'is_global': True,
                        'created_by': admin_user,
                    }
                )
                categories[data['name']] = category
                if created:
                    self.stdout.write(f'  Created category: {category.name}')
                else:
                    self.stdout.write(f'  Category already exists: {category.name}')
            
            return categories
            
        except ImportError:
            self.stdout.write(self.style.WARNING('Maintenance app not available, skipping categories'))
            return {}

    def ensure_default_activity_types(self, categories, admin_user):
        """Ensure default activity types exist."""
        try:
            from maintenance.models import MaintenanceActivityType
            
            activity_types_data = [
                # Preventive Maintenance
                {
                    'name': 'PM-001',
                    'category': categories.get('Preventive Maintenance'),
                    'description': 'Regular preventive maintenance inspection and service',
                    'estimated_duration_hours': 4,
                    'frequency_days': 90,
                    'is_mandatory': True,
                    'tools_required': 'Basic hand tools, inspection equipment',
                    'parts_required': 'Lubricants, filters (as needed)',
                    'safety_notes': 'Follow lockout/tagout procedures, wear appropriate PPE',
                },
                {
                    'name': 'PM-002',
                    'category': categories.get('Preventive Maintenance'),
                    'description': 'Annual comprehensive maintenance and inspection',
                    'estimated_duration_hours': 8,
                    'frequency_days': 365,
                    'is_mandatory': True,
                    'tools_required': 'Complete tool set, testing equipment',
                    'parts_required': 'Complete maintenance kit, replacement parts',
                    'safety_notes': 'Full lockout/tagout, safety briefing required',
                },
                {
                    'name': 'PM-003',
                    'category': categories.get('Preventive Maintenance'),
                    'description': 'Quarterly lubrication and minor adjustments',
                    'estimated_duration_hours': 2,
                    'frequency_days': 90,
                    'is_mandatory': True,
                    'tools_required': 'Lubrication equipment, adjustment tools',
                    'parts_required': 'Lubricants, gaskets',
                    'safety_notes': 'Ensure equipment is properly isolated',
                },
                {
                    'name': 'PM-004',
                    'category': categories.get('Preventive Maintenance'),
                    'description': 'Monthly visual inspection and cleaning',
                    'estimated_duration_hours': 1,
                    'frequency_days': 30,
                    'is_mandatory': False,
                    'tools_required': 'Cleaning supplies, inspection tools',
                    'parts_required': 'Cleaning materials',
                    'safety_notes': 'Basic safety precautions',
                },
                {
                    'name': 'PM-005',
                    'category': categories.get('Preventive Maintenance'),
                    'description': 'Weekly operational check and basic cleaning',
                    'estimated_duration_hours': 0.5,
                    'frequency_days': 7,
                    'is_mandatory': False,
                    'tools_required': 'Basic cleaning supplies',
                    'parts_required': 'None',
                    'safety_notes': 'Standard operational safety',
                },
                
                # Inspection
                {
                    'name': 'INS-001',
                    'category': categories.get('Inspection'),
                    'description': 'Monthly operational inspection',
                    'estimated_duration_hours': 1,
                    'frequency_days': 30,
                    'is_mandatory': True,
                    'tools_required': 'Inspection checklist, basic tools',
                    'parts_required': 'None',
                    'safety_notes': 'Operational safety procedures',
                },
                {
                    'name': 'INS-002',
                    'category': categories.get('Inspection'),
                    'description': 'Quarterly detailed inspection',
                    'estimated_duration_hours': 4,
                    'frequency_days': 90,
                    'is_mandatory': True,
                    'tools_required': 'Detailed inspection equipment',
                    'parts_required': 'Inspection materials',
                    'safety_notes': 'Full safety procedures required',
                },
                {
                    'name': 'INS-003',
                    'category': categories.get('Inspection'),
                    'description': 'Annual comprehensive inspection',
                    'estimated_duration_hours': 8,
                    'frequency_days': 365,
                    'is_mandatory': True,
                    'tools_required': 'Complete inspection suite',
                    'parts_required': 'Inspection materials, test equipment',
                    'safety_notes': 'Comprehensive safety briefing required',
                },
                
                # Calibration
                {
                    'name': 'CAL-001',
                    'category': categories.get('Calibration'),
                    'description': 'Semi-annual calibration check',
                    'estimated_duration_hours': 3,
                    'frequency_days': 180,
                    'is_mandatory': True,
                    'tools_required': 'Calibration equipment, standards',
                    'parts_required': 'Calibration materials',
                    'safety_notes': 'Precision work area required',
                },
                {
                    'name': 'CAL-002',
                    'category': categories.get('Calibration'),
                    'description': 'Annual full calibration',
                    'estimated_duration_hours': 6,
                    'frequency_days': 365,
                    'is_mandatory': True,
                    'tools_required': 'Full calibration suite',
                    'parts_required': 'Calibration standards, materials',
                    'safety_notes': 'Controlled environment required',
                },
                
                # Corrective Maintenance
                {
                    'name': 'COR-001',
                    'category': categories.get('Corrective Maintenance'),
                    'description': 'Minor repair and adjustment',
                    'estimated_duration_hours': 2,
                    'frequency_days': 0,  # As needed
                    'is_mandatory': False,
                    'tools_required': 'Basic repair tools',
                    'parts_required': 'Replacement parts as needed',
                    'safety_notes': 'Standard repair safety procedures',
                },
                {
                    'name': 'COR-002',
                    'category': categories.get('Corrective Maintenance'),
                    'description': 'Major repair or component replacement',
                    'estimated_duration_hours': 8,
                    'frequency_days': 0,  # As needed
                    'is_mandatory': False,
                    'tools_required': 'Complete repair tool set',
                    'parts_required': 'Major components, replacement parts',
                    'safety_notes': 'Comprehensive safety procedures required',
                },
                
                # Safety
                {
                    'name': 'SAF-001',
                    'category': categories.get('Safety'),
                    'description': 'Safety system inspection and testing',
                    'estimated_duration_hours': 2,
                    'frequency_days': 90,
                    'is_mandatory': True,
                    'tools_required': 'Safety testing equipment',
                    'parts_required': 'Safety system components',
                    'safety_notes': 'Critical safety procedures must be followed',
                },
                {
                    'name': 'SAF-002',
                    'category': categories.get('Safety'),
                    'description': 'Emergency system verification',
                    'estimated_duration_hours': 4,
                    'frequency_days': 180,
                    'is_mandatory': True,
                    'tools_required': 'Emergency system test equipment',
                    'parts_required': 'Emergency system components',
                    'safety_notes': 'Emergency procedures must be in place',
                },
            ]
            
            activity_types = []
            for data in activity_types_data:
                if not data['category']:
                    self.stdout.write(self.style.WARNING(f'Skipping {data["name"]} - category not found'))
                    continue
                
                activity_type, created = MaintenanceActivityType.objects.get_or_create(
                    name=data['name'],
                    defaults={
                        'category': data['category'],
                        'description': data['description'],
                        'estimated_duration_hours': data['estimated_duration_hours'],
                        'frequency_days': data['frequency_days'],
                        'is_mandatory': data['is_mandatory'],
                        'is_active': True,
                        'tools_required': data['tools_required'],
                        'parts_required': data['parts_required'],
                        'safety_notes': data['safety_notes'],
                        'created_by': admin_user,
                    }
                )
                activity_types.append(activity_type)
                if created:
                    self.stdout.write(f'  Created activity type: {activity_type.name} - {activity_type.description}')
                else:
                    self.stdout.write(f'  Activity type already exists: {activity_type.name}')
            
            return activity_types
            
        except ImportError:
            self.stdout.write(self.style.WARNING('Maintenance app not available, skipping activity types'))
            return [] 