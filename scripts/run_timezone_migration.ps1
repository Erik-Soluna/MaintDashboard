# PowerShell script to run timezone migration for maintenance activities
# This should be run on the server after deployment

Write-Host "🔄 Running timezone migration for maintenance activities..." -ForegroundColor Cyan

# Navigate to app directory
Set-Location /app

# Run the migration
Write-Host "📦 Applying maintenance app migration..." -ForegroundColor Yellow
python manage.py migrate maintenance

# Check migration status
Write-Host "✅ Migration status:" -ForegroundColor Green
python manage.py showmigrations maintenance

Write-Host "🎉 Timezone migration completed successfully!" -ForegroundColor Green
Write-Host "The timezone field has been added to maintenance_maintenanceactivity table." -ForegroundColor Green
