#!/bin/bash

# Comprehensive System Health Check for Maintenance Dashboard
# Categorizes issues and provides actionable solutions

echo "🏥 SYSTEM HEALTH CHECK - Maintenance Dashboard"
echo "=============================================="
echo ""

# Navigate to app directory
cd /app

# Initialize counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

# Function to run a check and categorize results
run_check() {
    local category="$1"
    local check_name="$2"
    local command="$3"
    local fix_suggestion="$4"
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    echo "🔍 [$category] $check_name"
    
    if eval "$command" >/dev/null 2>&1; then
        echo "   ✅ PASS"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo "   ❌ FAIL"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        if [ -n "$fix_suggestion" ]; then
            echo "   💡 Fix: $fix_suggestion"
        fi
    fi
    echo ""
}

# Function to run a warning check
run_warning_check() {
    local category="$1"
    local check_name="$2"
    local command="$3"
    local warning_message="$4"
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    echo "🔍 [$category] $check_name"
    
    if eval "$command" >/dev/null 2>&1; then
        echo "   ✅ PASS"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo "   ⚠️  WARNING"
        WARNING_CHECKS=$((WARNING_CHECKS + 1))
        if [ -n "$warning_message" ]; then
            echo "   💡 Note: $warning_message"
        fi
    fi
    echo ""
}

echo "📋 CATEGORY 1: CORE APPLICATION HEALTH"
echo "======================================"

run_check "CORE" "Django Configuration" "python manage.py check --deploy" "Check Django settings and configuration"
run_check "CORE" "Database Connection" "python manage.py shell -c 'from django.db import connection; connection.cursor().execute(\"SELECT 1\")'" "Check database connectivity and credentials"
run_check "CORE" "Static Files" "python manage.py collectstatic --noinput" "Run collectstatic to ensure static files are available"

echo "📋 CATEGORY 2: DATABASE SCHEMA INTEGRITY"
echo "======================================="

run_check "SCHEMA" "MaintenanceActivity Model" "python manage.py shell -c 'from maintenance.models import MaintenanceActivity; MaintenanceActivity.objects.count()'" "Run: ./scripts/simple_timezone_fix.sh"
run_check "SCHEMA" "Timezone Field Exists" "python manage.py shell -c 'from maintenance.models import MaintenanceActivity; hasattr(MaintenanceActivity, \"timezone\")'" "Run: ./scripts/simple_timezone_fix.sh"
run_check "SCHEMA" "CalendarEvent Model" "python manage.py shell -c 'from events.models import CalendarEvent; CalendarEvent.objects.count()'" "Check events app migrations"
run_check "SCHEMA" "Equipment Model" "python manage.py shell -c 'from equipment.models import Equipment; Equipment.objects.count()'" "Check equipment app migrations"
run_check "SCHEMA" "Location Model" "python manage.py shell -c 'from core.models import Location; Location.objects.count()'" "Check core app migrations"

echo "📋 CATEGORY 3: API ENDPOINTS FUNCTIONALITY"
echo "========================================="

run_check "API" "fetch_unified_events API" "python manage.py shell -c '
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

run_check "API" "fetch_events API" "python manage.py shell -c '
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

echo "📋 CATEGORY 4: CALENDAR SPECIFIC ISSUES"
echo "======================================"

run_check "CALENDAR" "Calendar View Renders" "python manage.py shell -c '
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

run_warning_check "CALENDAR" "Maintenance Activities Count" "python manage.py shell -c 'from maintenance.models import MaintenanceActivity; count = MaintenanceActivity.objects.count(); exit(0 if count > 0 else 1)'" "No maintenance activities found - calendar may appear empty"

run_warning_check "CALENDAR" "Calendar Events Count" "python manage.py shell -c 'from events.models import CalendarEvent; count = CalendarEvent.objects.count(); exit(0 if count > 0 else 1)'" "No calendar events found - calendar may appear empty"

echo "📋 CATEGORY 5: MIGRATION STATUS"
echo "=============================="

run_check "MIGRATIONS" "Migration Status" "python manage.py showmigrations --plan | grep -v '\[X\]' | grep -q '\[ \]' && exit 1 || exit 0" "Run: python manage.py migrate --noinput"

run_warning_check "MIGRATIONS" "Migration Conflicts" "python manage.py makemigrations --dry-run --check" "Run: python manage.py makemigrations --merge --noinput"

echo "📋 CATEGORY 6: USER AUTHENTICATION"
echo "================================="

run_check "AUTH" "Admin User Exists" "python manage.py shell -c 'from django.contrib.auth.models import User; exit(0 if User.objects.filter(is_superuser=True).exists() else 1)'" "Create admin user: python manage.py createsuperuser"

run_check "AUTH" "User Authentication" "python manage.py shell -c 'from django.contrib.auth.models import User; user = User.objects.first(); exit(0 if user and user.check_password(\"test\") == False else 1)'" "Check user authentication system"

echo "📋 CATEGORY 7: EXTERNAL DEPENDENCIES"
echo "==================================="

run_check "DEPS" "Redis Connection" "python manage.py shell -c 'from django.core.cache import cache; cache.set(\"test\", \"value\"); exit(0 if cache.get(\"test\") == \"value\" else 1)'" "Check Redis server connectivity"

run_warning_check "DEPS" "PostgreSQL Version" "python manage.py shell -c 'from django.db import connection; cursor = connection.cursor(); cursor.execute(\"SELECT version()\"); version = cursor.fetchone()[0]; print(f\"PostgreSQL: {version}\"); exit(0)'" "Check PostgreSQL version compatibility"

echo ""
echo "📊 HEALTH CHECK SUMMARY"
echo "======================"
echo "Total Checks: $TOTAL_CHECKS"
echo "✅ Passed: $PASSED_CHECKS"
echo "❌ Failed: $FAILED_CHECKS"
echo "⚠️  Warnings: $WARNING_CHECKS"
echo ""

# Calculate health percentage
if [ $TOTAL_CHECKS -gt 0 ]; then
    HEALTH_PERCENTAGE=$(( (PASSED_CHECKS * 100) / TOTAL_CHECKS ))
    echo "🏥 Overall Health: $HEALTH_PERCENTAGE%"
    
    if [ $HEALTH_PERCENTAGE -ge 90 ]; then
        echo "🎉 System is in excellent health!"
    elif [ $HEALTH_PERCENTAGE -ge 75 ]; then
        echo "✅ System is in good health with minor issues"
    elif [ $HEALTH_PERCENTAGE -ge 50 ]; then
        echo "⚠️  System has moderate issues that need attention"
    else
        echo "🚨 System has critical issues requiring immediate attention"
    fi
fi

echo ""
echo "🔧 QUICK FIXES FOR COMMON ISSUES"
echo "================================"

if [ $FAILED_CHECKS -gt 0 ]; then
    echo "Based on the failed checks above, try these solutions:"
    echo ""
    
    # Check if timezone field is missing
    if ! python manage.py shell -c 'from maintenance.models import MaintenanceActivity; exit(0 if hasattr(MaintenanceActivity, "timezone") else 1)' >/dev/null 2>&1; then
        echo "🌍 TIMEZONE FIELD MISSING:"
        echo "   Run: ./scripts/simple_timezone_fix.sh"
        echo ""
    fi
    
    # Check if migrations are pending
    if python manage.py showmigrations --plan | grep -q '\[ \]'; then
        echo "📦 PENDING MIGRATIONS:"
        echo "   Run: python manage.py migrate --noinput"
        echo ""
    fi
    
    # Check if admin user is missing
    if ! python manage.py shell -c 'from django.contrib.auth.models import User; exit(0 if User.objects.filter(is_superuser=True).exists() else 1)' >/dev/null 2>&1; then
        echo "👤 ADMIN USER MISSING:"
        echo "   Run: python manage.py createsuperuser"
        echo ""
    fi
fi

echo "💡 For detailed diagnostics, run:"
echo "   ./scripts/test_calendar_api.sh"
echo ""
echo "🎯 Health check completed at $(date)"
