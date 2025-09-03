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
        
        if table_exists and not options['force']:
            self.stdout.write(self.style.SUCCESS('✅ Conditional fields table already exists'))
            return
        
        if options['force']:
            self.stdout.write('🔄 Force mode: recreating table...')
        
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
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Migration failed: {e}'))
            
            # Try to create table manually as fallback
            self.stdout.write('🔄 Attempting manual table creation...')
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS equipment_equipmentcategoryconditionalfield (
                            id SERIAL PRIMARY KEY,
                            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                            updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
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
                    
                self.stdout.write(self.style.SUCCESS('✅ Table created manually'))
                
            except Exception as manual_error:
                self.stdout.write(self.style.ERROR(f'❌ Manual table creation failed: {manual_error}'))
                self.stdout.write(self.style.ERROR('💡 Please check your database permissions and try again'))
