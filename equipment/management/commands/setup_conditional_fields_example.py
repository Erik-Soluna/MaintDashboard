"""
Management command to set up example conditional fields for demonstration.
This creates example conditional field assignments like "oil_type" for "Transformers" 
being available for "Switchgear" equipment.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import EquipmentCategory
from equipment.models import EquipmentCategoryField, EquipmentCategoryConditionalField


class Command(BaseCommand):
    help = 'Set up example conditional fields for demonstration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of conditional fields even if they already exist'
        )

    def handle(self, *args, **options):
        self.stdout.write('🚀 Setting up example conditional fields...')
        
        # Get or create admin user
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        
        # Create example equipment categories if they don't exist
        transformer_category, created = EquipmentCategory.objects.get_or_create(
            name='Transformers',
            defaults={
                'description': 'Power transformers and related equipment',
                'created_by': admin_user,
            }
        )
        
        switchgear_category, created = EquipmentCategory.objects.get_or_create(
            name='Switchgear',
            defaults={
                'description': 'Electrical switchgear and distribution equipment',
                'created_by': admin_user,
            }
        )
        
        protection_category, created = EquipmentCategory.objects.get_or_create(
            name='Protection',
            defaults={
                'description': 'Protection relays and control equipment',
                'created_by': admin_user,
            }
        )
        
        # Create example fields for Transformers category
        oil_type_field, created = EquipmentCategoryField.objects.get_or_create(
            category=transformer_category,
            name='oil_type',
            defaults={
                'label': 'Oil Type',
                'field_type': 'select',
                'required': True,
                'help_text': 'Type of insulating oil used in the transformer',
                'choices': 'Mineral Oil,Silicon Oil,Synthetic Ester,Natural Ester',
                'field_group': 'Electrical',
                'sort_order': 10,
                'created_by': admin_user,
            }
        )
        
        cooling_type_field, created = EquipmentCategoryField.objects.get_or_create(
            category=transformer_category,
            name='cooling_type',
            defaults={
                'label': 'Cooling Type',
                'field_type': 'select',
                'required': False,
                'help_text': 'Type of cooling system used',
                'choices': 'ONAN,ONAF,ONAF/ONAN,OFAN,OFWF',
                'field_group': 'Electrical',
                'sort_order': 20,
                'created_by': admin_user,
            }
        )
        
        # Create example fields for Switchgear category
        breaker_type_field, created = EquipmentCategoryField.objects.get_or_create(
            category=switchgear_category,
            name='breaker_type',
            defaults={
                'label': 'Breaker Type',
                'field_type': 'select',
                'required': True,
                'help_text': 'Type of circuit breaker',
                'choices': 'Vacuum,SF6,Air,Oil',
                'field_group': 'Electrical',
                'sort_order': 10,
                'created_by': admin_user,
            }
        )
        
        # Create example fields for Protection category
        relay_type_field, created = EquipmentCategoryField.objects.get_or_create(
            category=protection_category,
            name='relay_type',
            defaults={
                'label': 'Relay Type',
                'field_type': 'select',
                'required': True,
                'help_text': 'Type of protection relay',
                'choices': 'Overcurrent,Differential,Distance,Voltage,Frequency',
                'field_group': 'Protection',
                'sort_order': 10,
                'created_by': admin_user,
            }
        )
        
        # Create conditional field assignments
        conditional_fields_created = 0
        
        # Make oil_type field from Transformers available to Switchgear
        oil_to_switchgear, created = EquipmentCategoryConditionalField.objects.get_or_create(
            source_category=transformer_category,
            target_category=switchgear_category,
            field=oil_type_field,
            defaults={
                'override_label': 'Insulating Medium Type',
                'override_help_text': 'Type of insulating medium used in the switchgear (oil type for oil-filled equipment)',
                'override_required': False,
                'override_field_group': 'Electrical',
                'override_sort_order': 15,
                'created_by': admin_user,
            }
        )
        if created:
            conditional_fields_created += 1
            self.stdout.write(f'  ✅ Created conditional field: {oil_type_field.label} → {switchgear_category.name}')
        
        # Make cooling_type field from Transformers available to Switchgear
        cooling_to_switchgear, created = EquipmentCategoryConditionalField.objects.get_or_create(
            source_category=transformer_category,
            target_category=switchgear_category,
            field=cooling_type_field,
            defaults={
                'override_label': 'Cooling System',
                'override_help_text': 'Type of cooling system used in the switchgear',
                'override_required': False,
                'override_field_group': 'Electrical',
                'override_sort_order': 25,
                'created_by': admin_user,
            }
        )
        if created:
            conditional_fields_created += 1
            self.stdout.write(f'  ✅ Created conditional field: {cooling_type_field.label} → {switchgear_category.name}')
        
        # Make breaker_type field from Switchgear available to Protection
        breaker_to_protection, created = EquipmentCategoryConditionalField.objects.get_or_create(
            source_category=switchgear_category,
            target_category=protection_category,
            field=breaker_type_field,
            defaults={
                'override_label': 'Associated Breaker Type',
                'override_help_text': 'Type of circuit breaker associated with this protection relay',
                'override_required': False,
                'override_field_group': 'Equipment',
                'override_sort_order': 20,
                'created_by': admin_user,
            }
        )
        if created:
            conditional_fields_created += 1
            self.stdout.write(f'  ✅ Created conditional field: {breaker_type_field.label} → {protection_category.name}')
        
        # Make relay_type field from Protection available to Transformers
        relay_to_transformer, created = EquipmentCategoryConditionalField.objects.get_or_create(
            source_category=protection_category,
            target_category=transformer_category,
            field=relay_type_field,
            defaults={
                'override_label': 'Protection Relay Type',
                'override_help_text': 'Type of protection relay used for this transformer',
                'override_required': False,
                'override_field_group': 'Protection',
                'override_sort_order': 30,
                'created_by': admin_user,
            }
        )
        if created:
            conditional_fields_created += 1
            self.stdout.write(f'  ✅ Created conditional field: {relay_type_field.label} → {transformer_category.name}')
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'✅ Conditional fields setup completed!'))
        self.stdout.write(f'   Created: {conditional_fields_created} conditional field assignments')
        self.stdout.write('')
        self.stdout.write('📋 Example assignments created:')
        self.stdout.write('   • Oil Type (Transformers) → Switchgear (as "Insulating Medium Type")')
        self.stdout.write('   • Cooling Type (Transformers) → Switchgear (as "Cooling System")')
        self.stdout.write('   • Breaker Type (Switchgear) → Protection (as "Associated Breaker Type")')
        self.stdout.write('   • Relay Type (Protection) → Transformers (as "Protection Relay Type")')
        self.stdout.write('')
        self.stdout.write('🔗 You can now manage these conditional fields at:')
        self.stdout.write('   /equipment-conditional-fields/settings/')
