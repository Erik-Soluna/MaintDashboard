"""
Django command to load initial data for the maintenance dashboard.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import EquipmentCategory, Location
from maintenance.models import MaintenanceActivityType


class Command(BaseCommand):
    """Django command to load initial data."""

    help = 'Load initial data for the maintenance dashboard'

    def handle(self, *args, **options):
        """Handle the command."""
        self.stdout.write('Loading initial data...')

        try:
            with transaction.atomic():
                self.create_equipment_categories()
                self.create_locations()
                self.create_maintenance_activity_types()

            self.stdout.write(
                self.style.SUCCESS('Initial data loaded successfully!')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error loading initial data: {e}')
            )

    def create_equipment_categories(self):
        """Create initial equipment categories."""
        categories = [
            {
                'name': 'Transformers',
                'description': 'Power transformers and distribution transformers'
            },
            {
                'name': 'Switchgear',
                'description': 'High voltage and low voltage switchgear'
            },
            {
                'name': 'Protection Systems',
                'description': 'Protective relays and control systems'
            },
            {
                'name': 'Generators',
                'description': 'Emergency generators and backup power systems'
            },
            {
                'name': 'HVAC Systems',
                'description': 'Heating, ventilation, and air conditioning'
            },
            {
                'name': 'Fire Protection',
                'description': 'Fire suppression and detection systems'
            },
            {
                'name': 'Monitoring Equipment',
                'description': 'SCADA, meters, and monitoring devices'
            },
        ]

        for cat_data in categories:
            category, created = EquipmentCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={'description': cat_data['description']}
            )
            if created:
                self.stdout.write(f'Created category: {category.name}')

    def create_locations(self):
        """Create initial locations with hierarchy."""
        # Create site locations first
        sites = [
            {
                'name': 'Main Site',
                'is_site': True,
                'address': '123 Main Street, City, State'
            },
            {
                'name': 'Substation A',
                'is_site': True,
                'address': '456 Industrial Ave, City, State'
            },
            {
                'name': 'Substation B',
                'is_site': True,
                'address': '789 Power Blvd, City, State'
            },
        ]

        site_objects = {}
        for site_data in sites:
            site, created = Location.objects.get_or_create(
                name=site_data['name'],
                is_site=True,
                defaults={
                    'address': site_data['address'],
                    'is_site': True
                }
            )
            site_objects[site.name] = site
            if created:
                self.stdout.write(f'Created site: {site.name}')

        # Create equipment locations
        equipment_locations = [
            {
                'name': 'Control Room',
                'parent': 'Main Site',
            },
            {
                'name': 'Transformer Yard',
                'parent': 'Main Site',
            },
            {
                'name': 'Switchgear Room',
                'parent': 'Main Site',
            },
            {
                'name': 'Generator Building',
                'parent': 'Main Site',
            },
            {
                'name': 'Primary Bay',
                'parent': 'Substation A',
            },
            {
                'name': 'Secondary Bay',
                'parent': 'Substation A',
            },
            {
                'name': 'Control House',
                'parent': 'Substation B',
            },
        ]

        for loc_data in equipment_locations:
            parent_site = site_objects.get(loc_data['parent'])
            if parent_site:
                location, created = Location.objects.get_or_create(
                    name=loc_data['name'],
                    parent_location=parent_site,
                    defaults={'is_site': False}
                )
                if created:
                    self.stdout.write(f'Created location: {location.name}')

    def create_maintenance_activity_types(self):
        """Create initial maintenance activity types."""
        activity_types = [
            {
                'name': 'T-A-1',
                'description': 'Annual Transformer Inspection',
                'estimated_duration_hours': 4,
                'frequency_days': 365,
                'is_mandatory': True
            },
            {
                'name': 'T-A-2',
                'description': 'Transformer Oil Analysis',
                'estimated_duration_hours': 2,
                'frequency_days': 365,
                'is_mandatory': True
            },
            {
                'name': 'T-R/A-3',
                'description': 'Transformer Repair/Assessment',
                'estimated_duration_hours': 8,
                'frequency_days': 730,  # Every 2 years
                'is_mandatory': False
            },
            {
                'name': 'SW-M-1',
                'description': 'Monthly Switchgear Inspection',
                'estimated_duration_hours': 2,
                'frequency_days': 30,
                'is_mandatory': True
            },
            {
                'name': 'SW-A-1',
                'description': 'Annual Switchgear Maintenance',
                'estimated_duration_hours': 6,
                'frequency_days': 365,
                'is_mandatory': True
            },
            {
                'name': 'GEN-M-1',
                'description': 'Monthly Generator Test',
                'estimated_duration_hours': 1,
                'frequency_days': 30,
                'is_mandatory': True
            },
            {
                'name': 'GEN-A-1',
                'description': 'Annual Generator Service',
                'estimated_duration_hours': 8,
                'frequency_days': 365,
                'is_mandatory': True
            },
            {
                'name': 'PROT-A-1',
                'description': 'Annual Protection System Test',
                'estimated_duration_hours': 4,
                'frequency_days': 365,
                'is_mandatory': True
            },
            {
                'name': 'HVAC-Q-1',
                'description': 'Quarterly HVAC Filter Change',
                'estimated_duration_hours': 2,
                'frequency_days': 90,
                'is_mandatory': True
            },
            {
                'name': 'FIRE-A-1',
                'description': 'Annual Fire System Inspection',
                'estimated_duration_hours': 3,
                'frequency_days': 365,
                'is_mandatory': True
            },
        ]

        for activity_data in activity_types:
            activity_type, created = MaintenanceActivityType.objects.get_or_create(
                name=activity_data['name'],
                defaults=activity_data
            )
            if created:
                self.stdout.write(f'Created activity type: {activity_type.name}')