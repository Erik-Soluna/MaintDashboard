# Test calendar API endpoint to diagnose the blank calendar issue

Write-Host "🔍 CALENDAR API DIAGNOSTIC TEST" -ForegroundColor Cyan
Write-Host "Testing the fetch_unified_events API endpoint..." -ForegroundColor Yellow
Write-Host ""

# Navigate to app directory
Set-Location /app

Write-Host "📦 Step 1: Testing Django application health..." -ForegroundColor Cyan
if (python manage.py check --deploy) {
    Write-Host "✅ Django configuration check passed" -ForegroundColor Green
} else {
    Write-Host "❌ Django configuration check failed" -ForegroundColor Red
    Write-Host "This could be causing the calendar loading issue" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "📦 Step 2: Testing database connection..." -ForegroundColor Cyan
$dbTest = python manage.py shell -c "
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
"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Database connection test passed" -ForegroundColor Green
} else {
    Write-Host "❌ Database connection test failed" -ForegroundColor Red
    Write-Host "This is likely causing the calendar loading issue" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "📦 Step 3: Testing MaintenanceActivity model..." -ForegroundColor Cyan
$maintenanceTest = python manage.py shell -c "
try:
    from maintenance.models import MaintenanceActivity
    print('✅ MaintenanceActivity model can be imported')
    
    # Check if timezone field exists
    if hasattr(MaintenanceActivity, 'timezone'):
        print('✅ Timezone field exists on MaintenanceActivity model')
    else:
        print('❌ Timezone field missing from MaintenanceActivity model')
        print('This is likely causing the calendar API to fail')
        
    # Try to count activities
    try:
        count = MaintenanceActivity.objects.count()
        print(f'✅ Found {count} maintenance activities in database')
    except Exception as e:
        print(f'❌ Error querying MaintenanceActivity: {e}')
        print('This is likely causing the calendar API to fail')
        
except Exception as e:
    print(f'❌ Error testing MaintenanceActivity model: {e}')
    print('This is likely causing the calendar API to fail')
"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ MaintenanceActivity model test completed" -ForegroundColor Green
} else {
    Write-Host "❌ MaintenanceActivity model test failed" -ForegroundColor Red
}

Write-Host ""
Write-Host "📦 Step 4: Testing CalendarEvent model..." -ForegroundColor Cyan
$eventTest = python manage.py shell -c "
try:
    from events.models import CalendarEvent
    print('✅ CalendarEvent model can be imported')
    
    # Try to count events
    try:
        count = CalendarEvent.objects.count()
        print(f'✅ Found {count} calendar events in database')
    except Exception as e:
        print(f'❌ Error querying CalendarEvent: {e}')
        
except Exception as e:
    print(f'❌ Error testing CalendarEvent model: {e}')
"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ CalendarEvent model test completed" -ForegroundColor Green
} else {
    Write-Host "❌ CalendarEvent model test failed" -ForegroundColor Red
}

Write-Host ""
Write-Host "📦 Step 5: Testing fetch_unified_events API directly..." -ForegroundColor Cyan
$apiTest = python manage.py shell -c "
import json
from django.test import RequestFactory
from django.contrib.auth.models import User
from events.views import fetch_unified_events

try:
    # Create a test request
    factory = RequestFactory()
    request = factory.get('/events/api/unified/?start=2025-01-01&end=2025-12-31')
    
    # Get or create a test user
    user, created = User.objects.get_or_create(
        username='test_user',
        defaults={'is_staff': True, 'is_superuser': True}
    )
    request.user = user
    
    # Call the API endpoint
    response = fetch_unified_events(request)
    
    if response.status_code == 200:
        data = json.loads(response.content)
        if isinstance(data, list):
            print(f'✅ fetch_unified_events API returned {len(data)} events')
        else:
            print(f'⚠️  fetch_unified_events API returned non-list data: {type(data)}')
            if 'error' in data:
                print(f'❌ API Error: {data.get(\"error\")}')
    else:
        print(f'❌ fetch_unified_events API returned status {response.status_code}')
        print(f'Response: {response.content.decode()}')
        
except Exception as e:
    print(f'❌ Error testing fetch_unified_events API: {e}')
    import traceback
    print('Traceback:')
    print(traceback.format_exc())
"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ fetch_unified_events API test completed" -ForegroundColor Green
} else {
    Write-Host "❌ fetch_unified_events API test failed" -ForegroundColor Red
}

Write-Host ""
Write-Host "🎯 DIAGNOSTIC COMPLETE!" -ForegroundColor Green
Write-Host "If any tests failed above, those are likely the cause of the blank calendar." -ForegroundColor Yellow
Write-Host "💡 Run the simple timezone fix if the MaintenanceActivity model has issues:" -ForegroundColor Cyan
Write-Host "   ./scripts/simple_timezone_fix.sh" -ForegroundColor White
