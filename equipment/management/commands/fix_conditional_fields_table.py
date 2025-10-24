"""
Management command to fix the conditional fields table issue.
This command manually applies the conditional fields migration if it's missing.
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.core.management import call_command
from django.db.utils import OperationalError


class Command(BaseCommand):
    help = 'Fix conditional fields table by applying migration manually'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreate the table even if it exists'
        )
        parser.add_argument(
            '--fake-reset',
            action='store_true',
            help='Reset the migration state and reapply'
        )

    def handle(self, *args, **options):
        self.stdout.write('🔧 Checking conditional fields table...')
        
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
        
        self.stdout.write(f'📊 Status: Table exists = {table_exists}, Migration applied = {migration_applied}')
        
        if table_exists and not options['force']:
            self.stdout.write(self.style.SUCCESS('✅ Conditional fields table already exists'))
            return
        
        # Handle the case where migration is marked as applied but table doesn't exist
        if migration_applied and not table_exists:
            self.stdout.write(self.style.WARNING('⚠️ Migration marked as applied but table missing - fixing migration state...'))
            
            if options['fake_reset']:
                # Remove the migration record
                try:
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            DELETE FROM django_migrations 
                            WHERE app = 'equipment' AND name = '0004_equipmentcategoryconditionalfield';
                        """)
                    self.stdout.write('✅ Removed incorrect migration record')
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'❌ Failed to remove migration record: {e}'))
                    return
            else:
                self.stdout.write(self.style.WARNING('💡 Use --fake-reset to reset migration state'))
                self.stdout.write('🔄 Attempting manual table creation...')
                self._create_table_manually()
                return
        
        # Try to apply the migration
        try:
            self.stdout.write('📦 Applying equipment migration...')
            call_command('migrate', 'equipment', verbosity=1)
            self.stdout.write(self.style.SUCCESS('✅ Migration applied successfully'))
            
            # Verify table was created
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'equipment_equipmentcategoryconditionalfield'
                    );
                """)
                table_exists = cursor.fetchone()[0]
            
            if table_exists:
                self.stdout.write(self.style.SUCCESS('✅ Conditional fields table verified'))
                
                # Create example data if table is empty
                try:
                    from equipment.models import EquipmentCategoryConditionalField
                    count = EquipmentCategoryConditionalField.objects.count()
                    if count == 0:
                        self.stdout.write('📝 Creating example conditional fields...')
                        call_command('setup_conditional_fields_example')
                        self.stdout.write(self.style.SUCCESS('✅ Example data created'))
                    else:
                        self.stdout.write(f'ℹ️ Table contains {count} conditional field(s)')
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'⚠️ Could not create example data: {e}'))
            else:
                self.stdout.write(self.style.ERROR('❌ Table still does not exist after migration'))
                self.stdout.write('🔄 Attempting manual table creation...')
                self._create_table_manually()
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Migration failed: {e}'))
            self.stdout.write('🔄 Attempting manual table creation...')
            self._create_table_manually()
    
    def _create_table_manually(self):
        """Create the table manually as a fallback."""
        try:
            with connection.cursor() as cursor:
                # Create the table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS equipment_equipmentcategoryconditionalfield (
                        id SERIAL PRIMARY KEY,
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        created_by_id INTEGER,
                        updated_by_id INTEGER,
                        source_category_id INTEGER NOT NULL,
                        target_category_id INTEGER NOT NULL,
                        field_id INTEGER NOT NULL,
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        override_label VARCHAR(200) NOT NULL DEFAULT '',
                        override_help_text TEXT NOT NULL DEFAULT '',
                        override_required BOOLEAN,
                        override_default_value TEXT NOT NULL DEFAULT '',
                        override_sort_order INTEGER,
                        override_field_group VARCHAR(100) NOT NULL DEFAULT ''
                    );
                """)
                
                # Create indexes
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS equipment_equipmentcategoryconditionalfield_source_category_id 
                    ON equipment_equipmentcategoryconditionalfield(source_category_id);
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS equipment_equipmentcategoryconditionalfield_target_category_id 
                    ON equipment_equipmentcategoryconditionalfield(target_category_id);
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS equipment_equipmentcategoryconditionalfield_field_id 
                    ON equipment_equipmentcategoryconditionalfield(field_id);
                """)
                cursor.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS equipment_equipmentcategoryconditionalfield_target_category_field_unique 
                    ON equipment_equipmentcategoryconditionalfield(target_category_id, field_id);
                """)
                
                # Mark migration as applied
                cursor.execute("""
                    INSERT INTO django_migrations (app, name, applied) 
                    VALUES ('equipment', '0004_equipmentcategoryconditionalfield', NOW())
                    ON CONFLICT (app, name) DO NOTHING;
                """)
                
            self.stdout.write(self.style.SUCCESS('✅ Table created manually and migration marked as applied'))
            
            # Create example data
            try:
                from equipment.models import EquipmentCategoryConditionalField
                count = EquipmentCategoryConditionalField.objects.count()
                if count == 0:
                    self.stdout.write('📝 Creating example conditional fields...')
                    call_command('setup_conditional_fields_example')
                    self.stdout.write(self.style.SUCCESS('✅ Example data created'))
                else:
                    self.stdout.write(f'ℹ️ Table contains {count} conditional field(s)')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'⚠️ Could not create example data: {e}'))
                
        except Exception as manual_error:
            self.stdout.write(self.style.ERROR(f'❌ Manual table creation failed: {manual_error}'))
            self.stdout.write(self.style.ERROR('💡 Please check your database permissions and try again'))
