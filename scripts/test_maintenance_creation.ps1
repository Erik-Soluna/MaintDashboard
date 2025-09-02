# Simple test script to diagnose maintenance creation issues
# This script can be run on the server to test the maintenance creation API

Write-Host "Testing Maintenance Creation API" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan

# Test the API endpoint directly
Write-Host "Testing API endpoint: /maintenance/api/activities/create/" -ForegroundColor Yellow

# Create test data
$testData = @{
    title = "Test Maintenance Activity"
    description = "This is a test maintenance activity created by the diagnostic script"
    priority = "medium"
    status = "scheduled"
    scheduled_start = "2025-01-15T09:00:00"
    scheduled_end = "2025-01-15T17:00:00"
    timezone = "America/Chicago"
    equipment = $null
    activity_type = $null
    assigned_to = $null
} | ConvertTo-Json

Write-Host "Sending test data:" -ForegroundColor Yellow
Write-Host $testData

Write-Host ""
Write-Host "Making API request..." -ForegroundColor Yellow

try {
    # Test the API endpoint
    $response = Invoke-RestMethod -Uri "https://dev.maintenance.errorlog.app/maintenance/api/activities/create/" `
        -Method POST `
        -ContentType "application/json" `
        -Headers @{"X-CSRFToken" = "test"} `
        -Body $testData `
        -ErrorAction Stop
    
    Write-Host "API Response:" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 10
} catch {
    Write-Host "API Error:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    
    if ($_.Exception.Response) {
        $statusCode = $_.Exception.Response.StatusCode
        Write-Host "Status Code: $statusCode" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Additional Diagnostics:" -ForegroundColor Cyan
Write-Host ""

# Check if the endpoint is accessible
Write-Host "Testing endpoint accessibility..." -ForegroundColor Yellow
try {
    $headResponse = Invoke-WebRequest -Uri "https://dev.maintenance.errorlog.app/maintenance/api/activities/create/" -Method HEAD -ErrorAction Stop
    Write-Host "Endpoint accessible - Status: $($headResponse.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "Endpoint not accessible: $($_.Exception.Message)" -ForegroundColor Red
}

# Check if the application is running
Write-Host "Testing application health..." -ForegroundColor Yellow
try {
    $healthResponse = Invoke-WebRequest -Uri "https://dev.maintenance.errorlog.app/" -Method HEAD -ErrorAction Stop
    Write-Host "Application running - Status: $($healthResponse.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "Application not accessible: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "If the API returns errors, check:" -ForegroundColor Yellow
Write-Host "   1. Database connection issues" -ForegroundColor White
Write-Host "   2. Missing equipment or activity type data" -ForegroundColor White
Write-Host "   3. Form validation errors" -ForegroundColor White
Write-Host "   4. Authentication/CSRF token issues" -ForegroundColor White
Write-Host "   5. Timezone field database migration issues" -ForegroundColor White
