"""
Django management command to clear all migrations and start fresh.
This command will:
1. Drop the django_migrations table
2. Remove all migration files except __init__.py
3. Create fresh migrations
4. Apply them properly
"""

import os
import shutil
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import connection
from django.conf import settings


class Command(BaseCommand):
    help = 'Clear all migrations and start completely fresh'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompts (use with extreme caution)',
        )
        parser.add_argument(
            '--keep-data',
            action='store_true',
            help='Keep existing data (only clear migration state)',
        )

    def handle(self, *args, **options):
        """Main command handler."""
        force = options['force']
        keep_data = options['keep_data']
        
        self.stdout.write(
            self.style.WARNING('🚨 CLEARING ALL MIGRATIONS - DESTRUCTIVE OPERATION!')
        )
        
        if not force:
            confirm = input('Are you sure you want to clear all migrations? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Operation cancelled.'))
                return
        
        try:
            # Step 1: Drop django_migrations table
            self.stdout.write('🗑️  Dropping django_migrations table...')
            with connection.cursor() as cursor:
                try:
                    cursor.execute("DROP TABLE IF EXISTS django_migrations CASCADE;")
                    self.stdout.write(self.style.SUCCESS('   ✅ django_migrations table dropped'))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'   ⚠️  Could not drop django_migrations table: {e}'))
            
            # Step 2: Drop all application tables if not keeping data
            if not keep_data:
                self.stdout.write('🗑️  Dropping all application tables...')
                with connection.cursor() as cursor:
                    try:
                        # Get all tables
                        cursor.execute("""
                            SELECT tablename FROM pg_tables 
                            WHERE schemaname = 'public' 
                            AND tablename NOT LIKE 'pg_%'
                            AND tablename NOT IN ('spatial_ref_sys', 'geometry_columns', 'geography_columns')
                        """)
                        tables = [row[0] for row in cursor.fetchall()]
                        
                        # Drop tables
                        for table in tables:
                            try:
                                cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
                                self.stdout.write(f'   ✅ Dropped table: {table}')
                            except Exception as e:
                                self.stdout.write(self.style.WARNING(f'   ⚠️  Could not drop table {table}: {e}'))
                        
                        self.stdout.write(self.style.SUCCESS('   ✅ All application tables dropped'))
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'   ⚠️  Could not drop tables: {e}'))
            
            # Step 3: Remove migration files
            self.stdout.write('📁 Removing migration files...')
            apps = ['core', 'equipment', 'maintenance', 'events']
            
            for app in apps:
                app_path = os.path.join(settings.BASE_DIR, app)
                migrations_path = os.path.join(app_path, 'migrations')
                
                if os.path.exists(migrations_path):
                    # Remove all .py files except __init__.py
                    for filename in os.listdir(migrations_path):
                        if filename.endswith('.py') and filename != '__init__.py':
                            file_path = os.path.join(migrations_path, filename)
                            try:
                                os.remove(file_path)
                                self.stdout.write(f'   ✅ Removed: {app}/{filename}')
                            except Exception as e:
                                self.stdout.write(self.style.WARNING(f'   ⚠️  Could not remove {app}/{filename}: {e}'))
                    
                    # Remove .pyc files
                    for filename in os.listdir(migrations_path):
                        if filename.endswith('.pyc'):
                            file_path = os.path.join(migrations_path, filename)
                            try:
                                os.remove(file_path)
                            except Exception as e:
                                pass  # Ignore pyc removal errors
            
            self.stdout.write(self.style.SUCCESS('   ✅ Migration files removed'))
            
            # Step 4: Create fresh migrations
            self.stdout.write('📝 Creating fresh migrations...')
            try:
                call_command('makemigrations', verbosity=0)
                self.stdout.write(self.style.SUCCESS('   ✅ Fresh migrations created'))
            except Exception as e:
                raise CommandError(f'Failed to create migrations: {e}')
            
            # Step 5: Apply migrations
            self.stdout.write('🚀 Applying fresh migrations...')
            try:
                call_command('migrate', verbosity=0)
                self.stdout.write(self.style.SUCCESS('   ✅ Fresh migrations applied'))
            except Exception as e:
                raise CommandError(f'Failed to apply migrations: {e}')
            
            # Step 6: Create admin user
            self.stdout.write('👤 Creating admin user...')
            try:
                call_command('init_database', '--skip-migrations', '--admin-username', 'admin', '--admin-email', 'admin@maintenance.local', '--admin-password', 'temppass123', verbosity=0)
                self.stdout.write(self.style.SUCCESS('   ✅ Admin user created'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'   ⚠️  Could not create admin user: {e}'))
            
            self.stdout.write(
                self.style.SUCCESS('\n🎉 Fresh start completed successfully!')
            )
            
            self.stdout.write('\n📋 Summary:')
            self.stdout.write('   ✅ django_migrations table cleared')
            if not keep_data:
                self.stdout.write('   ✅ All application tables cleared')
            self.stdout.write('   ✅ Migration files removed')
            self.stdout.write('   ✅ Fresh migrations created')
            self.stdout.write('   ✅ Fresh migrations applied')
            self.stdout.write('   ✅ Admin user created')
            
            self.stdout.write('\n🔑 Login credentials:')
            self.stdout.write('   Username: admin')
            self.stdout.write('   Password: temppass123')
            
        except Exception as e:
            raise CommandError(f'Fresh start failed: {e}')
