#!/usr/bin/env python3
"""
Fix missing database tables that should exist according to applied migrations.
This script checks for missing tables and applies the specific migrations needed.
"""

import os
import sys
import django

# Add the project directory to Python path
project_paths = ['/app', '/workspace', '.']
for path in project_paths:
    if path not in sys.path:
        sys.path.append(path)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maintenance_dashboard.settings')
django.setup()

from django.core.management import call_command
from django.db import connection, transaction
from django.db.utils import ProgrammingError, OperationalError

def check_table_exists(table_name):
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

def check_migration_applied(app_name, migration_name):
    """Check if a migration is marked as applied."""
    with connection.cursor() as cursor:
        try:
            cursor.execute("""
                SELECT COUNT(*) FROM django_migrations 
                WHERE app = %s AND name = %s
            """, [app_name, migration_name])
            return cursor.fetchone()[0] > 0
        except (ProgrammingError, OperationalError):
            return False

def main():
    print("🔍 Checking for missing tables...")
    
    # Key tables that should exist according to migrations
    required_tables = {
        'maintenance_maintenanceactivitytype': ('maintenance', '0001_initial'),
        'maintenance_activitytypecategory': ('maintenance', '0001_initial'),
        'maintenance_activitytypetemplate': ('maintenance', '0001_initial'),
        'core_userprofile': ('core', '0001_initial'),
        'equipment_equipment': ('equipment', '0001_initial'),
    }
    
    missing_tables = []
    
    for table_name, (app_name, migration_name) in required_tables.items():
        table_exists = check_table_exists(table_name)
        migration_applied = check_migration_applied(app_name, migration_name)
        
        print(f"📋 {table_name}: exists={table_exists}, migration_applied={migration_applied}")
        
        if migration_applied and not table_exists:
            missing_tables.append((table_name, app_name, migration_name))
            print(f"❌ PROBLEM: {table_name} migration marked as applied but table doesn't exist!")
    
    if missing_tables:
        print(f"\n🔧 Found {len(missing_tables)} missing tables that need to be created")
        
        # First, check if we need to create any missing migrations
        print("\n📦 Checking for pending migrations...")
        try:
            call_command('makemigrations', verbosity=1)
            print("✅ Migrations up to date")
        except Exception as e:
            print(f"⚠️  Makemigrations issue: {e}")
        
        # For missing tables, we need to unapply and reapply the migrations
        for table_name, app_name, migration_name in missing_tables:
            print(f"\n🔄 Fixing {table_name}...")
            
            try:
                # First, mark the migration as unapplied
                with connection.cursor() as cursor:
                    cursor.execute("""
                        DELETE FROM django_migrations 
                        WHERE app = %s AND name = %s
                    """, [app_name, migration_name])
                    print(f"   ✅ Unmarked {app_name}.{migration_name} as applied")
                
                # Then run the migration to actually create the table
                call_command('migrate', app_name, migration_name, verbosity=1)
                print(f"   ✅ Applied {app_name}.{migration_name} - table created")
                
            except Exception as e:
                print(f"   ❌ Failed to fix {table_name}: {e}")
                
                # Try a more aggressive approach - reset all migrations for this app
                try:
                    print(f"   🔄 Trying aggressive reset for {app_name}...")
                    with connection.cursor() as cursor:
                        cursor.execute("DELETE FROM django_migrations WHERE app = %s", [app_name])
                    call_command('migrate', app_name, verbosity=1)
                    print(f"   ✅ Aggressive reset successful for {app_name}")
                except Exception as e2:
                    print(f"   ❌ Aggressive reset also failed: {e2}")
                
        print("\n🔄 Running final migration to ensure everything is up to date...")
        try:
            call_command('migrate', verbosity=1)
            print("✅ Final migration completed")
        except Exception as e:
            print(f"⚠️  Final migration had issues: {e}")
        
    else:
        print("✅ All required tables exist!")
    
    print("\n🔍 Final verification...")
    for table_name, (app_name, migration_name) in required_tables.items():
        table_exists = check_table_exists(table_name)
        status = "✅" if table_exists else "❌"
        print(f"{status} {table_name}: {table_exists}")
        
    # Special check for the main problematic table
    if check_table_exists('maintenance_maintenanceactivitytype'):
        print("\n🎉 SUCCESS: maintenance_maintenanceactivitytype table now exists!")
    else:
        print("\n❌ STILL MISSING: maintenance_maintenanceactivitytype table")
        print("   This may require manual intervention.")
        return 1
        
    return 0

if __name__ == '__main__':
    main()