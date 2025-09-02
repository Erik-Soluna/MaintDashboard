# Comprehensive System Health Check for Maintenance Dashboard
# Categorizes issues and provides actionable solutions

Write-Host "🏥 SYSTEM HEALTH CHECK - Maintenance Dashboard" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# Navigate to app directory
Set-Location /app

# Initialize counters
$TOTAL_CHECKS = 0
$PASSED_CHECKS = 0
$FAILED_CHECKS = 0
$WARNING_CHECKS = 0

# Function to run a check and categorize results
function Run-Check {
    param(
        [string]$Category,
        [string]$CheckName,
        [string]$Command,
        [string]$FixSuggestion = ""
    )
    
    $script:TOTAL_CHECKS++
    
    Write-Host "🔍 [$Category] $CheckName" -ForegroundColor Yellow
    
    try {
        Invoke-Expression $Command | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "   ✅ PASS" -ForegroundColor Green
            $script:PASSED_CHECKS++
        } else {
            Write-Host "   ❌ FAIL" -ForegroundColor Red
            $script:FAILED_CHECKS++
            if ($FixSuggestion) {
                Write-Host "   💡 Fix: $FixSuggestion" -ForegroundColor Cyan
            }
        }
    } catch {
        Write-Host "   ❌ FAIL" -ForegroundColor Red
        $script:FAILED_CHECKS++
        if ($FixSuggestion) {
            Write-Host "   💡 Fix: $FixSuggestion" -ForegroundColor Cyan
        }
    }
    Write-Host ""
}

# Function to run a warning check
function Run-WarningCheck {
    param(
        [string]$Category,
        [string]$CheckName,
        [string]$Command,
        [string]$WarningMessage = ""
    )
    
    $script:TOTAL_CHECKS++
    
    Write-Host "🔍 [$Category] $CheckName" -ForegroundColor Yellow
    
    try {
        Invoke-Expression $Command | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "   ✅ PASS" -ForegroundColor Green
            $script:PASSED_CHECKS++
        } else {
            Write-Host "   ⚠️  WARNING" -ForegroundColor Yellow
            $script:WARNING_CHECKS++
            if ($WarningMessage) {
                Write-Host "   💡 Note: $WarningMessage" -ForegroundColor Cyan
            }
        }
    } catch {
        Write-Host "   ⚠️  WARNING" -ForegroundColor Yellow
        $script:WARNING_CHECKS++
        if ($WarningMessage) {
            Write-Host "   💡 Note: $WarningMessage" -ForegroundColor Cyan
        }
    }
    Write-Host ""
}

Write-Host "📋 CATEGORY 1: CORE APPLICATION HEALTH" -ForegroundColor Magenta
Write-Host "======================================" -ForegroundColor Magenta

Run-Check "CORE" "Django Configuration" "python manage.py check --deploy" "Check Django settings and configuration"
Run-Check "CORE" "Database Connection" "python manage.py shell -c 'from django.db import connection; connection.cursor().execute(\"SELECT 1\")'" "Check database connectivity and credentials"
Run-Check "CORE" "Static Files" "python manage.py collectstatic --noinput" "Run collectstatic to ensure static files are available"

Write-Host "📋 CATEGORY 2: DATABASE SCHEMA INTEGRITY" -ForegroundColor Magenta
Write-Host "=======================================" -ForegroundColor Magenta

Run-Check "SCHEMA" "MaintenanceActivity Model" "python manage.py shell -c 'from maintenance.models import MaintenanceActivity; MaintenanceActivity.objects.count()'" "Run: ./scripts/simple_timezone_fix.sh"
Run-Check "SCHEMA" "Timezone Field Exists" "python manage.py shell -c 'from maintenance.models import MaintenanceActivity; hasattr(MaintenanceActivity, \"timezone\")'" "Run: ./scripts/simple_timezone_fix.sh"
Run-Check "SCHEMA" "CalendarEvent Model" "python manage.py shell -c 'from events.models import CalendarEvent; CalendarEvent.objects.count()'" "Check events app migrations"
Run-Check "SCHEMA" "Equipment Model" "python manage.py shell -c 'from equipment.models import Equipment; Equipment.objects.count()'" "Check equipment app migrations"
Run-Check "SCHEMA" "Location Model" "python manage.py shell -c 'from core.models import Location; Location.objects.count()'" "Check core app migrations"

Write-Host "📋 CATEGORY 3: API ENDPOINTS FUNCTIONALITY" -ForegroundColor Magenta
Write-Host "=========================================" -ForegroundColor Magenta

Run-Check "API" "fetch_unified_events API" "python manage.py shell -c '
import json
from django.test import RequestFactory
from django.contrib.auth.models import User
from events.views import fetch_unified_events

factory = RequestFactory()
request = factory.get(\"/events/api/unified/?start=2025-01-01&end=2025-12-31\")
user, _ = User.objects.get_or_create(username=\"test_user\", defaults={\"is_staff\": True, \"is_superuser\": True})
request.user = user
response = fetch_unified_events(request)
exit(0 if response.status_code == 200 else 1)
'" "Run: ./scripts/simple_timezone_fix.sh"

Run-Check "API" "fetch_events API" "python manage.py shell -c '
import json
from django.test import RequestFactory
from django.contrib.auth.models import User
from events.views import fetch_events

factory = RequestFactory()
request = factory.get(\"/events/api/events/?start=2025-01-01&end=2025-12-31\")
user, _ = User.objects.get_or_create(username=\"test_user\", defaults={\"is_staff\": True, \"is_superuser\": True})
request.user = user
response = fetch_events(request)
exit(0 if response.status_code == 200 else 1)
'" "Check events app and database schema"

Write-Host "📋 CATEGORY 4: CALENDAR SPECIFIC ISSUES" -ForegroundColor Magenta
Write-Host "======================================" -ForegroundColor Magenta

Run-Check "CALENDAR" "Calendar View Renders" "python manage.py shell -c '
from django.test import RequestFactory
from django.contrib.auth.models import User
from events.views import calendar_view

factory = RequestFactory()
request = factory.get(\"/events/calendar/\")
user, _ = User.objects.get_or_create(username=\"test_user\", defaults={\"is_staff\": True, \"is_superuser\": True})
request.user = user
response = calendar_view(request)
exit(0 if response.status_code == 200 else 1)
'" "Check calendar view and template rendering"

Run-WarningCheck "CALENDAR" "Maintenance Activities Count" "python manage.py shell -c 'from maintenance.models import MaintenanceActivity; count = MaintenanceActivity.objects.count(); exit(0 if count > 0 else 1)'" "No maintenance activities found - calendar may appear empty"

Run-WarningCheck "CALENDAR" "Calendar Events Count" "python manage.py shell -c 'from events.models import CalendarEvent; count = CalendarEvent.objects.count(); exit(0 if count > 0 else 1)'" "No calendar events found - calendar may appear empty"

Write-Host "📋 CATEGORY 5: MIGRATION STATUS" -ForegroundColor Magenta
Write-Host "==============================" -ForegroundColor Magenta

Run-Check "MIGRATIONS" "Migration Status" "python manage.py showmigrations --plan | Select-String -Pattern '\[ \]' | Measure-Object | ForEach-Object { exit(0 if $_.Count -eq 0 else 1) }" "Run: python manage.py migrate --noinput"

Run-WarningCheck "MIGRATIONS" "Migration Conflicts" "python manage.py makemigrations --dry-run --check" "Run: python manage.py makemigrations --merge --noinput"

Write-Host "📋 CATEGORY 6: USER AUTHENTICATION" -ForegroundColor Magenta
Write-Host "=================================" -ForegroundColor Magenta

Run-Check "AUTH" "Admin User Exists" "python manage.py shell -c 'from django.contrib.auth.models import User; exit(0 if User.objects.filter(is_superuser=True).exists() else 1)'" "Create admin user: python manage.py createsuperuser"

Run-Check "AUTH" "User Authentication" "python manage.py shell -c 'from django.contrib.auth.models import User; user = User.objects.first(); exit(0 if user and user.check_password(\"test\") == False else 1)'" "Check user authentication system"

Write-Host "📋 CATEGORY 7: EXTERNAL DEPENDENCIES" -ForegroundColor Magenta
Write-Host "===================================" -ForegroundColor Magenta

Run-Check "DEPS" "Redis Connection" "python manage.py shell -c 'from django.core.cache import cache; cache.set(\"test\", \"value\"); exit(0 if cache.get(\"test\") == \"value\" else 1)'" "Check Redis server connectivity"

Run-WarningCheck "DEPS" "PostgreSQL Version" "python manage.py shell -c 'from django.db import connection; cursor = connection.cursor(); cursor.execute(\"SELECT version()\"); version = cursor.fetchone()[0]; print(f\"PostgreSQL: {version}\"); exit(0)'" "Check PostgreSQL version compatibility"

Write-Host ""
Write-Host "📊 HEALTH CHECK SUMMARY" -ForegroundColor Green
Write-Host "======================" -ForegroundColor Green
Write-Host "Total Checks: $TOTAL_CHECKS"
Write-Host "✅ Passed: $PASSED_CHECKS" -ForegroundColor Green
Write-Host "❌ Failed: $FAILED_CHECKS" -ForegroundColor Red
Write-Host "⚠️  Warnings: $WARNING_CHECKS" -ForegroundColor Yellow
Write-Host ""

# Calculate health percentage
if ($TOTAL_CHECKS -gt 0) {
    $HEALTH_PERCENTAGE = [math]::Round(($PASSED_CHECKS * 100) / $TOTAL_CHECKS)
    Write-Host "🏥 Overall Health: $HEALTH_PERCENTAGE%" -ForegroundColor Cyan
    
    if ($HEALTH_PERCENTAGE -ge 90) {
        Write-Host "🎉 System is in excellent health!" -ForegroundColor Green
    } elseif ($HEALTH_PERCENTAGE -ge 75) {
        Write-Host "✅ System is in good health with minor issues" -ForegroundColor Green
    } elseif ($HEALTH_PERCENTAGE -ge 50) {
        Write-Host "⚠️  System has moderate issues that need attention" -ForegroundColor Yellow
    } else {
        Write-Host "🚨 System has critical issues requiring immediate attention" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "🔧 QUICK FIXES FOR COMMON ISSUES" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

if ($FAILED_CHECKS -gt 0) {
    Write-Host "Based on the failed checks above, try these solutions:" -ForegroundColor Yellow
    Write-Host ""
    
    # Check if timezone field is missing
    $timezoneCheck = python manage.py shell -c 'from maintenance.models import MaintenanceActivity; exit(0 if hasattr(MaintenanceActivity, "timezone") else 1)' 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "🌍 TIMEZONE FIELD MISSING:" -ForegroundColor Red
        Write-Host "   Run: ./scripts/simple_timezone_fix.sh" -ForegroundColor White
        Write-Host ""
    }
    
    # Check if migrations are pending
    $migrationCheck = python manage.py showmigrations --plan | Select-String -Pattern '\[ \]'
    if ($migrationCheck) {
        Write-Host "📦 PENDING MIGRATIONS:" -ForegroundColor Red
        Write-Host "   Run: python manage.py migrate --noinput" -ForegroundColor White
        Write-Host ""
    }
    
    # Check if admin user is missing
    $adminCheck = python manage.py shell -c 'from django.contrib.auth.models import User; exit(0 if User.objects.filter(is_superuser=True).exists() else 1)' 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "👤 ADMIN USER MISSING:" -ForegroundColor Red
        Write-Host "   Run: python manage.py createsuperuser" -ForegroundColor White
        Write-Host ""
    }
}

Write-Host "💡 For detailed diagnostics, run:" -ForegroundColor Cyan
Write-Host "   ./scripts/test_calendar_api.sh" -ForegroundColor White
Write-Host ""
Write-Host "🎯 Health check completed at $(Get-Date)" -ForegroundColor Green
