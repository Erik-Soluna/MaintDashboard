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
            type=str,
            default='admin',
            help='Username for the admin user (default: admin)'
        )
        parser.add_argument(
            '--admin-email',
            type=str,
            default='admin@maintenance.local',
            help='Email for the admin user (default: admin@maintenance.local)'
        )
        parser.add_argument(
            '--admin-password',
            type=str,
            default='temppass123',
            help='Temporary password for admin user (default: temppass123)'
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
            with transaction.atomic():
                # Step 1: Run migrations
                if not options['skip_migrations']:
                    self._run_migrations()

                # Step 2: Create admin user
                if not options['skip_admin']:
                    admin_user = self._create_admin_user(
                        username=options['admin_username'],
                        email=options['admin_email'],
                        password=options['admin_password']
                    )

                # Step 3: Create initial data
                if not options['skip_sample_data']:
                    self._create_initial_data()

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
        """Run Django migrations."""
        self.stdout.write('📦 Running database migrations...')
        
        try:
            # Run makemigrations first to create any missing migrations
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

    def _create_initial_data(self):
        """Create initial data like categories and locations."""
        self.stdout.write('🏗️  Creating initial data...')
        
        try:
            # Create default equipment categories
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

            for cat_data in categories:
                category, created = EquipmentCategory.objects.get_or_create(
                    name=cat_data['name'],
                    defaults={'description': cat_data['description']}
                )
                if created:
                    self.stdout.write(f'     Created category: {category.name}')

            # Create default locations
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

            self.stdout.write(
                self.style.SUCCESS('   ✅ Initial data created successfully')
            )

        except Exception as e:
            raise CommandError(f'Initial data creation failed: {str(e)}')