@echo off
echo ========================================
echo CSV Import Test Runner
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python and try again
    pause
    exit /b 1
)

REM Check if we're in the right directory
if not exist "tests\test_csv_import.py" (
    echo ERROR: Please run this script from the project root directory
    echo Current directory: %CD%
    echo Expected files: tests\test_csv_import.py
    pause
    exit /b 1
)

echo Running CSV Import Tests...
echo.

REM Run the test runner
python scripts\run_csv_import_tests.py

echo.
echo Tests completed. Check the output above for results.
pause
