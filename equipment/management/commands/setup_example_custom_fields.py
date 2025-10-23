"""
Management command to create example custom fields for equipment categories.
This provides sample fields that users can use for conditional field assignments.
"""

from django.core.management.base import BaseCommand
from equipment.models import EquipmentCategory, EquipmentCategoryField


class Command(BaseCommand):
    help = 'Create example custom fields for equipment categories'

    def handle(self, *args, **options):
        self.stdout.write('🏗️ Creating example custom fields...')
        
        # Get or create equipment categories
        categories_data = [
            {
                'name': 'Transformers',
                'description': 'Power transformers and distribution transformers',
                'fields': [
                    {'name': 'oil_type', 'label': 'Oil Type', 'field_type': 'choice', 'choices': 'Mineral Oil,Silicon Oil,Synthetic Oil,Vegetable Oil', 'help_text': 'Type of insulating oil used'},
                    {'name': 'cooling_type', 'label': 'Cooling Type', 'field_type': 'choice', 'choices': 'ONAN,ONAF,OFAF,OFWF', 'help_text': 'Cooling system type'},
                    {'name': 'primary_voltage', 'label': 'Primary Voltage (kV)', 'field_type': 'number', 'help_text': 'Primary winding voltage rating'},
                    {'name': 'secondary_voltage', 'label': 'Secondary Voltage (kV)', 'field_type': 'number', 'help_text': 'Secondary winding voltage rating'},
                    {'name': 'power_rating', 'label': 'Power Rating (MVA)', 'field_type': 'number', 'help_text': 'Transformer power rating'},
                ]
            },
            {
                'name': 'Switchgear',
                'description': 'Circuit breakers, switches, and protection equipment',
                'fields': [
                    {'name': 'breaker_type', 'label': 'Breaker Type', 'field_type': 'choice', 'choices': 'Vacuum,SF6,Air Blast,Oil', 'help_text': 'Type of circuit breaker'},
                    {'name': 'operating_voltage', 'label': 'Operating Voltage (kV)', 'field_type': 'number', 'help_text': 'Rated operating voltage'},
                    {'name': 'breaking_capacity', 'label': 'Breaking Capacity (kA)', 'field_type': 'number', 'help_text': 'Short circuit breaking capacity'},
                    {'name': 'protection_type', 'label': 'Protection Type', 'field_type': 'choice', 'choices': 'Overcurrent,Differential,Distance,Earth Fault', 'help_text': 'Primary protection scheme'},
                ]
            },
            {
                'name': 'Protection',
                'description': 'Protection relays and control systems',
                'fields': [
                    {'name': 'relay_type', 'label': 'Relay Type', 'field_type': 'choice', 'choices': 'Electromechanical,Static,Digital', 'help_text': 'Type of protection relay'},
                    {'name': 'protection_function', 'label': 'Protection Function', 'field_type': 'choice', 'choices': 'Overcurrent,Differential,Distance,Earth Fault,Under/Over Voltage', 'help_text': 'Primary protection function'},
                    {'name': 'communication_protocol', 'label': 'Communication Protocol', 'field_type': 'choice', 'choices': 'Modbus,DNP3,IEC 61850,Profinet', 'help_text': 'Communication protocol used'},
                ]
            },
            {
                'name': 'Cables',
                'description': 'Power cables and accessories',
                'fields': [
                    {'name': 'cable_type', 'label': 'Cable Type', 'field_type': 'choice', 'choices': 'XLPE,PVC,Paper Insulated,Mineral Insulated', 'help_text': 'Cable insulation type'},
                    {'name': 'conductor_material', 'label': 'Conductor Material', 'field_type': 'choice', 'choices': 'Copper,Aluminum', 'help_text': 'Conductor material'},
                    {'name': 'cross_section', 'label': 'Cross Section (mm²)', 'field_type': 'number', 'help_text': 'Conductor cross-sectional area'},
                    {'name': 'voltage_rating', 'label': 'Voltage Rating (kV)', 'field_type': 'number', 'help_text': 'Cable voltage rating'},
                ]
            },
            {
                'name': 'Motors',
                'description': 'Electric motors and drives',
                'fields': [
                    {'name': 'motor_type', 'label': 'Motor Type', 'field_type': 'choice', 'choices': 'Induction,Synchronous,DC,Stepper', 'help_text': 'Type of electric motor'},
                    {'name': 'power_rating', 'label': 'Power Rating (kW)', 'field_type': 'number', 'help_text': 'Motor power rating'},
                    {'name': 'speed_rating', 'label': 'Speed Rating (RPM)', 'field_type': 'number', 'help_text': 'Rated motor speed'},
                    {'name': 'efficiency_class', 'label': 'Efficiency Class', 'field_type': 'choice', 'choices': 'IE1,IE2,IE3,IE4', 'help_text': 'Motor efficiency class'},
                ]
            }
        ]
        
        created_count = 0
        
        for category_data in categories_data:
            # Get or create the category
            category, created = EquipmentCategory.objects.get_or_create(
                name=category_data['name'],
                defaults={'description': category_data['description']}
            )
            
            if created:
                self.stdout.write(f'  ✅ Created category: {category.name}')
            else:
                self.stdout.write(f'  ℹ️ Category already exists: {category.name}')
            
            # Create fields for this category
            for field_data in category_data['fields']:
                field, created = EquipmentCategoryField.objects.get_or_create(
                    category=category,
                    name=field_data['name'],
                    defaults={
                        'label': field_data['label'],
                        'field_type': field_data['field_type'],
                        'help_text': field_data.get('help_text', ''),
                        'choices': field_data.get('choices', ''),
                        'required': False,
                        'is_active': True,
                        'sort_order': 0,
                    }
                )
                
                if created:
                    self.stdout.write(f'    ✅ Created field: {field.label}')
                    created_count += 1
                else:
                    self.stdout.write(f'    ℹ️ Field already exists: {field.label}')
        
        self.stdout.write(f'\n🎉 Example custom fields setup completed!')
        self.stdout.write(f'📊 Created {created_count} new custom fields')
        self.stdout.write(f'💡 You can now use these fields for conditional field assignments')
        self.stdout.write(f'🔗 Go to the Conditional Fields settings page to create assignments')
