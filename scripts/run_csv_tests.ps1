# CSV Import Test Runner - PowerShell Version
# Run this script to automatically test the CSV import functionality

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CSV Import Test Runner" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ ERROR: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python and try again" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if we're in the right directory
if (-not (Test-Path "tests\test_csv_import.py")) {
    Write-Host "❌ ERROR: Please run this script from the project root directory" -ForegroundColor Red
    Write-Host "Current directory: $(Get-Location)" -ForegroundColor Yellow
    Write-Host "Expected files: tests\test_csv_import.py" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "🚀 Running CSV Import Tests..." -ForegroundColor Green
Write-Host ""

# Run the test runner
try {
    python scripts\run_csv_import_tests.py
    $exitCode = $LASTEXITCODE
} catch {
    Write-Host "❌ Error running tests: $_" -ForegroundColor Red
    $exitCode = 1
}

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "✅ Tests completed successfully!" -ForegroundColor Green
} else {
    Write-Host "❌ Tests completed with errors (Exit code: $exitCode)" -ForegroundColor Red
}

Write-Host "Check the output above for detailed results." -ForegroundColor Yellow
Read-Host "Press Enter to exit"
exit $exitCode
