# PowerShell script to fix migration conflicts and apply timezone migration
# This can be run manually if automatic resolution fails

Write-Host "🔧 Fixing migration conflicts and applying timezone migration..." -ForegroundColor Cyan

# Navigate to app directory
Set-Location /app

Write-Host "📦 Step 1: Attempting to merge conflicting migrations..." -ForegroundColor Yellow
if (python manage.py makemigrations --merge --noinput) {
    Write-Host "✅ Migration merge completed successfully" -ForegroundColor Green
} else {
    Write-Host "⚠️  Migration merge failed, trying individual app merges..." -ForegroundColor Yellow
    
    # Try merging each app individually
    Write-Host "📦 Merging core migrations..." -ForegroundColor Yellow
    python manage.py makemigrations core --merge --noinput
    if ($LASTEXITCODE -ne 0) { Write-Host "⚠️  Core merge failed" -ForegroundColor Yellow }
    
    Write-Host "📦 Merging maintenance migrations..." -ForegroundColor Yellow
    python manage.py makemigrations maintenance --merge --noinput
    if ($LASTEXITCODE -ne 0) { Write-Host "⚠️  Maintenance merge failed" -ForegroundColor Yellow }
    
    Write-Host "📦 Merging equipment migrations..." -ForegroundColor Yellow
    python manage.py makemigrations equipment --merge --noinput
    if ($LASTEXITCODE -ne 0) { Write-Host "⚠️  Equipment merge failed" -ForegroundColor Yellow }
    
    Write-Host "📦 Merging events migrations..." -ForegroundColor Yellow
    python manage.py makemigrations events --merge --noinput
    if ($LASTEXITCODE -ne 0) { Write-Host "⚠️  Events merge failed" -ForegroundColor Yellow }
}

Write-Host "📦 Step 2: Applying all migrations..." -ForegroundColor Yellow
if (python manage.py migrate --noinput) {
    Write-Host "✅ All migrations applied successfully" -ForegroundColor Green
} else {
    Write-Host "⚠️  Full migration failed, trying individual app migrations..." -ForegroundColor Yellow
    
    # Try migrating each app individually
    Write-Host "📦 Migrating core app..." -ForegroundColor Yellow
    python manage.py migrate core --noinput
    if ($LASTEXITCODE -ne 0) { Write-Host "⚠️  Core migration failed" -ForegroundColor Yellow }
    
    Write-Host "📦 Migrating maintenance app..." -ForegroundColor Yellow
    python manage.py migrate maintenance --noinput
    if ($LASTEXITCODE -ne 0) { Write-Host "⚠️  Maintenance migration failed" -ForegroundColor Yellow }
    
    Write-Host "📦 Migrating equipment app..." -ForegroundColor Yellow
    python manage.py migrate equipment --noinput
    if ($LASTEXITCODE -ne 0) { Write-Host "⚠️  Equipment migration failed" -ForegroundColor Yellow }
    
    Write-Host "📦 Migrating events app..." -ForegroundColor Yellow
    python manage.py migrate events --noinput
    if ($LASTEXITCODE -ne 0) { Write-Host "⚠️  Events migration failed" -ForegroundColor Yellow }
}

Write-Host "📦 Step 3: Verifying timezone field exists..." -ForegroundColor Yellow
$timezoneCheck = python manage.py shell -c "
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
"

if ($LASTEXITCODE -eq 0) {
    Write-Host "🎉 Timezone migration completed successfully!" -ForegroundColor Green
} else {
    Write-Host "❌ Timezone field still missing. Manual intervention may be required." -ForegroundColor Red
    Write-Host "💡 You can try running: python manage.py migrate maintenance 0005 --fake" -ForegroundColor Yellow
}

Write-Host "📊 Step 4: Migration status check..." -ForegroundColor Yellow
python manage.py showmigrations maintenance

Write-Host "🎯 Migration conflict resolution completed!" -ForegroundColor Green
