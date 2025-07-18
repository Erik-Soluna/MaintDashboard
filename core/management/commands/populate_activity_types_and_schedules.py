"""
Populate activity types and basic scheduling data.
This command creates activity types based on the hardcoded event types and sets up basic scheduling.
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
import random
import logging

from core.models import EquipmentCategory, Location
from equipment.models import Equipment
from maintenance.models import (
    ActivityTypeCategory, ActivityTypeTemplate, MaintenanceActivityType,
    MaintenanceActivity, EquipmentCategorySchedule, GlobalSchedule
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Populate activity types based on event types and create basic scheduling data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Clear existing activity types and schedules before populating',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating data',
        )

    def handle(self, *args, **options):
        if options['dry_run']:
            self.stdout.write(
                self.style.SUCCESS('DRY RUN: Would populate activity types and schedules:')
            )
            self.stdout.write('  - Activity Type Categories')
            self.stdout.write('  - Activity Types (based on event types)')
            self.stdout.write('  - Basic Category Schedules')
            self.stdout.write('  - Basic Global Schedules')
            if options['reset']:
                self.stdout.write('  - Reset existing data: YES')
            return
            
        self.stdout.write(
            self.style.SUCCESS('Starting activity types and schedules population...')
        )
        
        try:
            with transaction.atomic():
                if options['reset']:
                    self.stdout.write('Clearing existing activity types and schedules...')
                    self.clear_existing_data()
                
                # Step 1: Create activity type categories
                self.stdout.write('Creating activity type categories...')
                categories = self.create_activity_type_categories()
                
                # Step 2: Create activity types based on event types
                self.stdout.write('Creating activity types...')
                activity_types = self.create_activity_types(categories)
                
                # Step 3: Create basic category schedules
                self.stdout.write('Creating category schedules...')
                self.create_category_schedules(activity_types)
                
                # Step 4: Create basic global schedules
                self.stdout.write('Creating global schedules...')
                self.create_global_schedules(activity_types)
                
                self.stdout.write(
                    self.style.SUCCESS('Activity types and schedules population completed successfully!')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during population: {str(e)}')
            )
            raise CommandError(f'Population failed: {str(e)}')

    def clear_existing_data(self):
        """Clear existing activity types and schedules."""
        EquipmentCategorySchedule.objects.all().delete()
        GlobalSchedule.objects.all().delete()
        MaintenanceActivity.objects.all().delete()
        MaintenanceActivityType.objects.all().delete()
        ActivityTypeTemplate.objects.all().delete()
        ActivityTypeCategory.objects.all().delete()

    def create_activity_type_categories(self):
        """Create activity type categories."""
        categories_data = [
            {
                'name': 'Preventive Maintenance',
                'description': 'Regular maintenance activities to prevent equipment failure',
                'color': '#28a745',
                'icon': 'fas fa-shield-alt',
                'sort_order': 1,
            },
            {
                'name': 'Corrective Maintenance',
                'description': 'Repair and corrective actions for equipment issues',
                'color': '#dc3545',
                'icon': 'fas fa-tools',
                'sort_order': 2,
            },
            {
                'name': 'Inspection & Testing',
                'description': 'Regular inspections and testing procedures',
                'color': '#17a2b8',
                'icon': 'fas fa-search',
                'sort_order': 3,
            },
            {
                'name': 'Calibration',
                'description': 'Equipment calibration and measurement verification',
                'color': '#ffc107',
                'icon': 'fas fa-balance-scale',
                'sort_order': 4,
            },
            {
                'name': 'Equipment Management',
                'description': 'Equipment commissioning, decommissioning, and upgrades',
                'color': '#6f42c1',
                'icon': 'fas fa-cogs',
                'sort_order': 5,
            },
            {
                'name': 'Other Activities',
                'description': 'Miscellaneous maintenance and operational activities',
                'color': '#6c757d',
                'icon': 'fas fa-ellipsis-h',
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
        """Create activity types based on the hardcoded event types."""
        activity_types_data = [
            # Preventive Maintenance
            {
                'name': 'PM-001',
                'category': categories['Preventive Maintenance'],
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
                'category': categories['Preventive Maintenance'],
                'description': 'Comprehensive preventive maintenance overhaul',
                'estimated_duration_hours': 8,
                'frequency_days': 365,
                'is_mandatory': True,
                'tools_required': 'Complete tool set, testing equipment',
                'parts_required': 'Complete maintenance kit, replacement parts',
                'safety_notes': 'Equipment must be completely de-energized, follow safety protocols',
            },
            
            # Inspection & Testing
            {
                'name': 'INS-001',
                'category': categories['Inspection & Testing'],
                'description': 'Regular equipment inspection and condition assessment',
                'estimated_duration_hours': 2,
                'frequency_days': 30,
                'is_mandatory': True,
                'tools_required': 'Inspection tools, measurement devices',
                'parts_required': 'None',
                'safety_notes': 'Visual inspection only, no disassembly required',
            },
            {
                'name': 'TEST-001',
                'category': categories['Inspection & Testing'],
                'description': 'Functional testing and performance verification',
                'estimated_duration_hours': 3,
                'frequency_days': 60,
                'is_mandatory': True,
                'tools_required': 'Testing equipment, measurement devices',
                'parts_required': 'Test materials (if required)',
                'safety_notes': 'Follow testing procedures, monitor equipment during testing',
            },
            
            # Calibration
            {
                'name': 'CAL-001',
                'category': categories['Calibration'],
                'description': 'Equipment calibration and measurement verification',
                'estimated_duration_hours': 2,
                'frequency_days': 180,
                'is_mandatory': True,
                'tools_required': 'Calibration standards, measurement equipment',
                'parts_required': 'Calibration materials',
                'safety_notes': 'Handle calibration equipment carefully, follow calibration procedures',
            },
            
            # Corrective Maintenance
            {
                'name': 'CM-001',
                'category': categories['Corrective Maintenance'],
                'description': 'Repair and corrective maintenance for equipment issues',
                'estimated_duration_hours': 6,
                'frequency_days': 0,  # As needed
                'is_mandatory': False,
                'tools_required': 'Repair tools, diagnostic equipment',
                'parts_required': 'Replacement parts (as identified)',
                'safety_notes': 'Follow repair procedures, ensure proper isolation',
            },
            
            # Equipment Management
            {
                'name': 'EQ-001',
                'category': categories['Equipment Management'],
                'description': 'Equipment commissioning and initial setup',
                'estimated_duration_hours': 8,
                'frequency_days': 0,  # One-time
                'is_mandatory': True,
                'tools_required': 'Installation tools, testing equipment',
                'parts_required': 'Installation materials, initial supplies',
                'safety_notes': 'Follow installation procedures, verify all connections',
            },
            {
                'name': 'EQ-002',
                'category': categories['Equipment Management'],
                'description': 'Equipment upgrade and modification',
                'estimated_duration_hours': 12,
                'frequency_days': 0,  # As needed
                'is_mandatory': False,
                'tools_required': 'Upgrade tools, testing equipment',
                'parts_required': 'Upgrade components, new parts',
                'safety_notes': 'Complete system shutdown required, follow upgrade procedures',
            },
            {
                'name': 'EQ-003',
                'category': categories['Equipment Management'],
                'description': 'Equipment decommissioning and removal',
                'estimated_duration_hours': 6,
                'frequency_days': 0,  # One-time
                'is_mandatory': True,
                'tools_required': 'Removal tools, safety equipment',
                'parts_required': 'None',
                'safety_notes': 'Complete de-energization required, follow removal procedures',
            },
            
            # Other Activities
            {
                'name': 'OTH-001',
                'category': categories['Other Activities'],
                'description': 'Equipment outage and shutdown procedures',
                'estimated_duration_hours': 4,
                'frequency_days': 0,  # As needed
                'is_mandatory': False,
                'tools_required': 'Shutdown tools, safety equipment',
                'parts_required': 'None',
                'safety_notes': 'Follow shutdown procedures, ensure proper isolation',
            },
        ]
        
        activity_types = {}
        for data in activity_types_data:
            activity_type, created = MaintenanceActivityType.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            activity_types[data['name']] = activity_type
            if created:
                self.stdout.write(f'  Created activity type: {activity_type.name} - {activity_type.description}')
            else:
                self.stdout.write(f'  Activity type already exists: {activity_type.name}')
        
        return activity_types

    def create_category_schedules(self, activity_types):
        """Create basic category schedules."""
        # Get equipment categories
        equipment_categories = EquipmentCategory.objects.all()
        if not equipment_categories.exists():
            self.stdout.write(self.style.WARNING('No equipment categories found. Creating basic categories...'))
            self.create_basic_equipment_categories()
            equipment_categories = EquipmentCategory.objects.all()
        
        # Create schedules for each category
        for category in equipment_categories:
            # PM-001 for all categories (quarterly)
            pm_001 = activity_types.get('PM-001')
            if pm_001:
                schedule, created = EquipmentCategorySchedule.objects.get_or_create(
                    equipment_category=category,
                    activity_type=pm_001,
                    defaults={
                        'frequency': 'quarterly',
                        'frequency_days': 90,
                        'auto_generate': True,
                        'advance_notice_days': 7,
                        'is_mandatory': True,
                        'allow_override': True,
                        'default_priority': 'medium',
                        'default_duration_hours': 4,
                    }
                )
                if created:
                    self.stdout.write(f'  Created category schedule: {category.name} - {pm_001.name}')
            
            # INS-001 for all categories (monthly)
            ins_001 = activity_types.get('INS-001')
            if ins_001:
                schedule, created = EquipmentCategorySchedule.objects.get_or_create(
                    equipment_category=category,
                    activity_type=ins_001,
                    defaults={
                        'frequency': 'monthly',
                        'frequency_days': 30,
                        'auto_generate': True,
                        'advance_notice_days': 3,
                        'is_mandatory': True,
                        'allow_override': True,
                        'default_priority': 'low',
                        'default_duration_hours': 2,
                    }
                )
                if created:
                    self.stdout.write(f'  Created category schedule: {category.name} - {ins_001.name}')

    def create_global_schedules(self, activity_types):
        """Create basic global schedules."""
        global_schedules_data = [
            {
                'name': 'Annual Comprehensive Maintenance',
                'activity_type': activity_types.get('PM-002'),
                'frequency': 'annual',
                'frequency_days': 365,
                'description': 'Annual comprehensive maintenance for all equipment',
                'auto_generate': True,
                'advance_notice_days': 14,
                'is_mandatory': True,
                'allow_override': True,
                'default_priority': 'high',
                'default_duration_hours': 8,
            },
            {
                'name': 'Semi-Annual Calibration',
                'activity_type': activity_types.get('CAL-001'),
                'frequency': 'semi_annual',
                'frequency_days': 180,
                'description': 'Semi-annual calibration for measurement equipment',
                'auto_generate': True,
                'advance_notice_days': 7,
                'is_mandatory': True,
                'allow_override': True,
                'default_priority': 'medium',
                'default_duration_hours': 2,
            },
            {
                'name': 'Quarterly Testing',
                'activity_type': activity_types.get('TEST-001'),
                'frequency': 'quarterly',
                'frequency_days': 90,
                'description': 'Quarterly functional testing for all equipment',
                'auto_generate': True,
                'advance_notice_days': 5,
                'is_mandatory': True,
                'allow_override': True,
                'default_priority': 'medium',
                'default_duration_hours': 3,
            },
        ]
        
        for data in global_schedules_data:
            if data['activity_type']:
                schedule, created = GlobalSchedule.objects.get_or_create(
                    name=data['name'],
                    defaults=data
                )
                if created:
                    self.stdout.write(f'  Created global schedule: {schedule.name}')
                else:
                    self.stdout.write(f'  Global schedule already exists: {schedule.name}')

    def create_basic_equipment_categories(self):
        """Create basic equipment categories if none exist."""
        categories_data = [
            {'name': 'Transformers', 'description': 'Power transformers and related equipment'},
            {'name': 'Switchgear', 'description': 'Electrical switchgear and distribution equipment'},
            {'name': 'Motors', 'description': 'Electric motors and drives'},
            {'name': 'Pumps', 'description': 'Pumps and pumping systems'},
            {'name': 'HVAC', 'description': 'Heating, ventilation, and air conditioning equipment'},
            {'name': 'Instrumentation', 'description': 'Measurement and control instrumentation'},
        ]
        
        for data in categories_data:
            category, created = EquipmentCategory.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            if created:
                self.stdout.write(f'  Created equipment category: {category.name}') 