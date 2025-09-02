#!/bin/bash
# Simple test script to diagnose maintenance creation issues
# This script can be run on the server to test the maintenance creation API

echo "🔍 Testing Maintenance Creation API"
echo "=================================="

# Test the API endpoint directly
echo "📡 Testing API endpoint: /maintenance/api/activities/create/"

# Create test data
TEST_DATA='{
    "title": "Test Maintenance Activity",
    "description": "This is a test maintenance activity created by the diagnostic script",
    "priority": "medium",
    "status": "scheduled",
    "scheduled_start": "2025-01-15T09:00:00",
    "scheduled_end": "2025-01-15T17:00:00",
    "timezone": "America/Chicago",
    "equipment": null,
    "activity_type": null,
    "assigned_to": null
}'

echo "📤 Sending test data:"
echo "$TEST_DATA" | python -m json.tool

echo ""
echo "📡 Making API request..."

# Test the API endpoint
curl -X POST "https://dev.maintenance.errorlog.app/maintenance/api/activities/create/" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: test" \
  -d "$TEST_DATA" \
  -v

echo ""
echo "=================================="
echo "🔍 Additional Diagnostics:"
echo ""

# Check if the endpoint is accessible
echo "📡 Testing endpoint accessibility..."
curl -I "https://dev.maintenance.errorlog.app/maintenance/api/activities/create/" 2>/dev/null | head -1

# Check if the application is running
echo "📡 Testing application health..."
curl -I "https://dev.maintenance.errorlog.app/" 2>/dev/null | head -1

echo ""
echo "💡 If the API returns errors, check:"
echo "   1. Database connection issues"
echo "   2. Missing equipment or activity type data"
echo "   3. Form validation errors"
echo "   4. Authentication/CSRF token issues"
echo "   5. Timezone field database migration issues"
