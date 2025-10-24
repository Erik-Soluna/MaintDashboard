"""
Management command to apply the conditional fields migration.
This can be used to manually apply the migration if the automatic process fails.
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Apply the conditional fields migration manually'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force the migration even if it might conflict'
        )

    def handle(self, *args, **options):
        self.stdout.write('🔧 Applying conditional fields migration...')
        
        # Check if the table already exists
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'equipment_equipmentcategoryconditionalfield'
                );
            """)
            table_exists = cursor.fetchone()[0]
        
        if table_exists:
            self.stdout.write(self.style.SUCCESS('✅ equipment_equipmentcategoryconditionalfield table already exists'))
            return
        
        self.stdout.write('📋 Table does not exist, applying migration...')
        
        try:
            # Try to apply the equipment migrations specifically
            call_command('migrate', 'equipment', verbosity=2)
            self.stdout.write(self.style.SUCCESS('✅ Equipment migrations applied successfully'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠️ Equipment migrations failed: {e}'))
            
            if options['force']:
                self.stdout.write('🔄 Attempting to apply all migrations...')
                try:
                    call_command('migrate', verbosity=2)
                    self.stdout.write(self.style.SUCCESS('✅ All migrations applied successfully'))
                except Exception as e2:
                    self.stdout.write(self.style.ERROR(f'❌ All migrations failed: {e2}'))
                    return
            
            # Check if the table was created despite the error
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'equipment_equipmentcategoryconditionalfield'
                    );
                """)
                table_exists = cursor.fetchone()[0]
            
            if table_exists:
                self.stdout.write(self.style.SUCCESS('✅ Table was created successfully despite the error'))
            else:
                self.stdout.write(self.style.ERROR('❌ Table was not created'))
        
        # Verify the table exists
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'equipment_equipmentcategoryconditionalfield'
                );
            """)
            table_exists = cursor.fetchone()[0]
        
        if table_exists:
            self.stdout.write(self.style.SUCCESS('✅ Conditional fields migration completed successfully'))
        else:
            self.stdout.write(self.style.ERROR('❌ Conditional fields migration failed'))
