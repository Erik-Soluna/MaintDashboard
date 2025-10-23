"""
Management command to fix migration state for conditional fields.
This manually marks the migration as applied.
"""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Fix migration state for conditional fields table'

    def handle(self, *args, **options):
        self.stdout.write('🔧 Fixing migration state...')
        
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
        
        if not table_exists:
            self.stdout.write(self.style.ERROR('❌ Table does not exist - cannot mark migration as applied'))
            return
        
        # Check if migration is already marked as applied
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
        
        if migration_applied:
            self.stdout.write(self.style.SUCCESS('✅ Migration already marked as applied'))
            return
        
        # Mark migration as applied
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO django_migrations (app, name, applied) 
                    VALUES ('equipment', '0004_equipmentcategoryconditionalfield', NOW());
                """)
            self.stdout.write(self.style.SUCCESS('✅ Migration marked as applied successfully'))
            
            # Verify
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) FROM django_migrations 
                    WHERE app = 'equipment' AND name = '0004_equipmentcategoryconditionalfield';
                """)
                count = cursor.fetchone()[0]
                if count > 0:
                    self.stdout.write(self.style.SUCCESS('✅ Verification successful - migration state fixed'))
                else:
                    self.stdout.write(self.style.ERROR('❌ Verification failed - migration not marked'))
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Failed to mark migration as applied: {e}'))
