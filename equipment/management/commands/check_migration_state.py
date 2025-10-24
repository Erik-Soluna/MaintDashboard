"""
Management command to check migration state for conditional fields.
This helps diagnose migration issues.
"""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Check migration state for conditional fields table'

    def handle(self, *args, **options):
        self.stdout.write('🔍 Checking migration state...')
        
        # Check if table exists
        table_exists = False
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'equipment_equipmentcategoryconditionalfield'
                    );
                """)
                table_exists = cursor.fetchone()[0]
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error checking table: {e}'))
            return
        
        # Check if migration is marked as applied
        migration_applied = False
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) FROM django_migrations 
                    WHERE app = 'equipment' AND name = '0004_equipmentcategoryconditionalfield';
                """)
                migration_applied = cursor.fetchone()[0] > 0
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠️ Could not check migration state: {e}'))
        
        # Check all equipment migrations
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT name, applied FROM django_migrations 
                    WHERE app = 'equipment' 
                    ORDER BY applied;
                """)
                migrations = cursor.fetchall()
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠️ Could not list migrations: {e}'))
            migrations = []
        
        # Display results
        self.stdout.write('📊 Migration State Report:')
        self.stdout.write('=' * 50)
        self.stdout.write(f'Table exists: {"✅ Yes" if table_exists else "❌ No"}')
        self.stdout.write(f'Migration applied: {"✅ Yes" if migration_applied else "❌ No"}')
        
        if table_exists and migration_applied:
            self.stdout.write(self.style.SUCCESS('✅ Everything looks good!'))
        elif not table_exists and not migration_applied:
            self.stdout.write(self.style.WARNING('⚠️ Table and migration both missing - run migrations'))
        elif not table_exists and migration_applied:
            self.stdout.write(self.style.ERROR('❌ Migration marked as applied but table missing!'))
            self.stdout.write('💡 Run: python manage.py fix_conditional_fields_table --fake-reset')
        elif table_exists and not migration_applied:
            self.stdout.write(self.style.WARNING('⚠️ Table exists but migration not marked as applied'))
            self.stdout.write('💡 Run: python manage.py migrate equipment --fake 0004')
        
        # Show all equipment migrations
        if migrations:
            self.stdout.write('\n📋 All Equipment Migrations:')
            for name, applied in migrations:
                status = "✅" if name == '0004_equipmentcategoryconditionalfield' else "  "
                self.stdout.write(f'{status} {name} - {applied}')
        
        # Check for unapplied migrations
        try:
            from django.core.management import call_command
            from io import StringIO
            
            output = StringIO()
            call_command('showmigrations', 'equipment', stdout=output)
            output.seek(0)
            migration_output = output.read()
            
            if '[ ]' in migration_output:
                self.stdout.write('\n⚠️ Unapplied migrations detected:')
                for line in migration_output.split('\n'):
                    if '[ ]' in line:
                        self.stdout.write(f'  {line.strip()}')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠️ Could not check unapplied migrations: {e}'))
