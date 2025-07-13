"""
Management command to populate the database with sample data.
"""

import csv
import io
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Location, Customer, EquipmentCategory
from equipment.models import Equipment


class Command(BaseCommand):
    help = 'Populate database with sample data for Project Dorothy'

    def handle(self, *args, **options):
        self.stdout.write('Starting to populate sample data...')
        
        # Get or create admin user
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write('Created admin user')
        
        # Create or get customer
        customer, created = Customer.objects.get_or_create(
            name='Project Dorothy',
            defaults={
                'code': 'DOROTHY',
                'contact_email': 'dorothy@example.com',
                'description': 'Project Dorothy customer',
                'created_by': admin_user,
            }
        )
        if created:
            self.stdout.write('Created customer: Project Dorothy')
        
        # Create or get equipment category
        category, created = EquipmentCategory.objects.get_or_create(
            name='Transformers',
            defaults={
                'description': 'Power transformers and related equipment',
                'created_by': admin_user,
            }
        )
        if created:
            self.stdout.write('Created equipment category: Transformers')
        
        # Create or get main site
        main_site, created = Location.objects.get_or_create(
            name='Dorothy Site',
            defaults={
                'is_site': True,
                'customer': customer,
                'is_active': True,
                'created_by': admin_user,
            }
        )
        if created:
            self.stdout.write('Created main site: Dorothy Site')
        
        # Sample data
        sample_data = """Asset Tag,Serial Number,Model,Company,Category,Status,Location,Entity
MD2550-2212,MD2550-2212,Maddox,Project Dorothy,Transformers,Deployed,Dorothy POD 1,D1B
MD2550-2210,MD2550-2210,Maddox,Project Dorothy,Transformers,Deployed,Dorothy POD 2,D1B
MD2550-2209,MD2550-2209,Maddox,Project Dorothy,Transformers,Deployed,Dorothy POD 3,D1B
MD2550-2208,MD2550-2208,Maddox,Project Dorothy,Transformers,Deployed,Dorothy POD 4,D1B
MD2550-2207,MD2550-2207,Maddox,Project Dorothy,Transformers,Deployed,Dorothy POD 5,D1B
MD2550-2211,MD2550-2211,Maddox,Project Dorothy,Transformers,Deployed,Dorothy POD 6,D1B
MD2550-2204,MD2550-2204,Maddox,Project Dorothy,Transformers,Deployed,Dorothy POD 7,D1B
MD2550-2205,MD2550-2205,Maddox,Project Dorothy,Transformers,Deployed,Dorothy POD 8,D1B
MD2550-2202,MD2550-2202,Maddox,Project Dorothy,Transformers,Deployed,Dorothy POD 9,D1A
32212679624,32212679624,Maddox,Project Dorothy,Transformers,Deployed,Dorothy POD 10,D1A
32212679625,32212679625,Maddox,Project Dorothy,Transformers,Deployed,Dorothy POD 11,D1A
MD2550-2201,MD2550-2201,Maddox,Project Dorothy,Transformers,Deployed,Dorothy POD 12,D1A
MD2550-2203,MD2550-2203,Maddox,Project Dorothy,Transformers,Deployed,Dorothy POD 13,D1A
32212680026,32212680026,Maddox,Project Dorothy,Transformers,Deployed,Dorothy POD 14,D1A
52212725139,52212725139,Maddox,Project Dorothy,Transformers,Deployed,Dorothy POD 15,D1A
32212679623,32212679623,Maddox,Project Dorothy,Transformers,Deployed,Dorothy POD 16,D1A
32212679622,32212679622,Maddox,Project Dorothy,Transformers,Deployed,Dorothy POD 17,D1A
32212680025,32212680025,Maddox,Project Dorothy,Transformers,Deployed,Dorothy POD 18,D1A
52212725138,52212725138,Maddox,Project Dorothy,Transformers,Deployed,Dorothy POD 19,D1A
42212707921,42212707921,Maddox,Project Dorothy,Transformers,Deployed,Dorothy POD 20,D1B
32212680027,32212680027,Maddox,Project Dorothy,Transformers,Deployed,Dorothy POD 21,D1B
MD2550-2206,MD2550-2206,Maddox,Project Dorothy,Transformers,Deployed,Dorothy POD 22,D1B"""
        
        # Parse CSV data
        csv_data = csv.DictReader(io.StringIO(sample_data))
        
        # Track created locations
        created_locations = {}
        created_equipment = []
        
        for row in csv_data:
            # Create or get POD location
            pod_name = row['Location']
            if pod_name not in created_locations:
                pod_location, created = Location.objects.get_or_create(
                    name=pod_name,
                    defaults={
                        'parent_location': main_site,
                        'is_site': False,
                        'customer': customer,
                        'is_active': True,
                        'created_by': admin_user,
                    }
                )
                created_locations[pod_name] = pod_location
                if created:
                    self.stdout.write(f'Created location: {pod_name}')
            else:
                pod_location = created_locations[pod_name]
            
            # Create equipment
            equipment, created = Equipment.objects.get_or_create(
                asset_tag=row['Asset Tag'],
                defaults={
                    'name': f"{row['Model']} - {row['Asset Tag']}",
                    'manufacturer_serial': row['Serial Number'],
                    'manufacturer': 'Maddox',
                    'model_number': row['Model'],
                    'category': category,
                    'location': pod_location,
                    'status': 'active' if row['Status'] == 'Deployed' else 'inactive',
                    'is_active': True,
                    'created_by': admin_user,
                }
            )
            
            if created:
                created_equipment.append(equipment)
                self.stdout.write(f'Created equipment: {equipment.name} at {pod_location.name}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully populated database with:\n'
                f'- 1 customer (Project Dorothy)\n'
                f'- 1 equipment category (Transformers)\n'
                f'- 1 main site (Dorothy Site)\n'
                f'- {len(created_locations)} POD locations\n'
                f'- {len(created_equipment)} equipment items'
            )
        ) 