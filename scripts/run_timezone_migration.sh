#!/bin/bash

# Script to run timezone migration for maintenance activities
# This should be run on the server after deployment

echo "🔄 Running timezone migration for maintenance activities..."

# Navigate to app directory
cd /app

# Run the migration
echo "📦 Applying maintenance app migration..."
python manage.py migrate maintenance

# Check migration status
echo "✅ Migration status:"
python manage.py showmigrations maintenance

echo "🎉 Timezone migration completed successfully!"
echo "The timezone field has been added to maintenance_maintenanceactivity table."
