#!/bin/bash
# Script to run the timezone fix directly on the server
# This bypasses the migration issues and adds the timezone field directly

echo "🚀 Running timezone fix on server..."

# Connect to the running container and run the timezone fix
docker exec -it $(docker ps --filter "name=maintenance-dashboard" --format "{{.ID}}" | head -1) bash -c "
    echo '🔧 Adding timezone field to maintenance_maintenanceactivity table...'
    
    # Get database connection info
    DB_NAME=\$(python manage.py shell -c \"from django.conf import settings; print(settings.DATABASES['default']['NAME'])\" 2>/dev/null || echo 'maintenance_dashboard_dev')
    DB_USER=\$(python manage.py shell -c \"from django.conf import settings; print(settings.DATABASES['default']['USER'])\" 2>/dev/null || echo 'maintenance_user_dev')
    DB_HOST=\$(python manage.py shell -c \"from django.conf import settings; print(settings.DATABASES['default']['HOST'])\" 2>/dev/null || echo 'db-dev')
    DB_PORT=\$(python manage.py shell -c \"from django.conf import settings; print(settings.DATABASES['default']['PORT'])\" 2>/dev/null || echo '5432')
    DB_PASSWORD=\$(python manage.py shell -c \"from django.conf import settings; print(settings.DATABASES['default']['PASSWORD'])\" 2>/dev/null || echo 'DevPassword2024!')
    
    echo \"Database: \$DB_NAME\"
    echo \"User: \$DB_USER\"
    echo \"Host: \$DB_HOST\"
    echo \"Port: \$DB_PORT\"
    
    # Add the timezone column
    echo 'Adding timezone column...'
    if PGPASSWORD=\"\$DB_PASSWORD\" psql -h \"\$DB_HOST\" -p \"\$DB_PORT\" -U \"\$DB_USER\" -d \"\$DB_NAME\" -c \"ALTER TABLE maintenance_maintenanceactivity ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT 'America/Chicago';\" 2>/dev/null; then
        echo '✅ Timezone column added successfully!'
    else
        echo '❌ Failed to add timezone column'
        exit 1
    fi
    
    # Test Django access
    echo 'Testing Django model access...'
    if python manage.py shell -c \"from maintenance.models import MaintenanceActivity; print('MaintenanceActivity count:', MaintenanceActivity.objects.count())\" 2>/dev/null; then
        echo '✅ Django model access working!'
    else
        echo '❌ Django model access failed'
        exit 1
    fi
    
    echo '🎉 Timezone fix completed successfully!'
"

echo "✅ Timezone fix script completed!"
