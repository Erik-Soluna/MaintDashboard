#!/bin/bash

# Script to fix migration conflicts and apply timezone migration
# This can be run manually if automatic resolution fails

echo "🔧 Fixing migration conflicts and applying timezone migration..."

# Navigate to app directory
cd /app

echo "📦 Step 1: Attempting to merge conflicting migrations..."
if python manage.py makemigrations --merge --noinput; then
    echo "✅ Migration merge completed successfully"
else
    echo "⚠️  Migration merge failed, trying individual app merges..."
    
    # Try merging each app individually
    echo "📦 Merging core migrations..."
    python manage.py makemigrations core --merge --noinput || echo "⚠️  Core merge failed"
    
    echo "📦 Merging maintenance migrations..."
    python manage.py makemigrations maintenance --merge --noinput || echo "⚠️  Maintenance merge failed"
    
    echo "📦 Merging equipment migrations..."
    python manage.py makemigrations equipment --merge --noinput || echo "⚠️  Equipment merge failed"
    
    echo "📦 Merging events migrations..."
    python manage.py makemigrations events --merge --noinput || echo "⚠️  Events merge failed"
fi

echo "📦 Step 2: Applying all migrations..."
if python manage.py migrate --noinput; then
    echo "✅ All migrations applied successfully"
else
    echo "⚠️  Full migration failed, trying individual app migrations..."
    
    # Try migrating each app individually
    echo "📦 Migrating core app..."
    python manage.py migrate core --noinput || echo "⚠️  Core migration failed"
    
    echo "📦 Migrating maintenance app..."
    python manage.py migrate maintenance --noinput || echo "⚠️  Maintenance migration failed"
    
    echo "📦 Migrating equipment app..."
    python manage.py migrate equipment --noinput || echo "⚠️  Equipment migration failed"
    
    echo "📦 Migrating events app..."
    python manage.py migrate events --noinput || echo "⚠️  Events migration failed"
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
    echo "🎉 Timezone migration completed successfully!"
else
    echo "❌ Timezone field still missing. Manual intervention may be required."
    echo "💡 You can try running: python manage.py migrate maintenance 0005 --fake"
fi

echo "📊 Step 4: Migration status check..."
python manage.py showmigrations maintenance

echo "🎯 Migration conflict resolution completed!"
