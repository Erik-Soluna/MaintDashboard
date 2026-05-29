"""
Django management command to create an admin user quickly.
"""

import secrets

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from decouple import config


class Command(BaseCommand):
    help = 'Create admin user for the maintenance dashboard'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            default='admin',
            help='Admin username (default: admin)'
        )
        parser.add_argument(
            '--email',
            default='admin@maintenance.local',
            help='Admin email (default: admin@maintenance.local)'
        )
        parser.add_argument(
            '--password',
            default=None,
            help='Admin password. If omitted, falls back to the ADMIN_PASSWORD '
                 'environment variable, otherwise a strong random password is '
                 'generated and printed once.'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation if user already exists'
        )

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        force = options['force']

        # Resolve password: explicit flag > ADMIN_PASSWORD env > generated random.
        password = options['password'] or config('ADMIN_PASSWORD', default=None)
        generated_password = False
        if not password:
            password = secrets.token_urlsafe(16)
            generated_password = True

        self.stdout.write('🚀 Creating Admin User for Maintenance Dashboard')
        self.stdout.write('=' * 50)

        try:
            with transaction.atomic():
                # Check if admin user already exists
                if User.objects.filter(username=username).exists():
                    if not force:
                        existing_user = User.objects.get(username=username)
                        self.stdout.write(
                            self.style.WARNING(f'✅ Admin user "{username}" already exists')
                        )
                        self.stdout.write(f'   - Is superuser: {existing_user.is_superuser}')
                        self.stdout.write(f'   - Is active: {existing_user.is_active}')
                        self.stdout.write(f'   - Email: {existing_user.email}')
                        
                        # Show database stats
                        total_users = User.objects.count()
                        superusers = User.objects.filter(is_superuser=True).count()
                        self.stdout.write(f'\n📊 Database Status:')
                        self.stdout.write(f'   - Total users: {total_users}')
                        self.stdout.write(f'   - Superusers: {superusers}')
                        
                        self.stdout.write(f'\n🔒 Login Information:')
                        self.stdout.write(f'   - URL: http://localhost:8000/')
                        self.stdout.write(f'   - Admin: http://localhost:8000/admin/')
                        self.stdout.write(f'   - Username: {username}')
                        return
                    else:
                        # Delete existing user if force is specified
                        User.objects.filter(username=username).delete()
                        self.stdout.write(
                            self.style.WARNING(f'🗑️  Existing user "{username}" deleted (force mode)')
                        )

                # Create superuser
                admin_user = User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password,
                    first_name='System',
                    last_name='Administrator'
                )

                self.stdout.write(
                    self.style.SUCCESS(f'✅ Admin user "{username}" created successfully!')
                )
                self.stdout.write(f'   - Username: {username}')
                self.stdout.write(f'   - Email: {email}')
                self.stdout.write(f'   - Is superuser: {admin_user.is_superuser}')
                self.stdout.write(f'   - Is active: {admin_user.is_active}')

                # Show database stats
                total_users = User.objects.count()
                superusers = User.objects.filter(is_superuser=True).count()
                self.stdout.write(f'\n📊 Database Status:')
                self.stdout.write(f'   - Total users: {total_users}')
                self.stdout.write(f'   - Superusers: {superusers}')

                self.stdout.write(f'\n🔒 Login Information:')
                self.stdout.write(f'   - URL: http://localhost:8000/')
                self.stdout.write(f'   - Admin: http://localhost:8000/admin/')
                self.stdout.write(f'   - Username: {username}')

                if generated_password:
                    self.stdout.write(self.style.WARNING(
                        f'\n🔑 Generated password (shown once, store it now): {password}'
                    ))

                self.stdout.write(f'\n⚠️  SECURITY NOTE:')
                self.stdout.write(f'   Please change the password after first login!')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error creating admin user: {str(e)}')
            )
            raise