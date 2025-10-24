#!/bin/bash

# Emergency migration fix for complex migration conflicts
# This script handles the KeyError: ('core', 'brandingsettings') issue

echo "🚨 Emergency migration fix for complex conflicts..."

# Navigate to app directory
cd /app

echo "📦 Step 1: Checking current migration status..."
python manage.py showmigrations

echo "📦 Step 2: Attempting to fake-apply problematic migrations..."

# First, let's try to fake-apply the timezone migration specifically
echo "🎯 Fake-applying timezone migration..."
if python manage.py migrate maintenance 0005_add_timezone_to_maintenance_activity --fake; then
    echo "✅ Timezone migration fake-applied successfully"
else
    echo "⚠️  Could not fake-apply timezone migration"
fi

# Try to fake-apply other problematic migrations
echo "🎯 Fake-applying core migrations..."
python manage.py migrate core 0005_add_branding_models --fake || echo "⚠️  Core branding migration fake-apply failed"
python manage.py migrate core 0012_add_breadcrumb_controls --fake || echo "⚠️  Core breadcrumb migration fake-apply failed"

echo "🎯 Fake-applying maintenance migrations..."
python manage.py migrate maintenance 0002_add_timeline_entry_types --fake || echo "⚠️  Maintenance timeline migration fake-apply failed"
python manage.py migrate maintenance 0006_globalschedule_scheduleoverride_and_more --fake || echo "⚠️  Maintenance schedule migration fake-apply failed"

echo "📦 Step 3: Verifying timezone field exists..."
if python manage.py shell -c "
from django.db import connection
try:
    with connection.cursor() as cursor:
        cursor.execute('SELECT column_name FROM information_schema.columns WHERE table_name = %s AND column_name = %s', ['maintenance_maintenanceactivity', 'timezone'])
        result = cursor.fetchone()
        if result:
            print('✅ Timezone field exists in maintenance_maintenanceactivity table')
            exit(0)
        else:
            print('❌ Timezone field does not exist in maintenance_maintenanceactivity table')
            exit(1)
except Exception as e:
    print(f'❌ Error checking timezone field: {e}')
    exit(1)
"; then
    echo "🎉 Timezone field verification successful!"
else
    echo "❌ Timezone field still missing, attempting manual SQL fix..."
    
    # Manual SQL fix as last resort
    echo "🔧 Adding timezone column manually..."
    if python manage.py shell -c "
from django.db import connection
try:
    with connection.cursor() as cursor:
        cursor.execute('ALTER TABLE maintenance_maintenanceactivity ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT %s', ['America/Chicago'])
        print('✅ Timezone column added manually')
        exit(0)
except Exception as e:
    print(f'❌ Error adding timezone column: {e}')
    exit(1)
"; then
        echo "🎉 Manual timezone column addition successful!"
    else
        echo "❌ Manual timezone column addition failed"
    fi
fi

echo "📦 Step 4: Final migration status check..."
python manage.py showmigrations maintenance

echo "📦 Step 5: Testing application startup..."
if python manage.py check --deploy; then
    echo "✅ Django configuration check passed"
else
    echo "⚠️  Django configuration check failed, but continuing..."
fi

echo "🎯 Emergency migration fix completed!"
echo "💡 If issues persist, you may need to reset the migration state or recreate the database"
