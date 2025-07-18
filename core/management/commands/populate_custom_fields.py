"""
Populate custom fields for equipment categories.
This command creates example custom fields for different equipment categories.
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db import transaction
import logging

from core.models import EquipmentCategory
from equipment.models import EquipmentCategoryField

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Populate custom fields for equipment categories'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Clear existing custom fields before populating',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating data',
        )

    def handle(self, *args, **options):
        if options['dry_run']:
            self.stdout.write(
                self.style.SUCCESS('DRY RUN: Would populate custom fields for:')
            )
            self.stdout.write('  - Transformers')
            self.stdout.write('  - Switchgear')
            self.stdout.write('  - Motors')
            self.stdout.write('  - Pumps')
            self.stdout.write('  - HVAC')
            self.stdout.write('  - Instrumentation')
            if options['reset']:
                self.stdout.write('  - Reset existing data: YES')
            return
            
        self.stdout.write(
            self.style.SUCCESS('Starting custom fields population...')
        )
        
        try:
            with transaction.atomic():
                if options['reset']:
                    self.stdout.write('Clearing existing custom fields...')
                    EquipmentCategoryField.objects.all().delete()
                
                # Create custom fields for each category
                self.create_transformer_fields()
                self.create_switchgear_fields()
                self.create_motor_fields()
                self.create_pump_fields()
                self.create_hvac_fields()
                self.create_instrumentation_fields()
                
                self.stdout.write(
                    self.style.SUCCESS('Custom fields population completed successfully!')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during population: {str(e)}')
            )
            raise CommandError(f'Population failed: {str(e)}')

    def create_transformer_fields(self):
        """Create custom fields for transformers."""
        category = EquipmentCategory.objects.filter(name='Transformers').first()
        if not category:
            self.stdout.write(self.style.WARNING('Transformers category not found, skipping...'))
            return
        
        fields_data = [
            {
                'name': 'voltage_primary',
                'label': 'Primary Voltage (kV)',
                'field_type': 'number',
                'required': True,
                'help_text': 'Primary winding voltage in kilovolts',
                'field_group': 'Electrical',
                'sort_order': 1,
            },
            {
                'name': 'voltage_secondary',
                'label': 'Secondary Voltage (kV)',
                'field_type': 'number',
                'required': True,
                'help_text': 'Secondary winding voltage in kilovolts',
                'field_group': 'Electrical',
                'sort_order': 2,
            },
            {
                'name': 'power_rating',
                'label': 'Power Rating (MVA)',
                'field_type': 'number',
                'required': True,
                'help_text': 'Transformer power rating in MVA',
                'field_group': 'Electrical',
                'sort_order': 3,
            },
            {
                'name': 'cooling_type',
                'label': 'Cooling Type',
                'field_type': 'select',
                'required': True,
                'help_text': 'Type of cooling system',
                'choices': 'ONAN,ONAF,ONAN/ONAF,OFAN,OFWF',
                'field_group': 'Cooling',
                'sort_order': 4,
            },
            {
                'name': 'insulation_class',
                'label': 'Insulation Class',
                'field_type': 'select',
                'required': True,
                'help_text': 'Insulation class rating',
                'choices': 'A,B,F,H',
                'field_group': 'Electrical',
                'sort_order': 5,
            },
            {
                'name': 'oil_type',
                'label': 'Oil Type',
                'field_type': 'select',
                'required': False,
                'help_text': 'Type of insulating oil',
                'choices': 'Mineral Oil,Silicone Oil,Vegetable Oil,Synthetic Ester',
                'field_group': 'Cooling',
                'sort_order': 6,
            },
            {
                'name': 'tap_changer_type',
                'label': 'Tap Changer Type',
                'field_type': 'select',
                'required': False,
                'help_text': 'Type of tap changer',
                'choices': 'None,Manual,Automatic,Load Tap Changer',
                'field_group': 'Electrical',
                'sort_order': 7,
            },
            {
                'name': 'dga_frequency',
                'label': 'DGA Frequency (months)',
                'field_type': 'number',
                'required': False,
                'help_text': 'Frequency of DGA testing in months',
                'field_group': 'Maintenance',
                'sort_order': 8,
            },
        ]
        
        for data in fields_data:
            field, created = EquipmentCategoryField.objects.get_or_create(
                category=category,
                name=data['name'],
                defaults=data
            )
            if created:
                self.stdout.write(f'  Created transformer field: {field.label}')
            else:
                self.stdout.write(f'  Transformer field already exists: {field.label}')

    def create_switchgear_fields(self):
        """Create custom fields for switchgear."""
        category = EquipmentCategory.objects.filter(name='Switchgear').first()
        if not category:
            self.stdout.write(self.style.WARNING('Switchgear category not found, skipping...'))
            return
        
        fields_data = [
            {
                'name': 'voltage_rating',
                'label': 'Voltage Rating (kV)',
                'field_type': 'number',
                'required': True,
                'help_text': 'Rated voltage in kilovolts',
                'field_group': 'Electrical',
                'sort_order': 1,
            },
            {
                'name': 'current_rating',
                'label': 'Current Rating (A)',
                'field_type': 'number',
                'required': True,
                'help_text': 'Rated current in amperes',
                'field_group': 'Electrical',
                'sort_order': 2,
            },
            {
                'name': 'breaker_type',
                'label': 'Breaker Type',
                'field_type': 'select',
                'required': True,
                'help_text': 'Type of circuit breaker',
                'choices': 'Vacuum,SF6,Air,Oil',
                'field_group': 'Electrical',
                'sort_order': 3,
            },
            {
                'name': 'protection_type',
                'label': 'Protection Type',
                'field_type': 'multiselect',
                'required': False,
                'help_text': 'Types of protection relays',
                'choices': 'Overcurrent,Differential,Distance,Ground Fault,Transformer Protection',
                'field_group': 'Protection',
                'sort_order': 4,
            },
            {
                'name': 'enclosure_type',
                'label': 'Enclosure Type',
                'field_type': 'select',
                'required': False,
                'help_text': 'Type of enclosure',
                'choices': 'Indoor,Outdoor,Arc Resistant,Weatherproof',
                'field_group': 'Mechanical',
                'sort_order': 5,
            },
            {
                'name': 'operating_mechanism',
                'label': 'Operating Mechanism',
                'field_type': 'select',
                'required': False,
                'help_text': 'Type of operating mechanism',
                'choices': 'Manual,Spring,Electromagnetic,Pneumatic,Hydraulic',
                'field_group': 'Mechanical',
                'sort_order': 6,
            },
        ]
        
        for data in fields_data:
            field, created = EquipmentCategoryField.objects.get_or_create(
                category=category,
                name=data['name'],
                defaults=data
            )
            if created:
                self.stdout.write(f'  Created switchgear field: {field.label}')
            else:
                self.stdout.write(f'  Switchgear field already exists: {field.label}')

    def create_motor_fields(self):
        """Create custom fields for motors."""
        category = EquipmentCategory.objects.filter(name='Motors').first()
        if not category:
            self.stdout.write(self.style.WARNING('Motors category not found, skipping...'))
            return
        
        fields_data = [
            {
                'name': 'power_rating',
                'label': 'Power Rating (HP)',
                'field_type': 'number',
                'required': True,
                'help_text': 'Motor power rating in horsepower',
                'field_group': 'Electrical',
                'sort_order': 1,
            },
            {
                'name': 'voltage_rating',
                'label': 'Voltage Rating (V)',
                'field_type': 'number',
                'required': True,
                'help_text': 'Motor voltage rating',
                'field_group': 'Electrical',
                'sort_order': 2,
            },
            {
                'name': 'speed_rating',
                'label': 'Speed Rating (RPM)',
                'field_type': 'number',
                'required': True,
                'help_text': 'Motor speed rating in RPM',
                'field_group': 'Mechanical',
                'sort_order': 3,
            },
            {
                'name': 'motor_type',
                'label': 'Motor Type',
                'field_type': 'select',
                'required': True,
                'help_text': 'Type of motor',
                'choices': 'Induction,Synchronous,DC,AC Servo,Stepper',
                'field_group': 'Electrical',
                'sort_order': 4,
            },
            {
                'name': 'efficiency_class',
                'label': 'Efficiency Class',
                'field_type': 'select',
                'required': False,
                'help_text': 'Motor efficiency class',
                'choices': 'IE1,IE2,IE3,IE4,Premium',
                'field_group': 'Electrical',
                'sort_order': 5,
            },
            {
                'name': 'enclosure_type',
                'label': 'Enclosure Type',
                'field_type': 'select',
                'required': False,
                'help_text': 'Motor enclosure type',
                'choices': 'Open Drip Proof,Totally Enclosed Fan Cooled,Totally Enclosed Non-Ventilated,Explosion Proof',
                'field_group': 'Mechanical',
                'sort_order': 6,
            },
            {
                'name': 'bearing_type',
                'label': 'Bearing Type',
                'field_type': 'select',
                'required': False,
                'help_text': 'Type of bearings',
                'choices': 'Ball Bearings,Roller Bearings,Sleeve Bearings,Thrust Bearings',
                'field_group': 'Mechanical',
                'sort_order': 7,
            },
        ]
        
        for data in fields_data:
            field, created = EquipmentCategoryField.objects.get_or_create(
                category=category,
                name=data['name'],
                defaults=data
            )
            if created:
                self.stdout.write(f'  Created motor field: {field.label}')
            else:
                self.stdout.write(f'  Motor field already exists: {field.label}')

    def create_pump_fields(self):
        """Create custom fields for pumps."""
        category = EquipmentCategory.objects.filter(name='Pumps').first()
        if not category:
            self.stdout.write(self.style.WARNING('Pumps category not found, skipping...'))
            return
        
        fields_data = [
            {
                'name': 'flow_rate',
                'label': 'Flow Rate (GPM)',
                'field_type': 'number',
                'required': True,
                'help_text': 'Pump flow rate in gallons per minute',
                'field_group': 'Performance',
                'sort_order': 1,
            },
            {
                'name': 'head_pressure',
                'label': 'Head Pressure (PSI)',
                'field_type': 'number',
                'required': True,
                'help_text': 'Pump head pressure in PSI',
                'field_group': 'Performance',
                'sort_order': 2,
            },
            {
                'name': 'pump_type',
                'label': 'Pump Type',
                'field_type': 'select',
                'required': True,
                'help_text': 'Type of pump',
                'choices': 'Centrifugal,Positive Displacement,Reciprocating,Rotary,Screw',
                'field_group': 'Mechanical',
                'sort_order': 3,
            },
            {
                'name': 'impeller_material',
                'label': 'Impeller Material',
                'field_type': 'select',
                'required': False,
                'help_text': 'Material of the impeller',
                'choices': 'Cast Iron,Stainless Steel,Bronze,Plastic,Ceramic',
                'field_group': 'Mechanical',
                'sort_order': 4,
            },
            {
                'name': 'seal_type',
                'label': 'Seal Type',
                'field_type': 'select',
                'required': False,
                'help_text': 'Type of pump seal',
                'choices': 'Mechanical Seal,Packing Seal,Lip Seal,O-Ring',
                'field_group': 'Mechanical',
                'sort_order': 5,
            },
            {
                'name': 'fluid_type',
                'label': 'Fluid Type',
                'field_type': 'select',
                'required': False,
                'help_text': 'Type of fluid being pumped',
                'choices': 'Water,Oil,Chemical,Slurry,Air',
                'field_group': 'Application',
                'sort_order': 6,
            },
        ]
        
        for data in fields_data:
            field, created = EquipmentCategoryField.objects.get_or_create(
                category=category,
                name=data['name'],
                defaults=data
            )
            if created:
                self.stdout.write(f'  Created pump field: {field.label}')
            else:
                self.stdout.write(f'  Pump field already exists: {field.label}')

    def create_hvac_fields(self):
        """Create custom fields for HVAC equipment."""
        category = EquipmentCategory.objects.filter(name='HVAC').first()
        if not category:
            self.stdout.write(self.style.WARNING('HVAC category not found, skipping...'))
            return
        
        fields_data = [
            {
                'name': 'cooling_capacity',
                'label': 'Cooling Capacity (BTU/hr)',
                'field_type': 'number',
                'required': True,
                'help_text': 'Cooling capacity in BTU per hour',
                'field_group': 'Performance',
                'sort_order': 1,
            },
            {
                'name': 'heating_capacity',
                'label': 'Heating Capacity (BTU/hr)',
                'field_type': 'number',
                'required': False,
                'help_text': 'Heating capacity in BTU per hour',
                'field_group': 'Performance',
                'sort_order': 2,
            },
            {
                'name': 'refrigerant_type',
                'label': 'Refrigerant Type',
                'field_type': 'select',
                'required': False,
                'help_text': 'Type of refrigerant used',
                'choices': 'R-22,R-134a,R-410a,R-407c,R-32,Ammonia',
                'field_group': 'Refrigeration',
                'sort_order': 3,
            },
            {
                'name': 'unit_type',
                'label': 'Unit Type',
                'field_type': 'select',
                'required': True,
                'help_text': 'Type of HVAC unit',
                'choices': 'Split System,Package Unit,Chiller,Air Handler,Heat Pump',
                'field_group': 'Mechanical',
                'sort_order': 4,
            },
            {
                'name': 'airflow_capacity',
                'label': 'Airflow Capacity (CFM)',
                'field_type': 'number',
                'required': False,
                'help_text': 'Airflow capacity in cubic feet per minute',
                'field_group': 'Performance',
                'sort_order': 5,
            },
            {
                'name': 'filter_type',
                'label': 'Filter Type',
                'field_type': 'select',
                'required': False,
                'help_text': 'Type of air filter',
                'choices': 'Fiberglass,Pleated,HEPA,Electrostatic,Washable',
                'field_group': 'Air Quality',
                'sort_order': 6,
            },
        ]
        
        for data in fields_data:
            field, created = EquipmentCategoryField.objects.get_or_create(
                category=category,
                name=data['name'],
                defaults=data
            )
            if created:
                self.stdout.write(f'  Created HVAC field: {field.label}')
            else:
                self.stdout.write(f'  HVAC field already exists: {field.label}')

    def create_instrumentation_fields(self):
        """Create custom fields for instrumentation."""
        category = EquipmentCategory.objects.filter(name='Instrumentation').first()
        if not category:
            self.stdout.write(self.style.WARNING('Instrumentation category not found, skipping...'))
            return
        
        fields_data = [
            {
                'name': 'measurement_type',
                'label': 'Measurement Type',
                'field_type': 'select',
                'required': True,
                'help_text': 'Type of measurement',
                'choices': 'Temperature,Pressure,Flow,Level,Analytical,Position',
                'field_group': 'Measurement',
                'sort_order': 1,
            },
            {
                'name': 'measurement_range',
                'label': 'Measurement Range',
                'field_type': 'text',
                'required': True,
                'help_text': 'Range of measurement (e.g., 0-100 PSI)',
                'field_group': 'Measurement',
                'sort_order': 2,
            },
            {
                'name': 'accuracy',
                'label': 'Accuracy (%)',
                'field_type': 'decimal',
                'required': False,
                'help_text': 'Accuracy as percentage of full scale',
                'field_group': 'Specifications',
                'sort_order': 3,
            },
            {
                'name': 'output_signal',
                'label': 'Output Signal',
                'field_type': 'select',
                'required': False,
                'help_text': 'Type of output signal',
                'choices': '4-20mA,0-10V,0-5V,Digital,HART,Foundation Fieldbus',
                'field_group': 'Electrical',
                'sort_order': 4,
            },
            {
                'name': 'power_supply',
                'label': 'Power Supply',
                'field_type': 'text',
                'required': False,
                'help_text': 'Power supply requirements (e.g., 24V DC)',
                'field_group': 'Electrical',
                'sort_order': 5,
            },
            {
                'name': 'calibration_frequency',
                'label': 'Calibration Frequency (months)',
                'field_type': 'number',
                'required': False,
                'help_text': 'Frequency of calibration in months',
                'field_group': 'Maintenance',
                'sort_order': 6,
            },
        ]
        
        for data in fields_data:
            field, created = EquipmentCategoryField.objects.get_or_create(
                category=category,
                name=data['name'],
                defaults=data
            )
            if created:
                self.stdout.write(f'  Created instrumentation field: {field.label}')
            else:
                self.stdout.write(f'  Instrumentation field already exists: {field.label}') 