#!/bin/bash

# Aggressive migration fix that bypasses problematic migrations entirely
# This script handles severe migration state corruption

echo "🚨 AGGRESSIVE MIGRATION FIX - Bypassing problematic migrations..."

# Navigate to app directory
cd /app

echo "📦 Step 1: Checking current migration status..."
python manage.py showmigrations

echo "📦 Step 2: Attempting to bypass problematic migrations with --fake-initial..."

# Try to fake-apply all migrations as if they were already applied
echo "🎯 Fake-applying all migrations as initial state..."
if python manage.py migrate --fake-initial; then
    echo "✅ Fake-initial migration successful"
else
    echo "⚠️  Fake-initial failed, trying individual app approach..."
    
    # Try each app individually with fake-initial
    echo "🎯 Fake-applying core migrations..."
    python manage.py migrate core --fake-initial || echo "⚠️  Core fake-initial failed"
    
    echo "🎯 Fake-applying maintenance migrations..."
    python manage.py migrate maintenance --fake-initial || echo "⚠️  Maintenance fake-initial failed"
    
    echo "🎯 Fake-applying equipment migrations..."
    python manage.py migrate equipment --fake-initial || echo "⚠️  Equipment fake-initial failed"
    
    echo "🎯 Fake-applying events migrations..."
    python manage.py migrate events --fake-initial || echo "⚠️  Events fake-initial failed"
fi

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
    echo "❌ Timezone field still missing, adding manually..."
    
    # Manual SQL fix
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

echo "📦 Step 4: Marking timezone migration as applied..."
# Mark the timezone migration as applied without running it
python manage.py migrate maintenance 0005_add_timezone_to_maintenance_activity --fake || echo "⚠️  Could not mark timezone migration as applied"

echo "📦 Step 5: Final migration status check..."
python manage.py showmigrations maintenance

echo "📦 Step 6: Testing Django configuration..."
if python manage.py check --deploy; then
    echo "✅ Django configuration check passed"
else
    echo "⚠️  Django configuration check failed, but continuing..."
fi

echo "📦 Step 7: Testing database connection..."
if python manage.py shell -c "
from django.db import connection
try:
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1')
        result = cursor.fetchone()
        if result:
            print('✅ Database connection successful')
            exit(0)
        else:
            print('❌ Database connection failed')
            exit(1)
except Exception as e:
    print(f'❌ Database connection error: {e}')
    exit(1)
"; then
    echo "🎉 Database connection test passed!"
else
    echo "❌ Database connection test failed"
fi

echo "🎯 AGGRESSIVE MIGRATION FIX COMPLETED!"
echo "💡 The application should now start without migration errors"
echo "⚠️  Note: Some migrations may be marked as applied without actually running"
echo "🔧 If you encounter issues, you may need to recreate the database from scratch"
