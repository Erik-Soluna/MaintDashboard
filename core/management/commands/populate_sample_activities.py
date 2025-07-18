"""
Populate sample maintenance activities.
This command creates sample maintenance activities using the activity types we created.
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
    MaintenanceActivityType, MaintenanceActivity
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Populate sample maintenance activities using existing activity types'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Clear existing maintenance activities before populating',
        )
        parser.add_argument(
            '--count',
            type=int,
            default=50,
            help='Number of sample activities to create (default: 50)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating data',
        )

    def handle(self, *args, **options):
        if options['dry_run']:
            self.stdout.write(
                self.style.SUCCESS('DRY RUN: Would populate sample activities:')
            )
            self.stdout.write(f'  - Sample Activities: {options["count"]}')
            if options['reset']:
                self.stdout.write('  - Reset existing data: YES')
            return
            
        self.stdout.write(
            self.style.SUCCESS('Starting sample activities population...')
        )
        
        try:
            with transaction.atomic():
                if options['reset']:
                    self.stdout.write('Clearing existing maintenance activities...')
                    MaintenanceActivity.objects.all().delete()
                
                # Create sample activities
                self.stdout.write('Creating sample maintenance activities...')
                self.create_sample_activities(options['count'])
                
                self.stdout.write(
                    self.style.SUCCESS('Sample activities population completed successfully!')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during population: {str(e)}')
            )
            raise CommandError(f'Population failed: {str(e)}')

    def create_sample_activities(self, count):
        """Create sample maintenance activities."""
        # Get activity types
        activity_types = list(MaintenanceActivityType.objects.filter(is_active=True))
        if not activity_types:
            self.stdout.write(self.style.ERROR('No activity types found. Please run populate_activity_types_and_schedules first.'))
            return
        
        # Get equipment
        equipment_list = list(Equipment.objects.filter(is_active=True))
        if not equipment_list:
            self.stdout.write(self.style.WARNING('No equipment found. Creating sample equipment...'))
            self.create_sample_equipment()
            equipment_list = list(Equipment.objects.filter(is_active=True))
        
        # Get users for assignment
        users = list(User.objects.filter(is_active=True))
        if not users:
            self.stdout.write(self.style.WARNING('No users found. Using admin user.'))
            users = [User.objects.filter(is_superuser=True).first()]
        
        # Status distribution
        status_weights = {
            'scheduled': 0.3,
            'pending': 0.2,
            'in_progress': 0.1,
            'completed': 0.35,
            'cancelled': 0.05,
        }
        
        # Priority distribution
        priority_weights = {
            'low': 0.2,
            'medium': 0.5,
            'high': 0.2,
            'critical': 0.1,
        }
        
        activities_created = 0
        
        for i in range(count):
            # Select random activity type and equipment
            activity_type = random.choice(activity_types)
            equipment = random.choice(equipment_list)
            
            # Determine status
            status = random.choices(
                list(status_weights.keys()),
                weights=list(status_weights.values())
            )[0]
            
            # Determine priority
            priority = random.choices(
                list(priority_weights.keys()),
                weights=list(priority_weights.values())
            )[0]
            
            # Generate dates
            base_date = timezone.now().date()
            
            # For completed activities, set dates in the past
            if status == 'completed':
                days_ago = random.randint(1, 90)
                scheduled_start = timezone.now() - timedelta(days=days_ago)
                scheduled_end = scheduled_start + timedelta(hours=activity_type.estimated_duration_hours)
                actual_start = scheduled_start + timedelta(minutes=random.randint(0, 60))
                actual_end = actual_start + timedelta(hours=random.uniform(0.8, 1.2) * activity_type.estimated_duration_hours)
            # For in_progress activities, start in the past, end in the future
            elif status == 'in_progress':
                days_ago = random.randint(1, 7)
                scheduled_start = timezone.now() - timedelta(days=days_ago)
                scheduled_end = scheduled_start + timedelta(hours=activity_type.estimated_duration_hours)
                actual_start = scheduled_start + timedelta(minutes=random.randint(0, 60))
                actual_end = None
            # For scheduled activities, set in the future
            elif status == 'scheduled':
                days_ahead = random.randint(1, 30)
                scheduled_start = timezone.now() + timedelta(days=days_ahead)
                scheduled_end = scheduled_start + timedelta(hours=activity_type.estimated_duration_hours)
                actual_start = None
                actual_end = None
            # For pending activities, set in the near future
            elif status == 'pending':
                days_ahead = random.randint(1, 7)
                scheduled_start = timezone.now() + timedelta(days=days_ahead)
                scheduled_end = scheduled_start + timedelta(hours=activity_type.estimated_duration_hours)
                actual_start = None
                actual_end = None
            # For cancelled activities, set in the past
            else:  # cancelled
                days_ago = random.randint(1, 30)
                scheduled_start = timezone.now() - timedelta(days=days_ago)
                scheduled_end = scheduled_start + timedelta(hours=activity_type.estimated_duration_hours)
                actual_start = None
                actual_end = None
            
            # Create the activity
            activity = MaintenanceActivity.objects.create(
                equipment=equipment,
                activity_type=activity_type,
                title=f"{activity_type.name} - {equipment.name}",
                description=f"Sample {activity_type.name} activity for {equipment.name}. {activity_type.description}",
                status=status,
                priority=priority,
                scheduled_start=scheduled_start,
                scheduled_end=scheduled_end,
                actual_start=actual_start,
                actual_end=actual_end,
                assigned_to=random.choice(users) if users else None,
                tools_required=activity_type.tools_required,
                parts_required=activity_type.parts_required,
                safety_notes=activity_type.safety_notes,
                completion_notes=f"Sample completion notes for {activity_type.name}" if status == 'completed' else "",
            )
            
            activities_created += 1
            if activities_created % 10 == 0:
                self.stdout.write(f'  Created {activities_created} activities...')
        
        self.stdout.write(f'  Total activities created: {activities_created}')

    def create_sample_equipment(self):
        """Create sample equipment if none exists."""
        # Get or create equipment categories
        categories_data = [
            {'name': 'Transformers', 'description': 'Power transformers and related equipment'},
            {'name': 'Switchgear', 'description': 'Electrical switchgear and distribution equipment'},
            {'name': 'Motors', 'description': 'Electric motors and drives'},
            {'name': 'Pumps', 'description': 'Pumps and pumping systems'},
            {'name': 'HVAC', 'description': 'Heating, ventilation, and air conditioning equipment'},
            {'name': 'Instrumentation', 'description': 'Measurement and control instrumentation'},
        ]
        
        categories = {}
        for data in categories_data:
            category, created = EquipmentCategory.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            categories[data['name']] = category
        
        # Get or create a location
        location, created = Location.objects.get_or_create(
            name='Main Facility',
            defaults={
                'address': '123 Main Street, Anytown, ST 12345, USA',
                'is_site': True,
            }
        )
        
        # Create sample equipment
        equipment_data = [
            {'name': 'Main Transformer T1', 'category': categories['Transformers'], 'model_number': 'T-1000', 'manufacturer_serial': 'T1-2024-001', 'asset_tag': 'T1-001'},
            {'name': 'Distribution Switchgear DS1', 'category': categories['Switchgear'], 'model_number': 'DS-500', 'manufacturer_serial': 'DS1-2024-001', 'asset_tag': 'DS1-001'},
            {'name': 'Cooling Pump P1', 'category': categories['Pumps'], 'model_number': 'CP-200', 'manufacturer_serial': 'P1-2024-001', 'asset_tag': 'P1-001'},
            {'name': 'HVAC Unit H1', 'category': categories['HVAC'], 'model_number': 'HVAC-300', 'manufacturer_serial': 'H1-2024-001', 'asset_tag': 'H1-001'},
            {'name': 'Control Panel CP1', 'category': categories['Instrumentation'], 'model_number': 'CP-100', 'manufacturer_serial': 'CP1-2024-001', 'asset_tag': 'CP1-001'},
            {'name': 'Motor M1', 'category': categories['Motors'], 'model_number': 'M-150', 'manufacturer_serial': 'M1-2024-001', 'asset_tag': 'M1-001'},
            {'name': 'Backup Transformer T2', 'category': categories['Transformers'], 'model_number': 'T-1000', 'manufacturer_serial': 'T2-2024-001', 'asset_tag': 'T2-001'},
            {'name': 'Secondary Switchgear DS2', 'category': categories['Switchgear'], 'model_number': 'DS-500', 'manufacturer_serial': 'DS2-2024-001', 'asset_tag': 'DS2-001'},
        ]
        
        for data in equipment_data:
            equipment, created = Equipment.objects.get_or_create(
                name=data['name'],
                defaults={
                    'category': data['category'],
                    'location': location,
                    'model_number': data['model_number'],
                    'manufacturer_serial': data['manufacturer_serial'],
                    'asset_tag': data['asset_tag'],
                    'manufacturer': 'Sample Manufacturer',
                    'commissioning_date': timezone.now().date() - timedelta(days=random.randint(30, 365)),
                    'is_active': True,
                }
            )
            if created:
                self.stdout.write(f'  Created equipment: {equipment.name}') 