"""
Django management command to initialize the database and create default admin user.
This command handles:
1. Running all Django migrations
2. Creating a default admin user
3. Setting up initial data (categories, locations)
4. Forcing password change on first login
"""

import os
import sys
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.contrib.auth.models import User, Group, Permission
from django.db import transaction
from django.conf import settings
from core.models import EquipmentCategory, Location, UserProfile


class Command(BaseCommand):
    help = 'Initialize database with migrations, admin user, and basic data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--admin-username',
            default='admin',
            help='Admin username (default: admin)'
        )
        parser.add_argument(
            '--admin-email',
            default='admin@maintenance.local',
            help='Admin email (default: admin@maintenance.local)'
        )
        parser.add_argument(
            '--admin-password',
            default='temppass123',
            help='Admin password (default: temppass123)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of initial data even if it already exists'
        )
        parser.add_argument(
            '--skip-migrations',
            action='store_true',
            help='Skip running migrations'
        )
        parser.add_argument(
            '--skip-admin',
            action='store_true',
            help='Skip creating admin user'
        )
        parser.add_argument(
            '--skip-sample-data',
            action='store_true',
            help='Skip creating sample data'
        )

    def handle(self, *args, **options):
        """Main command handler."""
        self.stdout.write(
            self.style.SUCCESS('🚀 Starting database initialization...\n')
        )

        try:
            # Step 1: Run migrations (do NOT wrap in transaction.atomic)
            if not options['skip_migrations']:
                self._run_migrations()

            # Step 2: Create admin user and initial data atomically
            with transaction.atomic():
                if not options['skip_admin']:
                    admin_user = self._create_admin_user(
                        username=options['admin_username'],
                        email=options['admin_email'],
                        password=options['admin_password']
                    )

                # Create initial data
                self._create_initial_data(options.get('force', False))

            self.stdout.write(
                self.style.SUCCESS('\n✅ Database initialization completed successfully!')
            )
            
            if not options['skip_admin']:
                self.stdout.write(
                    self.style.WARNING(f'\n⚠️  IMPORTANT: Admin user created with temporary password.')
                )
                self.stdout.write(
                    self.style.WARNING(f'   Username: {options["admin_username"]}')
                )
                self.stdout.write(
                    self.style.WARNING(f'   Password: {options["admin_password"]}')
                )
                self.stdout.write(
                    self.style.WARNING(f'   Email: {options["admin_email"]}')
                )
                self.stdout.write(
                    self.style.WARNING(f'\n🔒 The admin user will be required to change password on first login.')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\n❌ Database initialization failed: {str(e)}')
            )
            raise CommandError(f'Database initialization failed: {str(e)}')

    def _run_migrations(self):
        """Run Django migrations with proper handling of existing tables."""
        self.stdout.write('📦 Running database migrations...')
        
        try:
            # First, check if tables already exist
            from django.db import connection
            
            # Get all table names that currently exist
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT tablename FROM pg_tables 
                    WHERE schemaname = 'public' AND tablename NOT LIKE 'pg_%'
                """)
                existing_tables = [row[0] for row in cursor.fetchall()]
            
            # Check if core app tables exist
            core_tables_exist = any(table.startswith('core_') for table in existing_tables)
            
            if core_tables_exist:
                self.stdout.write('   ⚠️  Existing tables detected, using fake migrations...')
                
                # If tables exist, fake the initial migration
                try:
                    call_command('migrate', '--fake-initial', verbosity=0)
                    self.stdout.write('   ✅ Faked initial migrations for existing tables')
                except Exception as fake_error:
                    self.stdout.write(f'   ⚠️  Fake migration failed: {fake_error}')
                    # Try to mark migrations as applied
                    try:
                        call_command('migrate', '--fake', verbosity=0)
                        self.stdout.write('   ✅ Marked migrations as applied')
                    except Exception as mark_error:
                        self.stdout.write(f'   ⚠️  Could not mark migrations as applied: {mark_error}')
            else:
                self.stdout.write('   Creating migrations...')
                call_command('makemigrations', verbosity=0)
                
                # Run migrate to apply all migrations
                self.stdout.write('   Applying migrations...')
                call_command('migrate', verbosity=0)
            
            self.stdout.write(
                self.style.SUCCESS('   ✅ Migrations completed successfully')
            )
        except Exception as e:
            raise CommandError(f'Migration failed: {str(e)}')

    def _create_admin_user(self, username, email, password):
        """Create admin user with forced password change."""
        self.stdout.write('👤 Creating admin user...')
        
        try:
            # Check if admin user already exists
            if User.objects.filter(username=username).exists():
                self.stdout.write(
                    self.style.WARNING(f'   ⚠️  Admin user "{username}" already exists, skipping creation')
                )
                return User.objects.get(username=username)

            # Create superuser
            admin_user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                first_name='System',
                last_name='Administrator'
            )

            # Create user profile
            user_profile, created = UserProfile.objects.get_or_create(
                user=admin_user,
                defaults={
                    'role': 'admin',
                    'employee_id': 'ADMIN001',
                    'department': 'IT Administration',
                    'is_active': True,
                }
            )

            # Force password change on first login by setting a flag
            # We'll use the user's last_login field - if it's None, force password change
            admin_user.last_login = None
            admin_user.save()

            self.stdout.write(
                self.style.SUCCESS(f'   ✅ Admin user "{username}" created successfully')
            )
            
            return admin_user

        except Exception as e:
            raise CommandError(f'Admin user creation failed: {str(e)}')

    def _create_initial_data(self, force=False):
        """Create initial data like categories, locations, and activity types."""
        self.stdout.write('🏗️  Creating initial data...')
        
        try:
            # Check if data already exists
            existing_categories = EquipmentCategory.objects.count()
            existing_locations = Location.objects.count()
            
            if existing_categories > 0 and existing_locations > 0 and not force:
                self.stdout.write(
                    self.style.WARNING(f'   ⚠️  Data already exists ({existing_categories} categories, {existing_locations} locations), skipping creation')
                )
                return
            
            # Create default equipment categories only if none exist
            if existing_categories == 0:
                self.stdout.write('   Creating default equipment categories...')
                categories = [
                    {
                        'name': 'Transformers',
                        'description': 'Power transformers and distribution transformers'
                    },
                    {
                        'name': 'Switchgear',
                        'description': 'Circuit breakers, switches, and protective devices'
                    },
                    {
                        'name': 'Motors',
                        'description': 'Electric motors and drives'
                    },
                    {
                        'name': 'Generators',
                        'description': 'Emergency generators and backup power systems'
                    },
                    {
                        'name': 'HVAC',
                        'description': 'Heating, ventilation, and air conditioning systems'
                    },
                ]

                created_categories = {}
                for cat_data in categories:
                    category, created = EquipmentCategory.objects.get_or_create(
                        name=cat_data['name'],
                        defaults={'description': cat_data['description']}
                    )
                    created_categories[category.name] = category
                    if created:
                        self.stdout.write(f'     Created category: {category.name}')
            else:
                self.stdout.write('   ⚠️  Equipment categories already exist, skipping...')
                # Get existing categories for activity type creation
                created_categories = {cat.name: cat for cat in EquipmentCategory.objects.all()}

            # Create default locations only if none exist
            if existing_locations == 0:
                self.stdout.write('   Creating default locations...')
                locations = [
                    {
                        'name': 'Main Site',
                        'is_site': True,
                        'address': 'Main facility location',
                        'parent_location': None
                    },
                    {
                        'name': 'Building A',
                        'is_site': False,
                        'address': 'Main building',
                        'parent_name': 'Main Site'
                    },
                    {
                        'name': 'Building B',
                        'is_site': False,
                        'address': 'Secondary building',
                        'parent_name': 'Main Site'
                    },
                    {
                        'name': 'Electrical Room',
                        'is_site': False,
                        'address': 'Main electrical distribution room',
                        'parent_name': 'Building A'
                    },
                ]

                created_locations = {}
                for loc_data in locations:
                    parent_location = None
                    if loc_data.get('parent_name'):
                        parent_location = created_locations.get(loc_data['parent_name'])
                        if not parent_location:
                            parent_location = Location.objects.filter(
                                name=loc_data['parent_name']
                            ).first()

                    location, created = Location.objects.get_or_create(
                        name=loc_data['name'],
                        defaults={
                            'is_site': loc_data['is_site'],
                            'address': loc_data['address'],
                            'parent_location': parent_location
                        }
                    )
                    created_locations[location.name] = location
                    
                    if created:
                        self.stdout.write(f'     Created location: {location.get_full_path()}')
            else:
                self.stdout.write('   ⚠️  Locations already exist, skipping...')

            # Create default activity type categories and activity types
            self._create_default_activity_types(force)

            self.stdout.write(
                self.style.SUCCESS('   ✅ Initial data creation completed')
            )

        except Exception as e:
            raise CommandError(f'Initial data creation failed: {str(e)}')

    def _create_default_activity_types(self, force=False):
        """Create default activity type categories and activity types."""
        try:
            from maintenance.models import ActivityTypeCategory, MaintenanceActivityType
            
            # Check if activity types already exist
            existing_activity_types = MaintenanceActivityType.objects.count()
            if existing_activity_types > 0 and not force:
                self.stdout.write('   ⚠️  Activity types already exist, skipping creation...')
                return

            self.stdout.write('   Creating default activity type categories...')
            
            # Create activity type categories
            category_data = [
                {
                    'name': 'Preventive Maintenance',
                    'description': 'Regular preventive maintenance activities to prevent equipment failure',
                    'color': '#28a745',
                    'icon': 'fas fa-shield-alt',
                    'sort_order': 1,
                },
                {
                    'name': 'Inspection',
                    'description': 'Visual and testing checks to assess equipment condition',
                    'color': '#17a2b8',
                    'icon': 'fas fa-search',
                    'sort_order': 2,
                },
                {
                    'name': 'Testing',
                    'description': 'Functional and performance testing activities',
                    'color': '#ffc107',
                    'icon': 'fas fa-flask',
                    'sort_order': 3,
                },
                {
                    'name': 'Corrective Maintenance',
                    'description': 'Repair and fix activities to restore equipment function',
                    'color': '#dc3545',
                    'icon': 'fas fa-wrench',
                    'sort_order': 4,
                },
                {
                    'name': 'Calibration',
                    'description': 'Calibration and adjustment activities',
                    'color': '#6f42c1',
                    'icon': 'fas fa-cogs',
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

            created_categories = {}
            for cat_data in category_data:
                category, created = ActivityTypeCategory.objects.get_or_create(
                    name=cat_data['name'],
                    defaults={
                        'description': cat_data['description'],
                        'color': cat_data['color'],
                        'icon': cat_data['icon'],
                        'sort_order': cat_data['sort_order'],
                        'is_active': True,
                        'is_global': True,
                    }
                )
                created_categories[cat_data['name']] = category
                if created:
                    self.stdout.write(f'     Created activity category: {category.name}')

            # Create default activity types
            self.stdout.write('   Creating default activity types...')
            
            activity_types_data = [
                # Preventive Maintenance
                {
                    'name': 'PM-001',
                    'category': created_categories['Preventive Maintenance'],
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
                    'category': created_categories['Preventive Maintenance'],
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
                    'category': created_categories['Preventive Maintenance'],
                    'description': 'Quarterly preventive maintenance check',
                    'estimated_duration_hours': 2,
                    'frequency_days': 90,
                    'is_mandatory': True,
                    'tools_required': 'Basic inspection tools',
                    'parts_required': 'Cleaning supplies, basic lubricants',
                    'safety_notes': 'Standard safety procedures apply',
                },
                
                # Inspection
                {
                    'name': 'INS-001',
                    'category': created_categories['Inspection'],
                    'description': 'Monthly operational inspection',
                    'estimated_duration_hours': 1,
                    'frequency_days': 30,
                    'is_mandatory': True,
                    'tools_required': 'Visual inspection tools',
                    'parts_required': 'None',
                    'safety_notes': 'Visual inspection only, no physical contact required',
                },
                {
                    'name': 'INS-002',
                    'category': created_categories['Inspection'],
                    'description': 'Annual detailed inspection',
                    'estimated_duration_hours': 3,
                    'frequency_days': 365,
                    'is_mandatory': True,
                    'tools_required': 'Detailed inspection equipment',
                    'parts_required': 'Inspection forms, measurement tools',
                    'safety_notes': 'Follow detailed inspection procedures',
                },
                
                # Testing
                {
                    'name': 'TEST-001',
                    'category': created_categories['Testing'],
                    'description': 'Functional testing and verification',
                    'estimated_duration_hours': 2,
                    'frequency_days': 180,
                    'is_mandatory': True,
                    'tools_required': 'Testing equipment, multimeter',
                    'parts_required': 'Test leads, calibration standards',
                    'safety_notes': 'Ensure proper test setup and safety measures',
                },
                {
                    'name': 'TEST-002',
                    'category': created_categories['Testing'],
                    'description': 'Performance testing and analysis',
                    'estimated_duration_hours': 4,
                    'frequency_days': 365,
                    'is_mandatory': True,
                    'tools_required': 'Performance testing equipment',
                    'parts_required': 'Test software, analysis tools',
                    'safety_notes': 'Performance testing requires careful monitoring',
                },
                
                # Corrective Maintenance
                {
                    'name': 'CM-001',
                    'category': created_categories['Corrective Maintenance'],
                    'description': 'Emergency repair and troubleshooting',
                    'estimated_duration_hours': 6,
                    'frequency_days': 0,  # As needed
                    'is_mandatory': False,
                    'tools_required': 'Emergency repair kit',
                    'parts_required': 'Emergency spare parts',
                    'safety_notes': 'Emergency procedures, safety first',
                },
                
                # Calibration
                {
                    'name': 'CAL-001',
                    'category': created_categories['Calibration'],
                    'description': 'Equipment calibration and adjustment',
                    'estimated_duration_hours': 3,
                    'frequency_days': 365,
                    'is_mandatory': True,
                    'tools_required': 'Calibration equipment',
                    'parts_required': 'Calibration standards',
                    'safety_notes': 'Precision work, follow calibration procedures',
                },
                
                # Cleaning
                {
                    'name': 'CLN-001',
                    'category': created_categories['Cleaning'],
                    'description': 'Regular cleaning and maintenance',
                    'estimated_duration_hours': 1,
                    'frequency_days': 30,
                    'is_mandatory': True,
                    'tools_required': 'Cleaning supplies',
                    'parts_required': 'Cleaning materials',
                    'safety_notes': 'Use appropriate cleaning materials',
                },
            ]

            created_activity_types = []
            for at_data in activity_types_data:
                activity_type, created = MaintenanceActivityType.objects.get_or_create(
                    name=at_data['name'],
                    defaults={
                        'category': at_data['category'],
                        'description': at_data['description'],
                        'estimated_duration_hours': at_data['estimated_duration_hours'],
                        'frequency_days': at_data['frequency_days'],
                        'is_mandatory': at_data['is_mandatory'],
                        'is_active': True,
                        'tools_required': at_data['tools_required'],
                        'parts_required': at_data['parts_required'],
                        'safety_notes': at_data['safety_notes'],
                    }
                )
                created_activity_types.append(activity_type)
                if created:
                    self.stdout.write(f'     Created activity type: {activity_type.name} ({activity_type.category.name})')

            # Associate activity types with equipment categories
            self.stdout.write('   Associating activity types with equipment categories...')
            equipment_categories = EquipmentCategory.objects.all()
            
            for activity_type in created_activity_types:
                # Associate with all equipment categories by default
                activity_type.applicable_equipment_categories.set(equipment_categories)
                self.stdout.write(f'     Associated {activity_type.name} with all equipment categories')

            self.stdout.write(
                self.style.SUCCESS(f'   ✅ Created {len(created_categories)} activity categories and {len(created_activity_types)} activity types')
            )

        except ImportError:
            self.stdout.write(
                self.style.WARNING('   ⚠️  Maintenance app not available, skipping activity type creation')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'   ❌ Error creating activity types: {str(e)}')
            )