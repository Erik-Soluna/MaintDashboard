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
                'Thermal Imaging',
                'Operational inspection',
                'Visual Inspection',
                'Corrective Maintenance',
                '3 Year Torque Check',
                'Annual Torque Check',
                'DGA Sample',
                # Legacy names (keep for backward compatibility)
                'PM-001', 'PM-002', 'PM-003', 'PM-004', 'PM-005',
                'INS-001', 'INS-002', 'INS-003',
                'CAL-001', 'CAL-002',
                'COR-001', 'COR-002',
                'SAF-001', 'SAF-002',
                'General Maintenance'
            ]
            
            deleted_count = MaintenanceActivityType.objects.filter(name__in=default_names).delete()[0]
            self.stdout.write(f'  Deleted {deleted_count} default activity types')
            
            # Delete default categories (including duplicates)
            default_categories = [
                'Preventive', 'Preventive Maintenance',
                'Corrective', 'Corrective Maintenance',
                'Inspection', 'Calibration', 'Testing', 'Safety'
            ]
            
            deleted_categories = ActivityTypeCategory.objects.filter(name__in=default_categories).delete()[0]
            self.stdout.write(f'  Deleted {deleted_categories} default categories')
            
        except ImportError:
            self.stdout.write(self.style.WARNING('Maintenance app not available, skipping clear operation'))

    def ensure_default_categories(self, admin_user):
        """Ensure default activity type categories exist and merge duplicates."""
        try:
            from maintenance.models import ActivityTypeCategory, MaintenanceActivityType
            
            # Map of duplicate short names to full names
            duplicate_map = {
                'Preventive': 'Preventive Maintenance',
                'Corrective': 'Corrective Maintenance',
            }
            
            # First, handle duplicate categories - merge or rename as needed
            for short_name, full_name in duplicate_map.items():
                short_cat = ActivityTypeCategory.objects.filter(name=short_name).first()
                full_cat = ActivityTypeCategory.objects.filter(name=full_name).first()
                
                if short_cat and full_cat:
                    # Both exist - merge short into full
                    self.stdout.write(f'  Merging duplicate category "{short_name}" into "{full_name}"')
                    # Update all activity types using the short category
                    MaintenanceActivityType.objects.filter(category=short_cat).update(category=full_cat)
                    # Delete the short category
                    short_cat.delete()
                    self.stdout.write(f'    Merged and deleted "{short_name}"')
                elif short_cat and not full_cat:
                    # Only short exists - rename it to full
                    self.stdout.write(f'  Renaming category "{short_name}" to "{full_name}"')
                    short_cat.name = full_name
                    short_cat.save()
                    self.stdout.write(f'    Renamed "{short_name}" to "{full_name}"')
            
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
                    'name': 'Testing',
                    'description': 'Functional and performance testing activities',
                    'color': '#6f42c1',
                    'icon': 'fas fa-flask',
                    'sort_order': 5,
                },
                {
                    'name': 'Safety',
                    'description': 'Safety-related activities',
                    'color': '#fd7e14',
                    'icon': 'fas fa-shield-alt',
                    'sort_order': 6,
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
                # Update existing category if it was renamed from a short name
                if not created:
                    # Update properties to ensure consistency
                    category.description = data['description']
                    category.color = data['color']
                    category.icon = data['icon']
                    category.sort_order = data['sort_order']
                    category.is_active = True
                    category.is_global = True
                    if not category.created_by:
                        category.created_by = admin_user
                    category.save()
                
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
                {
                    'name': 'Thermal Imaging',
                    'category': categories.get('Preventive Maintenance'),
                    'description': 'Thermal imaging inspection for preventive maintenance',
                    'estimated_duration_hours': 1,
                    'frequency_days': 365,
                    'is_mandatory': True,
                    'tools_required': 'Thermal imaging camera',
                    'parts_required': 'None',
                    'safety_notes': 'Follow thermal imaging safety procedures',
                },
                {
                    'name': 'Operational inspection',
                    'category': categories.get('Inspection'),
                    'description': 'Annual operational inspection',
                    'estimated_duration_hours': 2,
                    'frequency_days': 365,
                    'is_mandatory': True,
                    'tools_required': 'Inspection checklist, basic tools',
                    'parts_required': 'None',
                    'safety_notes': 'Operational safety procedures',
                },
                {
                    'name': 'Visual Inspection',
                    'category': categories.get('Inspection'),
                    'description': 'Monthly visual inspection',
                    'estimated_duration_hours': 1,
                    'frequency_days': 30,
                    'is_mandatory': True,
                    'tools_required': 'Visual inspection tools',
                    'parts_required': 'None',
                    'safety_notes': 'Visual inspection only, no physical contact required',
                },
                {
                    'name': 'Corrective Maintenance',
                    'category': categories.get('Corrective Maintenance'),
                    'description': 'Corrective maintenance and repair activities',
                    'estimated_duration_hours': 2,
                    'frequency_days': 1,
                    'is_mandatory': False,
                    'tools_required': 'Repair tools as needed',
                    'parts_required': 'Replacement parts as needed',
                    'safety_notes': 'Standard repair safety procedures',
                },
                {
                    'name': '3 Year Torque Check',
                    'category': categories.get('Calibration'),
                    'description': 'Three-year torque calibration check',
                    'estimated_duration_hours': 1,
                    'frequency_days': 1095,
                    'is_mandatory': True,
                    'tools_required': 'Torque wrench, calibration equipment',
                    'parts_required': 'Calibration standards',
                    'safety_notes': 'Precision work area required',
                },
                {
                    'name': 'Annual Torque Check',
                    'category': categories.get('Calibration'),
                    'description': 'Annual torque calibration check',
                    'estimated_duration_hours': 1,
                    'frequency_days': 365,
                    'is_mandatory': True,
                    'tools_required': 'Torque wrench, calibration equipment',
                    'parts_required': 'Calibration standards',
                    'safety_notes': 'Precision work area required',
                },
                {
                    'name': 'DGA Sample',
                    'category': categories.get('Testing'),
                    'description': 'Dissolved Gas Analysis sample collection',
                    'estimated_duration_hours': 2,
                    'frequency_days': 365,
                    'is_mandatory': True,
                    'tools_required': 'DGA sampling equipment',
                    'parts_required': 'Sample containers',
                    'safety_notes': 'Follow DGA sampling safety procedures',
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