"""
Management command to ensure all required database tables exist.
This command checks for all necessary tables and creates them if missing.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.core.cache import cache
from django.conf import settings
from django.db import connection, transaction
from django.db.utils import ProgrammingError, OperationalError
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Ensure all required database tables exist and are properly configured'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of tables',
        )
        parser.add_argument(
            '--skip-cache-test',
            action='store_true',
            help='Skip cache functionality test',
        )

    def check_table_exists(self, table_name):
        """Check if a table exists in the database."""
        with connection.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    );
                """, [table_name])
                return cursor.fetchone()[0]
            except (ProgrammingError, OperationalError):
                return False

    def create_cache_table(self):
        """Create the cache table if it doesn't exist."""
        if self.check_table_exists('cache_table'):
            self.stdout.write('✅ Cache table already exists')
            return True
        
        self.stdout.write('🔧 Creating cache table...')
        
        try:
            # Try Django's createcachetable command
            call_command('createcachetable', verbosity=0)
            self.stdout.write('✅ Cache table created successfully')
            return True
        except Exception as e:
            self.stdout.write(f'⚠️  Django createcachetable failed: {str(e)}')
            
            # Try manual creation
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS cache_table (
                            cache_key varchar(255) NOT NULL PRIMARY KEY,
                            value text NOT NULL,
                            expires timestamp(6) NOT NULL
                        );
                    """)
                    
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS cache_table_expires_idx 
                        ON cache_table (expires);
                    """)
                    
                    transaction.commit()
                    self.stdout.write('✅ Cache table created manually')
                    return True
            except Exception as manual_error:
                self.stdout.write(f'❌ Manual cache table creation failed: {str(manual_error)}')
                return False

    def test_cache_functionality(self):
        """Test if the cache is working properly."""
        self.stdout.write('🧪 Testing cache functionality...')
        
        try:
            test_key = 'ensure_database_test_key'
            test_value = 'ensure_database_test_value'
            
            # Test set
            cache.set(test_key, test_value, 60)
            self.stdout.write('✅ Cache set successful')
            
            # Test get
            retrieved_value = cache.get(test_key)
            if retrieved_value == test_value:
                self.stdout.write('✅ Cache get successful')
            else:
                self.stdout.write(f'❌ Cache get failed: expected "{test_value}", got "{retrieved_value}"')
                return False
            
            # Test delete
            cache.delete(test_key)
            if cache.get(test_key) is None:
                self.stdout.write('✅ Cache delete successful')
            else:
                self.stdout.write('❌ Cache delete failed')
                return False
            
            self.stdout.write('🎉 Cache functionality test passed!')
            return True
            
        except Exception as e:
            self.stdout.write(f'❌ Cache functionality test failed: {str(e)}')
            return False

    def check_required_tables(self):
        """Check if all required tables exist."""
        required_tables = [
            'django_migrations',
            'django_content_type',
            'django_admin_log',
            'django_session',
            'auth_user',
            'auth_group',
            'auth_permission',
            'core_customer',
            'core_equipmentcategory',
            'core_location',
            'core_permission',
            'core_role',
            'core_userprofile',
            'core_modeldocument',
            'equipment_equipment',
            'equipment_equipmentcomponent',
            'equipment_equipmentdocument',
            'maintenance_maintenanceactivity',
            'maintenance_maintenanceactivitytype',
            'maintenance_maintenanceactivitytypecategory',
            'maintenance_maintenanceschedule',
            'maintenance_maintenancereport',
            'events_calendarevent',
            'django_celery_beat_periodictask',
            'django_celery_beat_periodictasks',
            'django_celery_beat_intervalschedule',
            'django_celery_beat_crontabschedule',
            'django_celery_beat_solarschedule',
            'django_celery_beat_clockedschedule',
            'cache_table',
        ]
        
        missing_tables = []
        
        for table in required_tables:
            if self.check_table_exists(table):
                self.stdout.write(f'✅ Table {table} exists')
            else:
                self.stdout.write(f'❌ Table {table} is missing')
                missing_tables.append(table)
        
        return missing_tables

    def handle(self, *args, **options):
        self.stdout.write('🚀 Starting comprehensive database check...')
        
        # Check cache backend
        cache_backend = getattr(settings, 'CACHES', {}).get('default', {}).get('BACKEND', '')
        self.stdout.write(f'Cache backend: {cache_backend}')
        
        # Check required tables
        missing_tables = self.check_required_tables()
        
        if missing_tables:
            self.stdout.write(f'⚠️  Missing tables: {", ".join(missing_tables)}')
            self.stdout.write('🔄 Running migrations to create missing tables...')
            
            try:
                # Run migrations
                call_command('migrate', verbosity=0)
                self.stdout.write('✅ Migrations completed')
                
                # Re-check tables
                missing_tables_after_migration = self.check_required_tables()
                if missing_tables_after_migration:
                    self.stdout.write(f'⚠️  Still missing tables after migration: {", ".join(missing_tables_after_migration)}')
                else:
                    self.stdout.write('✅ All tables created successfully')
                    
            except Exception as e:
                self.stdout.write(f'❌ Migration failed: {str(e)}')
                return
        
        # Handle cache table specifically
        if 'django.core.cache.backends.db.DatabaseCache' in cache_backend:
            if not self.create_cache_table():
                self.stdout.write('❌ Failed to create cache table')
                return
        
        # Test cache functionality
        if not options['skip_cache_test']:
            if not self.test_cache_functionality():
                self.stdout.write('❌ Cache functionality test failed')
                return
        
        # Final verification
        final_missing_tables = self.check_required_tables()
        if not final_missing_tables:
            self.stdout.write('🎉 Database check completed successfully!')
            self.stdout.write('✅ All required tables exist')
            self.stdout.write('✅ Cache functionality working')
        else:
            self.stdout.write(f'❌ Database check completed with issues')
            self.stdout.write(f'⚠️  Missing tables: {", ".join(final_missing_tables)}')
            return 